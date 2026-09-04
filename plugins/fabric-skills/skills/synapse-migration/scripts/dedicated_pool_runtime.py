"""Runtime controls for Dedicated SQL Pool schema/code migrations.

This module deliberately contains no source-row operations and no generated-notebook
execution path. Callers inject a Fabric HTTP transport so behavior is testable without
credentials or remote mutation.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
import argparse
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SKILL_HEADER = {"x-ms-fabric-skill": "synapse-migration"}
TERMINAL_LRO_STATES = {"Succeeded", "Failed", "Cancelled"}
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}


class MigrationBlocked(RuntimeError):
    """Raised before mutation when a migration contract is not satisfied."""


class Response(Protocol):
    status_code: int
    headers: Mapping[str, str]
    content: bytes

    def json(self) -> Mapping[str, Any]: ...


Transport = Callable[..., Response]


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def hash_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(canonical_json(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def collect_artifact_hashes(root: Path, relative_paths: Iterable[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    resolved_root = root.resolve()
    for relative_path in sorted(set(relative_paths)):
        artifact = (resolved_root / relative_path).resolve()
        if not artifact.is_relative_to(resolved_root):
            raise MigrationBlocked(f"Artifact path escapes the artifact root: {relative_path}")
        if not artifact.is_file():
            raise MigrationBlocked(f"Required artifact is missing: {relative_path}")
        hashes[relative_path] = hash_file(artifact)
    return hashes


def freeze_run_context(
    path: Path,
    *,
    datamart_id: str,
    workspace_id: str,
    lakehouse_id: str,
    artifact_root: Path,
    artifact_paths: Iterable[str],
) -> dict[str, Any]:
    context = {
        "version": 1,
        "datamartId": datamart_id,
        "workspaceId": workspace_id,
        "lakehouseId": lakehouse_id,
        "artifactHashes": collect_artifact_hashes(artifact_root, artifact_paths),
    }
    context["contextHash"] = sha256_bytes(canonical_json(context))
    atomic_write_json(path, context)
    return context


def verify_run_context(
    path: Path,
    artifact_root: Path,
    *,
    datamart_id: str,
    workspace_id: str,
    lakehouse_id: str,
) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MigrationBlocked(f"Run context could not be read: {error}") from error
    if not isinstance(loaded, dict):
        raise MigrationBlocked("Run context must be a JSON object")
    context = dict(loaded)
    recorded_hash = context.pop("contextHash", None)
    artifact_hashes = context.get("artifactHashes")
    if not isinstance(recorded_hash, str) or not recorded_hash:
        raise MigrationBlocked("Run context must contain a non-empty contextHash")
    if not isinstance(artifact_hashes, dict) or not all(
        isinstance(relative_path, str)
        and relative_path
        and isinstance(artifact_hash, str)
        and artifact_hash
        for relative_path, artifact_hash in artifact_hashes.items()
    ):
        raise MigrationBlocked("Run context artifactHashes must map paths to hashes")
    if recorded_hash != sha256_bytes(canonical_json(context)):
        raise MigrationBlocked("Run context was modified after the freeze gate")
    expected_owner = {
        "datamartId": datamart_id,
        "workspaceId": workspace_id,
        "lakehouseId": lakehouse_id,
    }
    if any(context.get(key) != value for key, value in expected_owner.items()):
        raise MigrationBlocked("Run context does not match the requested migration target")
    actual = collect_artifact_hashes(artifact_root, artifact_hashes.keys())
    if actual != artifact_hashes:
        raise MigrationBlocked("An artifact changed after the freeze gate")
    context["contextHash"] = recorded_hash
    return context


def _retry_after(response: Response, default: float = 1.0) -> float:
    try:
        return max(0.0, float(response.headers.get("Retry-After", default)))
    except (TypeError, ValueError):
        return default


def _json_object(response: Response, context: str) -> Mapping[str, Any]:
    try:
        payload = response.json()
    except Exception as exception:
        raise MigrationBlocked(f"{context} did not contain valid JSON") from exception
    if not isinstance(payload, Mapping):
        raise MigrationBlocked(f"{context} must be a JSON object")
    return payload


def fabric_pages(
    transport: Transport,
    url: str,
    *,
    deadline_seconds: float = 120,
    monotonic: Callable[[], float] = time.monotonic,
) -> list[Mapping[str, Any]]:
    collection_url = url
    deadline = monotonic() + deadline_seconds
    items: list[Mapping[str, Any]] = []
    visited: set[str] = set()
    while url:
        if monotonic() >= deadline:
            raise TimeoutError("Fabric pagination deadline exceeded")
        if url in visited:
            raise MigrationBlocked("Fabric pagination returned a continuation cycle")
        visited.add(url)
        response = transport("GET", url, headers=dict(SKILL_HEADER))
        if response.status_code != 200:
            raise MigrationBlocked(f"Fabric list request failed with HTTP {response.status_code}")
        payload = _json_object(response, "Fabric list response")
        page_items = payload.get("value", [])
        if not isinstance(page_items, list) or not all(isinstance(item, Mapping) for item in page_items):
            raise MigrationBlocked("Fabric list response value must be an array of objects")
        items.extend(page_items)
        url = payload.get("continuationUri") or payload.get("@odata.nextLink") or ""
        if not isinstance(url, str):
            raise MigrationBlocked("Fabric list continuation URI must be a string")
        if not url and payload.get("continuationToken"):
            if not isinstance(payload["continuationToken"], str):
                raise MigrationBlocked("Fabric list continuation token must be a string")
            parsed_url = urlsplit(collection_url)
            query = [
                pair
                for pair in parse_qsl(parsed_url.query, keep_blank_values=True)
                if pair[0].casefold() != "continuationtoken"
            ]
            query.append(("continuationToken", str(payload["continuationToken"])))
            url = urlunsplit(parsed_url._replace(query=urlencode(query)))
    return items


def await_lro(
    transport: Transport,
    response: Response,
    *,
    max_poll_duration_seconds: float = 900,
    max_poll_attempts: int = 180,
    retry_after_seconds: float = 5,
    deadline_seconds: float | None = None,
    max_polls: int | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = lambda message: print(message, file=sys.stderr),
) -> Mapping[str, Any]:
    if deadline_seconds is not None:
        max_poll_duration_seconds = deadline_seconds
    if max_polls is not None:
        max_poll_attempts = max_polls
    if max_poll_duration_seconds <= 0:
        raise ValueError("max_poll_duration_seconds must be greater than zero")
    if max_poll_attempts <= 0:
        raise ValueError("max_poll_attempts must be greater than zero")
    if retry_after_seconds < 0:
        raise ValueError("retry_after_seconds must not be negative")

    if response.status_code in {200, 201}:
        if getattr(response, "content", None) == b"":
            return {}
        return _json_object(response, "Fabric mutation response")
    if response.status_code != 202:
        raise MigrationBlocked(f"Fabric mutation failed with HTTP {response.status_code}")
    location = response.headers.get("Location")
    if not location:
        raise MigrationBlocked("Fabric 202 response omitted Location")
    deadline = monotonic() + max_poll_duration_seconds
    retry_count = 0
    next_delay = _retry_after(response, retry_after_seconds)
    for attempt in range(1, max_poll_attempts + 1):
        remaining = deadline - monotonic()
        if remaining <= 0:
            log("Fabric operation polling timed out before the next attempt")
            raise TimeoutError("Fabric operation deadline exceeded")
        sleep(min(next_delay, remaining))
        if monotonic() >= deadline:
            log("Fabric operation polling timed out while waiting for the next attempt")
            raise TimeoutError("Fabric operation deadline exceeded")
        response = transport("GET", location, headers=dict(SKILL_HEADER))
        if response.status_code in RETRYABLE_HTTP_STATUSES:
            retry_count += 1
            header_delay = _retry_after(response, retry_after_seconds)
            next_delay = max(header_delay, retry_after_seconds * (2 ** (retry_count - 1)))
            log(
                f"Fabric operation poll attempt {attempt}/{max_poll_attempts} returned "
                f"retryable HTTP {response.status_code}; retrying in {next_delay:g}s"
            )
            continue
        if response.status_code != 200:
            log(
                f"Fabric operation poll attempt {attempt}/{max_poll_attempts} failed with "
                f"non-retryable HTTP {response.status_code}"
            )
            raise MigrationBlocked(f"Fabric operation poll failed with HTTP {response.status_code}")
        try:
            payload = _json_object(response, "Fabric operation poll response")
        except MigrationBlocked as error:
            log(f"Fabric operation poll attempt {attempt}/{max_poll_attempts} failed: {error}")
            raise
        status = payload.get("status")
        if not isinstance(status, str) or not status:
            log(
                f"Fabric operation poll attempt {attempt}/{max_poll_attempts} failed: "
                "response omitted a valid status"
            )
            raise MigrationBlocked("Fabric operation poll response omitted a valid status")
        if status in TERMINAL_LRO_STATES:
            if status != "Succeeded":
                log(f"Fabric operation ended in terminal state {status}")
                raise MigrationBlocked(f"Fabric operation ended in {status}")
            return payload
        retry_count = 0
        next_delay = _retry_after(response, retry_after_seconds)
    log(f"Fabric operation polling exhausted {max_poll_attempts} attempts")
    raise TimeoutError("Fabric operation poll limit exceeded")


def livy_statement_payload(code: str) -> dict[str, str]:
    if not code.strip():
        raise MigrationBlocked("Livy schema statement cannot be empty")
    if code.lstrip().startswith("%%"):
        raise MigrationBlocked("Livy schema statement must be raw Spark SQL without notebook magic")
    return {"kind": "sql", "code": code}


def validate_spark_sql_notebook(notebook: Mapping[str, Any], parse_sql: Callable[[str], None]) -> None:
    if notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
        raise MigrationBlocked("Notebook must be valid nbformat 4 JSON")
    nbformat_minor = notebook.get("nbformat_minor")
    try:
        valid_minor_version = not isinstance(nbformat_minor, bool) and int(nbformat_minor) >= 5
    except (TypeError, ValueError):
        valid_minor_version = False
    if not valid_minor_version:
        raise MigrationBlocked("Notebook must declare nbformat_minor >= 5")
    parsed = 0
    code_cell_index = 0
    for index, cell in enumerate(notebook["cells"]):
        if not isinstance(cell, dict):
            raise MigrationBlocked(f"Notebook cell {index} must be a JSON object (got {type(cell).__name__})")
        if cell.get("cell_type") != "code":
            continue
        source_value = cell.get("source", [])
        if isinstance(source_value, str):
            source = source_value
        elif isinstance(source_value, list) and all(isinstance(line, str) for line in source_value):
            source = "".join(source_value)
        else:
            raise MigrationBlocked(f"Notebook code cell {index} source must be a string or array of strings")
        stripped = source.lstrip()
        if code_cell_index == 0 and stripped.startswith("%%configure"):
            configure_lines = stripped.split("\n", 1)
            if configure_lines[0].strip() != "%%configure":
                raise MigrationBlocked("The first-code-cell %%configure magic must be bare")
            try:
                configure = json.loads(configure_lines[1] if len(configure_lines) == 2 else "")
            except (json.JSONDecodeError, TypeError) as exception:
                raise MigrationBlocked("The first-code-cell %%configure payload must be valid JSON") from exception
            if not isinstance(configure, Mapping) or not isinstance(configure.get("conf"), Mapping):
                raise MigrationBlocked("The first-code-cell %%configure payload must contain a conf object")
            code_cell_index += 1
            continue
        code_cell_index += 1
        if not stripped.startswith("%%sql"):
            raise MigrationBlocked("Every executable transformation cell must use %%sql")
        sql = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        if not sql.strip():
            raise MigrationBlocked("Spark SQL cell cannot be empty")
        try:
            parse_sql(sql)
        except Exception as exception:
            raise MigrationBlocked(f"Target Spark parser rejected notebook cell {index}: {exception}") from exception
        parsed += 1
    if parsed == 0:
        raise MigrationBlocked("Notebook contains no parser-valid Spark SQL transformation cells")


def update_manifest(path: Path, mutation: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    if path.exists():
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exception:
            raise MigrationBlocked(f"Migration manifest could not be read: {exception}") from exception
        if not isinstance(manifest, dict):
            raise MigrationBlocked("Migration manifest root must be a JSON object")
    else:
        manifest = {"version": 1}
    recorded_hash = manifest.get("manifestHash")
    if recorded_hash is not None:
        actual_hash = sha256_bytes(
            canonical_json({key: value for key, value in manifest.items() if key != "manifestHash"})
        )
        if not isinstance(recorded_hash, str) or recorded_hash != actual_hash:
            raise MigrationBlocked("Migration manifest was modified after its integrity hash was written")
    mutation(manifest)
    manifest["manifestHash"] = sha256_bytes(
        canonical_json({key: value for key, value in manifest.items() if key != "manifestHash"})
    )
    atomic_write_json(path, manifest)
    return manifest


def record_checkpoint(
    path: Path,
    *,
    datamart_id: str,
    source_id: str,
    stage: str,
    status: str,
    input_hash: str,
    output_hash: str | None = None,
    identifiers: Mapping[str, str] | None = None,
    blocker: str | None = None,
) -> dict[str, Any]:
    canonical_stage = stage.casefold()

    def mutate(manifest: dict[str, Any]) -> None:
        if manifest.get("datamartId", datamart_id) != datamart_id:
            raise MigrationBlocked("Checkpoint datamart does not match the manifest owner")
        manifest["datamartId"] = datamart_id
        objects = manifest.setdefault("objects", [])
        if not isinstance(objects, list) or not all(isinstance(item, Mapping) for item in objects):
            raise MigrationBlocked("Migration manifest objects must be an array of JSON objects")
        checkpoint = next(
            (
                item
                for item in objects
                if isinstance(item.get("sourceId"), str)
                and item["sourceId"].casefold() == source_id.casefold()
                and isinstance(item.get("stage"), str)
                and item["stage"].casefold() == canonical_stage
            ),
            None,
        )
        value = {
            "sourceId": source_id,
            "stage": canonical_stage,
            "status": status,
            "inputHash": input_hash,
            "outputHash": output_hash,
            "identifiers": dict(identifiers or {}),
            "blocker": blocker,
        }
        if checkpoint is None:
            objects.append(value)
        else:
            checkpoint.clear()
            checkpoint.update(value)

    return update_manifest(path, mutate)


def checkpoint_is_reusable(item: Mapping[str, Any], input_hash: str) -> bool:
    return item.get("status") == "Succeeded" and item.get("inputHash") == input_hash and bool(item.get("outputHash"))


def require_schema_ready(manifest: Mapping[str, Any], expected_schema: Mapping[str, Any]) -> None:
    expected_objects = expected_schema.get("objects", [])
    if not isinstance(expected_objects, list) or not expected_objects:
        raise MigrationBlocked("Expected schema must contain at least one object")
    expected_ids = [item.get("sourceStableId") for item in expected_objects if isinstance(item, Mapping)]
    if len(expected_ids) != len(expected_objects) or any(
        not isinstance(source_id, str) or not source_id.strip() for source_id in expected_ids
    ):
        raise MigrationBlocked("Every expected schema object must have a non-empty string sourceStableId")
    expected_ids_by_casefold = {source_id.casefold(): source_id for source_id in expected_ids}
    if len(expected_ids_by_casefold) != len(expected_ids):
        raise MigrationBlocked("Expected schema sourceStableId values must be unique")

    manifest_objects = manifest.get("objects", [])
    if not isinstance(manifest_objects, list) or not all(isinstance(item, Mapping) for item in manifest_objects):
        raise MigrationBlocked("Schema manifest objects must be an array of JSON objects")

    checkpoints: dict[tuple[str, str], Mapping[str, Any]] = {}
    for item in manifest_objects:
        source_id = item.get("sourceId")
        stage = item.get("stage")
        if not isinstance(source_id, str) or source_id.casefold() not in expected_ids_by_casefold:
            continue
        if not isinstance(stage, str) or stage.casefold() not in {"schema", "metadata"}:
            continue
        key = (expected_ids_by_casefold[source_id.casefold()], stage.casefold())
        if key in checkpoints:
            raise MigrationBlocked("Schema manifest contains a duplicate object checkpoint")
        checkpoints[key] = item

    required = {(source_id, stage) for source_id in expected_ids for stage in ("schema", "metadata")}
    if set(checkpoints) != required or any(item.get("status") != "Succeeded" for item in checkpoints.values()):
        raise MigrationBlocked("Notebook publication is blocked until schema and metadata validation succeed")


def record_orphan_notebook(
    path: Path,
    *,
    datamart_id: str,
    source_id: str,
    notebook_id: str,
    operation_id: str | None,
    cleanup_status: str,
) -> dict[str, Any]:
    identifiers = {"notebookId": notebook_id}
    if operation_id is not None:
        identifiers["operationId"] = operation_id
    return record_checkpoint(
        path,
        datamart_id=datamart_id,
        source_id=source_id,
        stage="notebook-publication",
        status="RecoveryRequired",
        input_hash="pending-definition",
        identifiers=identifiers,
        blocker=f"Empty notebook item; cleanup={cleanup_status}",
    )


def spark_catalog_view_queries(schema: str, view: str) -> list[str]:
    escaped_schema = schema.replace("`", "``")
    escaped_view = view.replace("`", "``")
    return [
        f"SHOW VIEWS IN `{escaped_schema}`",
        f"DESCRIBE EXTENDED `{escaped_schema}`.`{escaped_view}`",
    ]


def regenerate_reports(manifest: Mapping[str, Any], json_path: Path, markdown_path: Path) -> None:
    atomic_write_json(json_path, manifest)
    objects = manifest.get("objects", [])
    lines = ["# Dedicated Pool Migration Report", "", "| Object | Stage | Status | Blocker |", "|---|---|---|---|"]
    for item in sorted(objects, key=lambda value: (str(value.get("sourceId", "")), str(value.get("stage", "")))):
        lines.append(
            f"| {item.get('sourceId', '')} | {item.get('stage', '')} | "
            f"{item.get('status', '')} | {item.get('blocker', '')} |"
        )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_effective_region(workspace_region: str, capacity_region: str) -> None:
    if workspace_region.strip().casefold() != capacity_region.strip().casefold():
        raise MigrationBlocked(
            f"Workspace effective region {workspace_region!r} conflicts with capacity region {capacity_region!r}"
        )


@dataclass(frozen=True)
class PortfolioEntry:
    datamart_id: str
    workspace_id: str
    lakehouse_id: str
    capacity_id: str
    region: str
    wave: str
    artifact_root: str
    capacity_region: str | None = None
    current_workspace_items: int = 0
    planned_non_notebook_items: int = 0
    planned_notebook_items: int = 0
    reserved_headroom: int = 0
    workspace_item_limit: int = 1000


def validate_portfolio(entries: Iterable[PortfolioEntry]) -> list[PortfolioEntry]:
    result = [
        replace(
            entry,
            datamart_id=entry.datamart_id.strip(),
            workspace_id=entry.workspace_id.strip(),
            lakehouse_id=entry.lakehouse_id.strip(),
            capacity_id=entry.capacity_id.strip(),
            region=entry.region.strip(),
            wave=entry.wave.strip(),
            artifact_root=entry.artifact_root.strip(),
            capacity_region=entry.capacity_region.strip() if entry.capacity_region is not None else None,
        )
        for entry in entries
    ]
    datamarts: set[str] = set()
    roots: set[str] = set()
    targets: set[tuple[str, str]] = set()
    for entry in result:
        required_values = {
            "datamart_id": entry.datamart_id,
            "workspace_id": entry.workspace_id,
            "lakehouse_id": entry.lakehouse_id,
            "capacity_id": entry.capacity_id,
            "region": entry.region,
            "wave": entry.wave,
            "artifact_root": entry.artifact_root,
        }
        for field, value in required_values.items():
            if not value:
                raise MigrationBlocked(f"Portfolio entry {field} must be a non-empty string")
        if entry.capacity_region == "":
            raise MigrationBlocked("Portfolio entry capacity_region must be a non-empty string or null")
        normalized_datamart = entry.datamart_id.casefold()
        if normalized_datamart in datamarts:
            raise MigrationBlocked(f"Duplicate datamart assignment: {entry.datamart_id}")
        target = (entry.workspace_id.casefold(), entry.lakehouse_id.casefold())
        if target in targets:
            raise MigrationBlocked(f"Duplicate workspace/Lakehouse assignment: {target}")
        normalized_root = str(Path(entry.artifact_root).resolve()).casefold()
        if normalized_root in roots:
            raise MigrationBlocked(f"Artifact root is shared by multiple datamarts: {entry.artifact_root}")
        if entry.capacity_region:
            validate_effective_region(entry.region, entry.capacity_region)
        projected_items = (
            entry.current_workspace_items
            + entry.planned_non_notebook_items
            + entry.planned_notebook_items
            + entry.reserved_headroom
        )
        if projected_items > entry.workspace_item_limit:
            raise MigrationBlocked(
                f"Workspace {entry.workspace_id} projects {projected_items} items including headroom; "
                f"limit is {entry.workspace_item_limit}"
            )
        datamarts.add(normalized_datamart)
        targets.add(target)
        roots.add(normalized_root)
    return result


def select_portfolio(
    entries: Iterable[PortfolioEntry],
    *,
    datamart: str | None = None,
    wave: str | None = None,
    failed: set[str] | None = None,
) -> list[PortfolioEntry]:
    normalized_datamart = datamart.strip().casefold() if datamart is not None else None
    normalized_wave = wave.strip().casefold() if wave is not None else None
    normalized_failed = {value.strip().casefold() for value in failed} if failed is not None else None
    return [
        entry
        for entry in entries
        if (normalized_datamart is None or entry.datamart_id.strip().casefold() == normalized_datamart)
        and (normalized_wave is None or entry.wave.strip().casefold() == normalized_wave)
        and (normalized_failed is None or entry.datamart_id.strip().casefold() in normalized_failed)
    ]


def capacity_batches(entries: Iterable[PortfolioEntry], limit_by_capacity: Mapping[str, int]) -> list[list[PortfolioEntry]]:
    pending = list(entries)
    normalized_limits = {capacity_id.strip().casefold(): limit for capacity_id, limit in limit_by_capacity.items()}
    batches: list[list[PortfolioEntry]] = []
    while pending:
        counts: dict[str, int] = {}
        batch: list[PortfolioEntry] = []
        deferred: list[PortfolioEntry] = []
        for entry in pending:
            capacity_id = entry.capacity_id.strip().casefold()
            limit = normalized_limits.get(capacity_id, 1)
            if limit < 1:
                raise MigrationBlocked(f"Capacity concurrency must be positive: {entry.capacity_id}")
            if counts.get(capacity_id, 0) < limit:
                batch.append(entry)
                counts[capacity_id] = counts.get(capacity_id, 0) + 1
            else:
                deferred.append(entry)
        batches.append(batch)
        pending = deferred
    return batches


def adaptive_capacity_limit(current_limit: int, status_code: int, queued_sessions: int = 0) -> int:
    if status_code == 429 or queued_sessions > 0:
        return max(1, current_limit // 2)
    if 200 <= status_code < 300 and queued_sessions == 0:
        return current_limit + 1
    return current_limit


def wave_can_promote(results: Iterable[Mapping[str, Any]], *, minimum_success_rate: float, maximum_blockers: int) -> bool:
    values = list(results)
    if not values:
        return False
    successes = sum(value.get("status") == "Succeeded" for value in values)
    blockers = sum(bool(value.get("blocker")) for value in values)
    return successes / len(values) >= minimum_success_rate and blockers <= maximum_blockers


def fleet_summary(manifests: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    result = {
        "datamarts": 0,
        "succeeded": 0,
        "failed": 0,
        "quarantined": [],
        "blockers": 0,
        "retries": 0,
        "durationSeconds": 0.0,
        "projectedRemainingSeconds": 0.0,
    }
    for manifest in manifests:
        result["datamarts"] += 1
        status = manifest.get("status")
        if status == "Succeeded":
            result["succeeded"] += 1
        elif status == "Quarantined":
            datamart_id = manifest.get("datamartId")
            if datamart_id is not None:
                result["quarantined"].append(datamart_id)
        else:
            result["failed"] += 1
        blockers = manifest.get("blockers")
        result["blockers"] += len(blockers) if isinstance(blockers, list) else 0
        try:
            result["retries"] += int(manifest.get("retries") or 0)
        except (TypeError, ValueError):
            pass
        try:
            result["durationSeconds"] += float(manifest.get("durationSeconds") or 0)
        except (TypeError, ValueError):
            pass
        try:
            result["projectedRemainingSeconds"] += float(manifest.get("projectedRemainingSeconds") or 0)
        except (TypeError, ValueError):
            pass
    result["quarantined"].sort(key=str)
    return result


def quarantine_manifest(path: Path, blocker: str) -> dict[str, Any]:
    def mutate(manifest: dict[str, Any]) -> None:
        manifest["status"] = "Quarantined"
        blockers = manifest.get("blockers")
        if not isinstance(blockers, list):
            blockers = []
            manifest["blockers"] = blockers
        if blocker not in blockers:
            blockers.append(blocker)

    return update_manifest(path, mutate)


def _load_portfolio(path: Path) -> list[PortfolioEntry]:
    payload = _load_json_object(path, "Portfolio")
    datamarts = payload.get("datamarts")
    if not isinstance(datamarts, list):
        raise MigrationBlocked("Portfolio field 'datamarts' must be a JSON array")

    required_fields = (
        "datamartId",
        "workspaceId",
        "lakehouseId",
        "capacityId",
        "region",
        "wave",
        "artifactRoot",
    )
    numeric_fields = (
        "currentWorkspaceItems",
        "plannedNonNotebookItems",
        "plannedNotebookItems",
        "reservedHeadroom",
        "workspaceItemLimit",
    )
    for index, item in enumerate(datamarts):
        if not isinstance(item, dict):
            raise MigrationBlocked(f"Portfolio datamarts[{index}] must be a JSON object")
        for field in required_fields:
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise MigrationBlocked(f"Portfolio datamarts[{index}].{field} must be a non-empty string")
        capacity_region = item.get("capacityRegion")
        if capacity_region is not None and (
            not isinstance(capacity_region, str) or not capacity_region.strip()
        ):
            raise MigrationBlocked(
                f"Portfolio datamarts[{index}].capacityRegion must be a non-empty string or null"
            )
        for field in numeric_fields:
            value = item.get(field, 1000 if field == "workspaceItemLimit" else 0)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise MigrationBlocked(
                    f"Portfolio datamarts[{index}].{field} must be a non-negative integer"
                )

    return validate_portfolio(
        PortfolioEntry(
            datamart_id=item["datamartId"].strip(),
            workspace_id=item["workspaceId"].strip(),
            lakehouse_id=item["lakehouseId"].strip(),
            capacity_id=item["capacityId"].strip(),
            region=item["region"].strip(),
            wave=item["wave"].strip(),
            artifact_root=item["artifactRoot"].strip(),
            capacity_region=item["capacityRegion"].strip() if item.get("capacityRegion") is not None else None,
            current_workspace_items=item.get("currentWorkspaceItems", 0),
            planned_non_notebook_items=item.get("plannedNonNotebookItems", 0),
            planned_notebook_items=item.get("plannedNotebookItems", 0),
            reserved_headroom=item.get("reservedHeadroom", 0),
            workspace_item_limit=item.get("workspaceItemLimit", 1000),
        )
        for item in datamarts
    )


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exception:
        raise MigrationBlocked(f"{label} file {path} could not be read as JSON: {exception}") from exception
    if not isinstance(payload, dict):
        raise MigrationBlocked(f"{label} file {path} root must be a JSON object")
    return payload


def _load_failed_datamarts(path: Path) -> set[str]:
    payload = _load_json_object(path, "Resume-failed")
    failed_datamarts = payload.get("failedDatamarts")
    if not isinstance(failed_datamarts, list):
        raise MigrationBlocked("Resume-failed field 'failedDatamarts' must be a JSON array")
    if any(not isinstance(value, str) or not value.strip() for value in failed_datamarts):
        raise MigrationBlocked("Resume-failed field 'failedDatamarts' must contain only non-empty strings")
    return {value.strip() for value in failed_datamarts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan an isolated Dedicated Pool migration portfolio")
    parser.add_argument("portfolio", type=Path)
    parser.add_argument("--datamart")
    parser.add_argument("--wave")
    parser.add_argument("--resume-failed", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    failed = None
    if args.resume_failed:
        failed = _load_failed_datamarts(args.resume_failed)
    selected = select_portfolio(_load_portfolio(args.portfolio), datamart=args.datamart, wave=args.wave, failed=failed)
    if not selected:
        raise MigrationBlocked("Portfolio selectors matched no datamarts")
    print(json.dumps({"dryRun": args.dry_run, "datamarts": [entry.datamart_id for entry in selected]}, sort_keys=True))
    return 0


def cli(argv: list[str] | None = None) -> int:
    try:
        return main(argv)
    except MigrationBlocked as exception:
        print(f"Dedicated Pool migration blocked: {exception}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(cli())