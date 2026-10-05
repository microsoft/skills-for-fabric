"""Runtime controls for Dedicated SQL Pool schema/code migrations.

This module deliberately contains no source-row operations and no generated-notebook
execution path. Callers inject a Fabric HTTP transport so behavior is testable without
credentials or remote mutation.
"""

from __future__ import annotations

import hashlib
import base64
import binascii
import json
import os
import re
import sys
import tempfile
import time
import argparse
import ast
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SKILL_HEADER = {"x-ms-fabric-skill": "synapse-migration"}
TERMINAL_LRO_STATES = {"Succeeded", "Failed", "Cancelled"}
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
TSQL_MANUAL_REDESIGN_PATTERNS = {
    "TRY/CATCH": r"\b(?:BEGIN\s+TRY|END\s+TRY|BEGIN\s+CATCH|END\s+CATCH)\b",
    "ExplicitTransaction": r"\b(?:BEGIN\s+TRAN(?:SACTION)?|SAVE\s+TRAN(?:SACTION)?|(?:COMMIT|ROLLBACK)(?:\s+TRAN(?:SACTION)?)?)\b",
    "TransactionState": r"(?:\bXACT_STATE\s*\(|@@TRANCOUNT\b)",
    "ErrorMetadata": r"\bERROR_(?:MESSAGE|NUMBER|SEVERITY|STATE|LINE|PROCEDURE)\s*\(",
    "ThrowOrRaiseError": r"\b(?:THROW|RAISERROR)\b",
    "DynamicSql": r"(?:\bsp_executesql\b|\bEXEC(?:UTE)?\s*(?:\(|@[A-Za-z_#][A-Za-z0-9_@$#]*|(?:N\s*)?__TSQL_STRING_LITERAL__))",
    "Cursor": r"\bCURSOR\b",
    "ControlFlowLoop": r"\bWHILE\b",
}
RESERVED_BRIDGE_PARAMETER_NAMES = {
    "__builtins__",
    "ValueError",
    "bool",
    "float",
    "int",
    "isinstance",
    "len",
    "re",
    "spark",
    "str",
}
ALLOWED_BRIDGE_METHOD_CALLS = {"casefold", "lower", "strip", "upper"}
FORBIDDEN_SPARK_ATTRIBUTES = {"createDataFrame", "read", "sql", "write"}
FORBIDDEN_DATAFRAME_ATTRIBUTES = {
    "agg",
    "collect",
    "drop",
    "filter",
    "groupBy",
    "join",
    "orderBy",
    "select",
    "sort",
    "where",
    "withColumn",
}
FORBIDDEN_EXIT_ROOTS = {"dbutils", "mssparkutils", "notebookutils"}
SQL_NULL_SENTINEL = "::SYNAPSE_MIGRATION_NULL::"
DELTA_UNSAFE_COLUMN_CHARACTERS = frozenset(" ,;{}()\n\t=")
LIVY_TERMINAL_STATEMENT_STATES = {"available", "error", "cancelled", "dead"}
SUPPORTED_SCHEMA_DDL_PATTERN = re.compile(
    r"(?is)^(?:"
    r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:SCHEMA|DATABASE|TABLE|VIEW)\b"
    r"|ALTER\s+(?:TABLE|VIEW)\b"
    r"|DROP\s+(?:SCHEMA|DATABASE|TABLE|VIEW)\b"
    r"|COMMENT\s+ON\s+(?:TABLE|VIEW|COLUMN)\b"
    r"|MSCK\s+REPAIR\s+TABLE\b"
    r")"
)
SENSITIVE_ERROR_VALUE_PATTERN = re.compile(
    r"(?i)([\"']?(?:authorization|api[-_ ]?key|access[-_ ]?token|client[-_ ]?secret|"
    r"account[-_ ]?key|shared[-_ ]?access[-_ ]?(?:key|signature)|"
    r"(?:aws[-_ ]?)?secret[-_ ]?access[-_ ]?key|password|pwd|token|secret)"
    r"[\"']?\s*[:=]\s*[\"']?(?:(?:bearer|basic)\s+)?)[^\"'\s,;&}]+"
)
SENSITIVE_DOUBLE_QUOTED_ERROR_VALUE_PATTERN = re.compile(
    r"(?i)([\"']?(?:authorization|api[-_ ]?key|access[-_ ]?token|client[-_ ]?secret|"
    r"account[-_ ]?key|shared[-_ ]?access[-_ ]?(?:key|signature)|"
    r"(?:aws[-_ ]?)?secret[-_ ]?access[-_ ]?key|password|pwd|token|secret)"
    r"[\"']?\s*[:=]\s*)\"(?:\\.|[^\"\\])*\""
)
SENSITIVE_SINGLE_QUOTED_ERROR_VALUE_PATTERN = re.compile(
    r"(?i)([\"']?(?:authorization|api[-_ ]?key|access[-_ ]?token|client[-_ ]?secret|"
    r"account[-_ ]?key|shared[-_ ]?access[-_ ]?(?:key|signature)|"
    r"(?:aws[-_ ]?)?secret[-_ ]?access[-_ ]?key|password|pwd|token|secret)"
    r"[\"']?\s*[:=]\s*)'(?:\\.|[^'\\])*'"
)
SENSITIVE_QUERY_VALUE_PATTERN = re.compile(
    r"(?i)([?&#](?:sig|se|sp|spr|srt|sv|token)=)[^&\s]+"
)
FORBIDDEN_BRIDGE_CONSTRUCTS = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.For,
    ast.AsyncFor,
    ast.While,
)


class MigrationBlocked(RuntimeError):
    """Raised before mutation when a migration contract is not satisfied."""


class LivySubmissionIndeterminate(MigrationBlocked):
    """Raised when Livy accepted a statement but its final target state is unknown."""

    def __init__(self, message: str, statement_id: str | None = None) -> None:
        super().__init__(message)
        self.statement_id = statement_id


class Response(Protocol):
    status_code: int
    headers: Mapping[str, str]
    content: bytes

    def json(self) -> Mapping[str, Any]: ...


Transport = Callable[..., Response]


def canonical_json(value: Any) -> bytes:
    def ordinal_key(text: str) -> bytes:
        return text.encode("utf-16-be", errors="surrogatepass")

    def order_keys(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {
                key: order_keys(item[key])
                for key in sorted(item, key=ordinal_key)
            }
        if isinstance(item, list):
            return [order_keys(element) for element in item]
        if isinstance(item, tuple):
            return [order_keys(element) for element in item]
        return item

    return json.dumps(
        order_keys(value),
        sort_keys=False,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def assess_tsql_manual_redesign(source: str) -> dict[str, Any]:
    searchable_source = _strip_tsql_comments_and_literals(
        source, mark_string_literals=True
    )
    normalized_identifiers = _strip_tsql_comments_and_literals(
        source, preserve_bracket_identifiers=True
    )
    features = [
        name
        for name, pattern in TSQL_MANUAL_REDESIGN_PATTERNS.items()
        if re.search(pattern, searchable_source, flags=re.IGNORECASE)
    ]
    if (
        re.search(
            r"(?i)\bEXEC(?:UTE)?\s+(?:sys\s*\.\s*)?sp_executesql(?=\s|$)",
            normalized_identifiers,
        )
        and "DynamicSql" not in features
    ):
        features.append("DynamicSql")
    return {
        "disposition": "ManualReviewRequired" if features else "AutomaticCandidate",
        "features": features,
        "reason": (
            "Unsupported Synapse T-SQL features require manual Spark SQL redesign: "
            + ", ".join(features)
            if features
            else None
        ),
    }


def _strip_tsql_comments_and_literals(
    source: str,
    *,
    mark_string_literals: bool = False,
    preserve_bracket_identifiers: bool = False,
) -> str:
    result: list[str] = []
    index = 0
    block_depth = 0
    quote: str | None = None
    in_bracket_identifier = False
    in_line_comment = False
    while index < len(source):
        current = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if in_line_comment:
            if current in "\r\n":
                in_line_comment = False
                result.append(current)
            else:
                result.append(" ")
            index += 1
            continue
        if block_depth:
            if current == "/" and following == "*":
                block_depth += 1
                result.extend((" ", " "))
                index += 2
            elif current == "*" and following == "/":
                block_depth -= 1
                result.extend((" ", " "))
                index += 2
            else:
                result.append(current if current in "\r\n" else " ")
                index += 1
            continue
        if in_bracket_identifier:
            if current == "]" and following == "]":
                if preserve_bracket_identifiers:
                    result.append("]")
                else:
                    result.extend((" ", " "))
                index += 2
            elif current == "]":
                if not preserve_bracket_identifiers:
                    result.append(" ")
                in_bracket_identifier = False
                index += 1
            else:
                result.append(
                    current
                    if preserve_bracket_identifiers or current in "\r\n"
                    else " "
                )
                index += 1
            continue
        if quote:
            if current == quote and following == quote:
                result.extend((" ", " "))
                index += 2
            elif current == quote:
                result.append(" ")
                quote = None
                index += 1
            else:
                result.append(current if current in "\r\n" else " ")
                index += 1
            continue
        if current == "-" and following == "-":
            in_line_comment = True
            result.extend((" ", " "))
            index += 2
        elif current == "/" and following == "*":
            block_depth = 1
            result.extend((" ", " "))
            index += 2
        elif current in {"'", '"', "`"}:
            quote = current
            if current == "'" and mark_string_literals:
                result.append(" __TSQL_STRING_LITERAL__ ")
            else:
                result.append(" ")
            index += 1
        elif current == "[":
            in_bracket_identifier = True
            if not preserve_bracket_identifiers:
                result.append(" ")
            index += 1
        else:
            result.append(current)
            index += 1
    return "".join(result)


def require_automatic_tsql_candidate(source: str) -> dict[str, Any]:
    assessment = assess_tsql_manual_redesign(source)
    if assessment["disposition"] != "AutomaticCandidate":
        features = ", ".join(assessment["features"])
        raise MigrationBlocked(
            f"Source procedure requires approved manual redesign before conversion: {features}"
        )
    return assessment


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
    statement = require_single_schema_statement(code)
    return {"kind": "sql", "code": statement}


def require_single_schema_statement(code: str) -> str:
    if not code.strip():
        raise MigrationBlocked("Livy schema statement cannot be empty")
    if code.lstrip().startswith("%%"):
        raise MigrationBlocked("Livy schema statement must be raw Spark SQL without notebook magic")

    segments = _split_sql_statements(code)
    if not segments:
        raise MigrationBlocked("Livy schema statement must contain executable SQL")
    if len(segments) != 1:
        raise MigrationBlocked("Each Livy schema request must contain exactly one SQL statement")
    statement = segments[0]
    searchable_statement = _strip_tsql_comments_and_literals(statement).strip()
    if not SUPPORTED_SCHEMA_DDL_PATTERN.match(searchable_statement):
        raise MigrationBlocked("Livy schema deployment accepts only supported schema DDL")
    if _is_row_materializing_create_table(searchable_statement):
        raise MigrationBlocked("Livy schema deployment rejects CTAS row materialization")
    return statement


def _is_row_materializing_create_table(statement: str) -> bool:
    create_table = re.match(
        r"(?is)^CREATE\s+(?:OR\s+REPLACE\s+)?TABLE\b",
        statement,
    )
    if create_table is None:
        return False

    depth = 0
    index = create_table.end()
    while index < len(statement):
        current = statement[index]
        if current == "(":
            depth += 1
            index += 1
            continue
        if current == ")":
            depth = max(0, depth - 1)
            index += 1
            continue
        if depth == 0 and (current.isalpha() or current == "_"):
            end = index + 1
            while end < len(statement) and (
                statement[end].isalnum() or statement[end] == "_"
            ):
                end += 1
            if statement[index:end].casefold() == "as":
                return True
            index = end
            continue
        index += 1
    return False


def _contains_executable_sql(code: str) -> bool:
    index = 0
    line_comment = False
    block_comment_depth = 0
    while index < len(code):
        current = code[index]
        following = code[index + 1] if index + 1 < len(code) else ""
        if line_comment:
            if current in "\r\n":
                line_comment = False
            index += 1
            continue
        if block_comment_depth:
            if current == "/" and following == "*":
                block_comment_depth += 1
                index += 2
            elif current == "*" and following == "/":
                block_comment_depth -= 1
                index += 2
            else:
                index += 1
            continue
        if current == "-" and following == "-":
            line_comment = True
            index += 2
        elif current == "/" and following == "*":
            block_comment_depth = 1
            index += 2
        elif not current.isspace():
            return True
        else:
            index += 1
    return False


def _split_sql_statements(code: str) -> list[str]:
    statements: list[str] = []
    start = 0
    index = 0
    quote: str | None = None
    bracket_identifier = False
    line_comment = False
    block_comment_depth = 0
    while index < len(code):
        current = code[index]
        following = code[index + 1] if index + 1 < len(code) else ""
        if line_comment:
            if current in "\r\n":
                line_comment = False
            index += 1
            continue
        if block_comment_depth:
            if current == "/" and following == "*":
                block_comment_depth += 1
                index += 2
            elif current == "*" and following == "/":
                block_comment_depth -= 1
                index += 2
            else:
                index += 1
            continue
        if bracket_identifier:
            if current == "]" and following == "]":
                index += 2
            elif current == "]":
                bracket_identifier = False
                index += 1
            else:
                index += 1
            continue
        if quote:
            if current == quote and following == quote:
                index += 2
            elif current == quote:
                quote = None
                index += 1
            else:
                index += 1
            continue
        if current == "-" and following == "-":
            line_comment = True
            index += 2
        elif current == "/" and following == "*":
            block_comment_depth = 1
            index += 2
        elif current in {"'", '"', "`"}:
            quote = current
            index += 1
        elif current == "[":
            bracket_identifier = True
            index += 1
        elif current == ";":
            statement = code[start:index].strip()
            if statement and _contains_executable_sql(statement):
                statements.append(statement)
            start = index + 1
            index += 1
        else:
            index += 1
    final_statement = code[start:].strip()
    if final_statement and _contains_executable_sql(final_statement):
        statements.append(final_statement)
    return statements


@dataclass(frozen=True)
class DeltaColumnMappingPlan:
    action: str
    mode: str | None
    offending_columns: tuple[str, ...]


def plan_delta_column_mapping(
    column_names: Iterable[str],
    *,
    target_exists: bool,
    existing_mode: str | None = None,
    downstream_supports_name_mapping: bool | None = None,
) -> DeltaColumnMappingPlan:
    names = tuple(column_names)
    if not names or any(not isinstance(name, str) or not name for name in names):
        raise MigrationBlocked("Delta column planning requires non-empty string column names")
    normalized_names = [name.casefold() for name in names]
    if len(set(normalized_names)) != len(normalized_names):
        raise MigrationBlocked("Delta column names must be unique ignoring case")

    offending = tuple(
        name for name in names if any(character in DELTA_UNSAFE_COLUMN_CHARACTERS for character in name)
    )
    normalized_existing_mode = existing_mode.casefold() if isinstance(existing_mode, str) else None
    if normalized_existing_mode == "none":
        normalized_existing_mode = None
    if target_exists:
        if normalized_existing_mode not in {None, "name", "id"}:
            raise MigrationBlocked("Existing target has an unrecognized Delta column mapping mode")
        if offending and normalized_existing_mode not in {"name", "id"}:
            raise MigrationBlocked(
                "Existing target has Delta-unsafe logical column names but no compatible column mapping mode"
            )
        if (
            offending
            and normalized_existing_mode == "name"
            and downstream_supports_name_mapping is not True
        ):
            raise MigrationBlocked(
                "Existing target Delta name mapping requires explicit downstream compatibility approval"
            )
        return DeltaColumnMappingPlan("ReuseExisting", normalized_existing_mode, offending)
    if not offending:
        return DeltaColumnMappingPlan("Create", None, ())
    if downstream_supports_name_mapping is not True:
        raise MigrationBlocked(
            "Delta name column mapping requires an explicit downstream compatibility approval"
        )
    return DeltaColumnMappingPlan("Create", "name", offending)


def delta_table_properties_sql(plan: DeltaColumnMappingPlan) -> str:
    if plan.action != "Create":
        raise MigrationBlocked("Table properties can be generated only for a new target table")
    return (
        "\nTBLPROPERTIES ('delta.columnMapping.mode' = 'name')"
        if plan.mode == "name"
        else ""
    )


def validate_notebook_definition_request(
    payload: Mapping[str, Any],
    *,
    require_item_metadata: bool,
    expected_lakehouse_binding: Mapping[str, str],
) -> bytes:
    if require_item_metadata:
        if not isinstance(payload.get("displayName"), str) or not payload["displayName"].strip():
            raise MigrationBlocked("Notebook create request requires a non-empty displayName")
        if payload.get("type") != "Notebook":
            raise MigrationBlocked("Notebook create request type must be Notebook")

    definition = payload.get("definition")
    if not isinstance(definition, Mapping):
        raise MigrationBlocked("Notebook request requires a definition object")
    if definition.get("format") != "ipynb":
        raise MigrationBlocked("Notebook definition format must be ipynb")
    parts = definition.get("parts")
    if not isinstance(parts, list) or not parts:
        raise MigrationBlocked("Notebook definition requires at least one definition part")

    notebook_parts = []
    for index, part in enumerate(parts):
        if not isinstance(part, Mapping):
            raise MigrationBlocked(f"Notebook definition part {index} must be a JSON object")
        path = part.get("path")
        if not isinstance(path, str) or not path.strip():
            raise MigrationBlocked(f"Notebook definition part {index} requires a non-empty path")
        if part.get("payloadType") != "InlineBase64":
            raise MigrationBlocked(f"Notebook definition part {path} must use InlineBase64")
        encoded = part.get("payload")
        if not isinstance(encoded, str) or not encoded:
            raise MigrationBlocked(f"Notebook definition part {path} requires a base64 payload")
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exception:
            raise MigrationBlocked(f"Notebook definition part {path} has invalid base64") from exception
        if path.casefold().endswith(".ipynb") and path != "notebook-content.ipynb":
            raise MigrationBlocked(
                "Notebook definition content part path must be notebook-content.ipynb"
            )
        if path == "notebook-content.ipynb":
            notebook_parts.append((path, decoded))

    if len(notebook_parts) != 1:
        raise MigrationBlocked("Notebook definition must contain exactly one .ipynb part")
    notebook_path, notebook_bytes = notebook_parts[0]
    try:
        notebook = json.loads(notebook_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exception:
        raise MigrationBlocked(f"Notebook definition part {notebook_path} is not valid notebook JSON") from exception
    if not isinstance(notebook, Mapping) or notebook.get("nbformat") != 4:
        raise MigrationBlocked(f"Notebook definition part {notebook_path} must use nbformat 4")
    metadata = notebook.get("metadata")
    language_info = metadata.get("language_info") if isinstance(metadata, Mapping) else None
    if not isinstance(language_info, Mapping) or language_info.get("name") != "python":
        raise MigrationBlocked(
            f"Notebook definition part {notebook_path} must declare metadata.language_info.name as python"
        )
    dependencies = metadata.get("dependencies") if isinstance(metadata, Mapping) else None
    binding = dependencies.get("lakehouse") if isinstance(dependencies, Mapping) else None
    required_binding_keys = (
        "default_lakehouse",
        "default_lakehouse_workspace_id",
        "default_lakehouse_name",
    )
    missing_binding_keys = [
        key
        for key in required_binding_keys
        if not isinstance(binding, Mapping)
        or not isinstance(binding.get(key), str)
        or not binding[key]
    ]
    mismatched_binding_keys = [
        key
        for key in required_binding_keys
        if isinstance(binding, Mapping)
        and isinstance(binding.get(key), str)
        and binding[key]
        and binding[key] != expected_lakehouse_binding.get(key)
    ]
    if missing_binding_keys or mismatched_binding_keys:
        details = []
        if missing_binding_keys:
            details.append(f"missing or empty keys: {', '.join(missing_binding_keys)}")
        if mismatched_binding_keys:
            details.append(f"mismatched keys: {', '.join(mismatched_binding_keys)}")
        raise MigrationBlocked(
            "Notebook definition does not match the expected default Lakehouse binding "
            f"({'; '.join(details)})"
        )
    trident = metadata.get("trident") if isinstance(metadata, Mapping) else None
    if isinstance(trident, Mapping) and "lakehouse" in trident:
        raise MigrationBlocked(
            "Notebook definition must not place the Lakehouse binding under metadata.trident.lakehouse"
        )
    return canonical_json(payload)


@contextmanager
def notebook_request_body_file(
    payload: Mapping[str, Any],
    *,
    require_item_metadata: bool,
    expected_lakehouse_binding: Mapping[str, str],
    directory: Path,
) -> Iterator[Path]:
    request_bytes = validate_notebook_definition_request(
        payload,
        require_item_metadata=require_item_metadata,
        expected_lakehouse_binding=expected_lakehouse_binding,
    )
    target_directory = directory.resolve()
    target_directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="synapse-notebook-request-",
        suffix=".json",
        dir=target_directory,
    )
    request_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(request_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        yield request_path
    finally:
        request_path.unlink(missing_ok=True)


def az_rest_file_body_argument(path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_file():
        raise MigrationBlocked(f"Fabric request body file does not exist: {resolved}")
    return f"@{resolved}"


def _is_safe_parameter_default(value: ast.expr | None) -> bool:
    if isinstance(value, ast.Constant):
        return value.value is None or isinstance(value.value, (str, int, float, bool))
    if (
        isinstance(value, ast.UnaryOp)
        and isinstance(value.op, (ast.UAdd, ast.USub))
        and isinstance(value.operand, ast.Constant)
        and isinstance(value.operand.value, (int, float))
        and not isinstance(value.operand.value, bool)
    ):
        return True
    return False


def _spark_conf_parameter_name(value: ast.expr, parameter_names: set[str]) -> str | None:
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "str"
        and len(value.args) == 1
        and not value.keywords
        and isinstance(value.args[0], ast.Name)
        and value.args[0].id in parameter_names
    ):
        return value.args[0].id
    return None


def _is_spark_conf_set_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "set"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "conf"
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "spark"
    )


def _attribute_root_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute):
        return _attribute_root_name(node.value)
    if isinstance(node, ast.Call):
        return _attribute_root_name(node.func)
    if isinstance(node, ast.Subscript):
        return _attribute_root_name(node.value)
    if isinstance(node, ast.Name):
        return node.id
    return None


def _is_likely_dataframe_name(name: str) -> bool:
    lowered = name.lower()
    return lowered in {"df", "dataframe", "data_frame"} or lowered.endswith("_df") or lowered.endswith("dataframe")


def _is_forbidden_bridge_attribute(node: ast.AST) -> bool:
    if not isinstance(node, ast.Attribute):
        return False
    root_name = _attribute_root_name(node)
    if node.attr in FORBIDDEN_SPARK_ATTRIBUTES and root_name == "spark":
        return True
    if node.attr in FORBIDDEN_DATAFRAME_ATTRIBUTES and root_name is not None:
        return _is_likely_dataframe_name(root_name)
    return node.attr == "exit" and root_name in FORBIDDEN_EXIT_ROOTS


def _is_parameter_string_expression(node: ast.AST, parameter_names: set[str]) -> bool:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "str"
        and len(node.args) == 1
        and not node.keywords
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id in parameter_names
    ):
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ALLOWED_BRIDGE_METHOD_CALLS
        and not node.args
        and not node.keywords
        and _is_parameter_string_expression(node.func.value, parameter_names)
    )


def _is_allowed_bridge_type_expression(node: ast.AST) -> bool:
    allowed_type_names = {"bool", "float", "int", "str"}
    if isinstance(node, ast.Name):
        return node.id in allowed_type_names
    return (
        isinstance(node, ast.Tuple)
        and 1 <= len(node.elts) <= len(allowed_type_names)
        and all(
            isinstance(element, ast.Name) and element.id in allowed_type_names
            for element in node.elts
        )
        and len({element.id for element in node.elts}) == len(node.elts)
    )


def _is_allowed_bridge_call(call: ast.Call, parameter_names: set[str]) -> bool:
    if _is_spark_conf_set_call(call):
        return True
    if isinstance(call.func, ast.Name):
        if call.keywords:
            return False
        if call.func.id == "ValueError":
            return (
                len(call.args) == 1
                and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, str)
            )
        if call.func.id == "str":
            return (
                len(call.args) == 1
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id in parameter_names
            )
        if call.func.id == "len":
            return len(call.args) == 1 and _is_parameter_string_expression(
                call.args[0], parameter_names
            )
        if call.func.id == "isinstance":
            return (
                len(call.args) == 2
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id in parameter_names
                and _is_allowed_bridge_type_expression(call.args[1])
            )
        return False
    if not isinstance(call.func, ast.Attribute):
        return False
    if (
        call.func.attr == "fullmatch"
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "re"
    ):
        return (
            len(call.args) == 2
            and not call.keywords
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
            and _is_parameter_string_expression(call.args[1], parameter_names)
        )
    return (
        call.func.attr in ALLOWED_BRIDGE_METHOD_CALLS
        and not call.args
        and not call.keywords
        and _is_parameter_string_expression(call.func.value, parameter_names)
    )


def _has_only_allowed_bridge_statements(
    bridge_tree: ast.Module, parameter_names: set[str]
) -> bool:
    for statement in bridge_tree.body:
        if isinstance(statement, ast.Import):
            continue
        if isinstance(statement, ast.Expr):
            if not _is_spark_conf_set_call(statement.value):
                return False
            continue
        if not isinstance(statement, ast.If):
            return False
        for nested_statement in statement.body + statement.orelse:
            if isinstance(nested_statement, ast.Raise):
                continue
            if _assigned_parameter(nested_statement, parameter_names) is not None:
                continue
            return False
    return True


def _referenced_parameters(node: ast.AST, parameter_names: set[str]) -> set[str]:
    return {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and child.id in parameter_names
    }


def _assigned_parameter(statement: ast.stmt, parameter_names: set[str]) -> str | None:
    if isinstance(statement, ast.Assign):
        targets = statement.targets
    elif isinstance(statement, ast.AnnAssign):
        targets = [statement.target]
    else:
        return None
    if len(targets) != 1 or not isinstance(targets[0], ast.Name):
        return None
    return targets[0].id if targets[0].id in parameter_names else None


def _guards_reserved_null_token(statement: ast.If, parameter_name: str) -> bool:
    return (
        _has_direct_raise(statement)
        and isinstance(statement.test, ast.Compare)
        and len(statement.test.ops) == 1
        and isinstance(statement.test.ops[0], ast.Eq)
        and len(statement.test.comparators) == 1
        and (
            (
                isinstance(statement.test.left, ast.Name)
                and statement.test.left.id == parameter_name
                and isinstance(statement.test.comparators[0], ast.Constant)
                and statement.test.comparators[0].value == SQL_NULL_SENTINEL
            )
            or (
                isinstance(statement.test.left, ast.Constant)
                and statement.test.left.value == SQL_NULL_SENTINEL
                and isinstance(statement.test.comparators[0], ast.Name)
                and statement.test.comparators[0].id == parameter_name
            )
        )
    )


def _has_direct_raise(statement: ast.If) -> bool:
    return (
        len(statement.body) == 1
        and isinstance(statement.body[0], ast.Raise)
        and not statement.orelse
    )


def _decimal_validation_contract(validation_pattern: str) -> str | None:
    decimal_match = re.fullmatch(
        r"\[\+\-\]\?\[0-9\]\{1,([1-9][0-9]*)\}(?:\\\.\[0-9\]\{([1-9][0-9]*)\})?",
        validation_pattern,
    )
    if decimal_match is not None:
        integer_digits = int(decimal_match.group(1))
        scale = int(decimal_match.group(2) or 0)
        precision = integer_digits + scale
        if precision <= 38:
            return f"decimal:{precision}:{scale}"
        return None
    zero_integral_decimal_match = re.fullmatch(
        r"\[\+\-\]\?0\\\.\[0-9\]\{([1-9][0-9]*)\}",
        validation_pattern,
    )
    if zero_integral_decimal_match is None:
        return None
    scale = int(zero_integral_decimal_match.group(1))
    if scale <= 38:
        return f"decimal:{scale}:{scale}"
    return None


def _parameter_validation_kinds(
    test: ast.expr,
    parameter_name: str,
    allow_empty_string: bool = False,
) -> set[str]:
    kinds: set[str] = set()
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        non_null_terms = [
            term
            for term in test.values
            if isinstance(term, ast.Compare)
            and isinstance(term.left, ast.Name)
            and term.left.id == parameter_name
            and len(term.ops) == 1
            and isinstance(term.ops[0], ast.IsNot)
            and len(term.comparators) == 1
            and isinstance(term.comparators[0], ast.Constant)
            and term.comparators[0].value is None
        ]
        if len(non_null_terms) == 1 and len(test.values) == 2:
            other_term = next(term for term in test.values if term is not non_null_terms[0])
            other_kinds = _parameter_validation_kinds(
                other_term, parameter_name, allow_empty_string
            )
            if "lexical" in other_kinds:
                kinds.update(other_kinds)
                kinds.add("none_safe_lexical")
        return kinds
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
        lexical_terms = 0
        for term in test.values:
            term_kinds = _parameter_validation_kinds(
                term, parameter_name, allow_empty_string
            )
            if not term_kinds:
                return set()
            if "lexical" in term_kinds:
                lexical_terms += 1
            kinds.update(term_kinds)
        if lexical_terms > 1:
            return set()
        return kinds
    if (
        isinstance(test, ast.UnaryOp)
        and isinstance(test.op, ast.Not)
        and isinstance(test.operand, ast.Call)
        and isinstance(test.operand.func, ast.Attribute)
        and test.operand.func.attr == "strip"
        and not test.operand.args
        and not test.operand.keywords
        and _spark_conf_parameter_name(
            test.operand.func.value, {parameter_name}
        ) == parameter_name
    ):
        return {"blank"}
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and len(test.comparators) == 1:
        comparator = test.comparators[0]
        if (
            isinstance(test.left, ast.Name)
            and test.left.id == parameter_name
            and isinstance(test.ops[0], ast.Is)
            and isinstance(comparator, ast.Constant)
            and comparator.value is None
        ):
            kinds.add("missing")
        elif (
            isinstance(test.left, ast.Call)
            and isinstance(test.left.func, ast.Attribute)
            and isinstance(test.left.func.value, ast.Name)
            and test.left.func.value.id == "re"
            and test.left.func.attr == "fullmatch"
            and len(test.left.args) == 2
            and isinstance(test.left.args[0], ast.Constant)
            and isinstance(test.left.args[0].value, str)
            and (
                test.left.args[0].value
                in {
                    r"[+-]?[0-9]+",
                    r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
                    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?",
                    r"(?i:true|false|1|0)",
                    r"[A-Za-z0-9 _.-]+",
                }
                or (
                    allow_empty_string
                    and test.left.args[0].value == r"[A-Za-z0-9 _.-]*"
                )
                or _decimal_validation_contract(test.left.args[0].value) is not None
            )
            and _spark_conf_parameter_name(
                test.left.args[1], {parameter_name}
            ) == parameter_name
            and isinstance(test.ops[0], ast.Is)
            and isinstance(comparator, ast.Constant)
            and comparator.value is None
        ):
            kinds.add("lexical")
            validation_pattern = test.left.args[0].value
            validation_contracts = {
                r"[+-]?[0-9]+": "integer",
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}": "date",
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?": "timestamp",
                r"(?i:true|false|1|0)": "boolean",
                r"[A-Za-z0-9 _.-]+": "string",
            }
            validation_contract = validation_contracts.get(validation_pattern)
            if validation_contract is None and allow_empty_string and validation_pattern == r"[A-Za-z0-9 _.-]*":
                validation_contract = "nullable-string"
            if validation_contract is None:
                validation_contract = _decimal_validation_contract(validation_pattern)
            if validation_contract is not None:
                kinds.add(f"contract:{validation_contract}")
            if validation_pattern == r"[A-Za-z0-9 _.-]+":
                kinds.add("non_nullable_string")
    return kinds


def _tests_parameter_is_none(test: ast.expr, parameter_name: str) -> bool:
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == parameter_name
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Is)
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value is None
    )


def _bridge_has_validation_before_transport(
    bridge_tree: ast.Module,
    parameter_names: set[str],
    parameter_defaults: Mapping[str, ast.expr],
    nullable_parameters: set[str],
    parameter_validations: Mapping[str, str],
) -> bool:
    none_default_parameters = {
        parameter_name
        for parameter_name, default_value in parameter_defaults.items()
        if isinstance(default_value, ast.Constant) and default_value.value is None
    }
    nullable_none_default_parameters = none_default_parameters & nullable_parameters
    required_none_default_parameters = none_default_parameters - nullable_parameters
    non_null_default_parameters = parameter_names - none_default_parameters
    validated_parameters: set[str] = set()
    lexically_validated_parameters: set[str] = set()
    none_safe_lexically_validated_parameters: set[str] = set()
    missing_guarded_parameters: set[str] = set()
    blank_guarded_parameters: set[str] = set()
    non_nullable_string_parameters: set[str] = set()
    default_fallback_parameters: set[str] = set()
    null_normalized_parameters: set[str] = set()
    null_token_guarded_parameters: set[str] = set()
    transport_started = False
    for statement in bridge_tree.body:
        conf_set_calls = [node for node in ast.walk(statement) if _is_spark_conf_set_call(node)]
        if conf_set_calls:
            if (
                validated_parameters != parameter_names
                or len(conf_set_calls) != 1
                or not isinstance(statement, ast.Expr)
                or statement.value is not conf_set_calls[0]
            ):
                return False
            transport_started = True
            continue
        if transport_started:
            return False
        if _assigned_parameter(statement, parameter_names) is not None:
            return False
        if isinstance(statement, ast.If):
            tested_parameters = _referenced_parameters(statement.test, parameter_names)
            if _has_direct_raise(statement):
                recognized_guard = False
                for parameter_name in tested_parameters:
                    validation_kinds = _parameter_validation_kinds(
                        statement.test,
                        parameter_name,
                        parameter_name not in required_none_default_parameters,
                    )
                    if validation_kinds:
                        recognized_guard = True
                        if (
                            parameter_name in non_null_default_parameters
                            and parameter_name not in default_fallback_parameters
                        ):
                            return False
                        validated_parameters.add(parameter_name)
                    if "missing" in validation_kinds:
                        if parameter_name in nullable_none_default_parameters:
                            return False
                        missing_guarded_parameters.add(parameter_name)
                    if "blank" in validation_kinds:
                        blank_guarded_parameters.add(parameter_name)
                    if "lexical" in validation_kinds:
                        expected_validation = parameter_validations.get(parameter_name)
                        if (
                            expected_validation is not None
                            and f"contract:{expected_validation}" not in validation_kinds
                        ):
                            return False
                        lexically_validated_parameters.add(parameter_name)
                    if "none_safe_lexical" in validation_kinds:
                        none_safe_lexically_validated_parameters.add(parameter_name)
                    if "non_nullable_string" in validation_kinds:
                        non_nullable_string_parameters.add(parameter_name)
                reserved_token_guards = {
                    parameter_name
                    for parameter_name in tested_parameters
                    if _guards_reserved_null_token(statement, parameter_name)
                }
                if reserved_token_guards:
                    recognized_guard = True
                    null_token_guarded_parameters.update(reserved_token_guards)
                if not recognized_guard:
                    return False
            if statement.orelse:
                return False
            for nested_statement in statement.body:
                assigned_parameter = _assigned_parameter(nested_statement, parameter_names)
                if assigned_parameter is None:
                    continue
                assigned_value = nested_statement.value
                default_value = parameter_defaults[assigned_parameter]
                exact_default_fallback = (
                    isinstance(assigned_value, ast.expr)
                    and not (
                        isinstance(default_value, ast.Constant)
                        and default_value.value is None
                    )
                    and ast.dump(assigned_value) == ast.dump(default_value)
                )
                null_token_fallback = (
                    isinstance(assigned_value, ast.Constant)
                    and assigned_value.value == SQL_NULL_SENTINEL
                    and assigned_parameter in null_token_guarded_parameters
                    and assigned_parameter in nullable_parameters
                )
                if (
                    assigned_parameter not in tested_parameters
                    or not _tests_parameter_is_none(statement.test, assigned_parameter)
                    or not (exact_default_fallback or null_token_fallback)
                ):
                    return False
                if null_token_fallback:
                    null_normalized_parameters.add(assigned_parameter)
                if exact_default_fallback:
                    default_fallback_parameters.add(assigned_parameter)
                validated_parameters.add(assigned_parameter)
    return (
        validated_parameters == parameter_names
        and lexically_validated_parameters == parameter_names
        and nullable_none_default_parameters <= none_safe_lexically_validated_parameters
        and nullable_none_default_parameters <= null_normalized_parameters
        and required_none_default_parameters <= missing_guarded_parameters
        and non_nullable_string_parameters <= blank_guarded_parameters
        and non_null_default_parameters <= default_fallback_parameters
    )


def validate_spark_sql_notebook(
    notebook: Mapping[str, Any],
    parse_sql: Callable[[str], None],
    expected_procedure_namespace: str | Iterable[str] | None = None,
    nullable_parameters: Iterable[str] = (),
    parameter_validations: Mapping[str, str] | None = None,
    require_parameter_validations: bool = False,
    expected_parameter_keys: Iterable[tuple[str, str]] | None = None,
    expected_parameter_defaults: Mapping[str, object] | None = None,
) -> None:
    nullable_parameter_names = set(nullable_parameters)
    expected_parameter_validations = dict(parameter_validations or {})
    if any(
        not isinstance(parameter_name, str)
        or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", parameter_name) is None
        or not isinstance(validation, str)
        or re.fullmatch(
            r"(?:integer|date|timestamp|boolean|string|nullable-string|"
            r"decimal:[1-9][0-9]?:(?:0|[1-9][0-9]?))",
            validation,
        )
        is None
        for parameter_name, validation in expected_parameter_validations.items()
    ):
        raise MigrationBlocked("Parameter validation contracts must use Name=Kind with a supported kind")
    decimal_contracts = [
        tuple(int(part) for part in validation.split(":")[1:])
        for validation in expected_parameter_validations.values()
        if validation.startswith("decimal:")
    ]
    if any(precision > 38 or scale > precision for precision, scale in decimal_contracts):
        raise MigrationBlocked("Decimal precision must be at most 38 and scale must not exceed precision")
    expected_procedure_namespaces = (
        {expected_procedure_namespace}
        if isinstance(expected_procedure_namespace, str)
        else set(expected_procedure_namespace or ())
    )
    expected_namespaced_parameters = set(expected_parameter_keys or ())
    expected_defaults = dict(expected_parameter_defaults or {})
    if any(
        not isinstance(namespace, str)
        or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", namespace) is None
        for namespace in expected_procedure_namespaces
    ):
        raise MigrationBlocked("Every expected procedure namespace must be a valid Spark configuration key segment")
    if notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
        raise MigrationBlocked("Notebook must be valid nbformat 4 JSON")
    nbformat_minor = notebook.get("nbformat_minor")
    valid_minor_version = (
        isinstance(nbformat_minor, int)
        and not isinstance(nbformat_minor, bool)
        and nbformat_minor >= 5
    )
    if not valid_minor_version:
        raise MigrationBlocked("Notebook must declare nbformat_minor >= 5")
    metadata = notebook.get("metadata")
    language_info = metadata.get("language_info") if isinstance(metadata, Mapping) else None
    language_name = language_info.get("name") if isinstance(language_info, Mapping) else None
    if language_name != "python":
        raise MigrationBlocked("Notebook must declare metadata.language_info.name as python")
    dependencies = metadata.get("dependencies") if isinstance(metadata, Mapping) else None
    lakehouse = dependencies.get("lakehouse") if isinstance(dependencies, Mapping) else None
    required_lakehouse_keys = {
        "default_lakehouse",
        "default_lakehouse_workspace_id",
        "default_lakehouse_name",
    }
    if not isinstance(lakehouse, Mapping) or any(
        not isinstance(lakehouse.get(key), str) or not lakehouse[key].strip()
        for key in required_lakehouse_keys
    ):
        raise MigrationBlocked("Notebook must contain a complete metadata.dependencies.lakehouse binding")
    trident = metadata.get("trident") if isinstance(metadata, Mapping) else None
    if isinstance(trident, Mapping) and "lakehouse" in trident:
        raise MigrationBlocked(
            "Notebook must not place the Lakehouse binding under metadata.trident.lakehouse"
        )
    parsed = 0
    code_cell_index = 0
    parameter_names: set[str] = set()
    parameter_defaults: dict[str, ast.expr] = {}
    referenced_parameter_keys: set[tuple[str, str]] = set()
    cell_ids: set[str] = set()
    for index, cell in enumerate(notebook["cells"]):
        if not isinstance(cell, dict):
            raise MigrationBlocked(f"Notebook cell {index} must be a JSON object (got {type(cell).__name__})")
        cell_id = cell.get("id")
        if (
            not isinstance(cell_id, str)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", cell_id) is None
            or cell_id in cell_ids
        ):
            raise MigrationBlocked(f"Notebook cell {index} must have a unique valid id")
        cell_ids.add(cell_id)
        if not isinstance(cell.get("metadata"), dict) or "source" not in cell:
            raise MigrationBlocked(f"Notebook cell {index} must contain metadata and source")
        cell_type = cell.get("cell_type")
        if cell_type not in {"code", "markdown"}:
            raise MigrationBlocked(f"Notebook cell {index} has unsupported cell_type")
        source_value = cell.get("source", [])
        if isinstance(source_value, str):
            source = source_value
        elif isinstance(source_value, list) and all(isinstance(line, str) for line in source_value):
            source = "".join(source_value)
        else:
            raise MigrationBlocked(f"Notebook cell {index} source must be a string or array of strings")
        if cell_type != "code":
            continue
        if cell.get("outputs") != [] or "execution_count" not in cell or cell["execution_count"] is not None:
            raise MigrationBlocked(
                f"Notebook code cell {index} must have empty outputs and null execution_count"
            )
        stripped = source.lstrip()
        metadata = cell["metadata"]
        tags = metadata.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise MigrationBlocked(f"Notebook cell {index} metadata.tags must be an array of strings")
        if code_cell_index > 0 and "parameters" in tags:
            raise MigrationBlocked("Notebook must contain exactly one parameters tag on the first code cell")
        if stripped.startswith("%%configure"):
            raise MigrationBlocked("Generated migration notebooks must not use %%configure parameter transport")
        if code_cell_index == 0:
            if "parameters" in tags:
                if tags != ["parameters"]:
                    raise MigrationBlocked(
                        'The first code cell metadata.tags must be exactly ["parameters"]'
                    )
                try:
                    parameter_tree = ast.parse(source)
                except SyntaxError as exception:
                    raise MigrationBlocked("The parameter cell must contain valid Python assignments") from exception
                for statement in parameter_tree.body:
                    if isinstance(statement, ast.AnnAssign):
                        raise MigrationBlocked("Every parameter must be assigned a safe scalar default")
                    if not isinstance(statement, ast.Assign):
                        raise MigrationBlocked("The parameter cell may contain only top-level assignments")
                    targets = statement.targets
                    if len(targets) != 1 or not isinstance(targets[0], ast.Name):
                        raise MigrationBlocked("Every parameter must be assigned to one top-level variable")
                    if not _is_safe_parameter_default(statement.value):
                        raise MigrationBlocked("Every parameter must be assigned a safe scalar default")
                    parameter_name = targets[0].id
                    if parameter_name in RESERVED_BRIDGE_PARAMETER_NAMES:
                        raise MigrationBlocked(
                            f"Parameter name {parameter_name} collides with a reserved bridge symbol"
                        )
                    if parameter_name in parameter_names:
                        raise MigrationBlocked("Every parameter must be declared exactly once")
                    parameter_names.add(parameter_name)
                    parameter_defaults[parameter_name] = statement.value
                if not parameter_names:
                    raise MigrationBlocked("The parameter cell must define at least one parameter")
                if expected_defaults:
                    if expected_defaults.keys() != parameter_names:
                        raise MigrationBlocked(
                            "Manifest defaults must exactly cover declared notebook parameters"
                        )
                    for parameter_name, default_expression in parameter_defaults.items():
                        notebook_default = ast.literal_eval(default_expression)
                        manifest_default = expected_defaults[parameter_name]
                        if (
                            type(notebook_default) is not type(manifest_default)
                            or notebook_default != manifest_default
                        ):
                            raise MigrationBlocked(
                                "Notebook parameter default does not match the manifest "
                                f"for {parameter_name}"
                            )
                code_cell_index += 1
                continue
            if re.match(r"%%sql[ \t]*(?:\r?\n|$)", stripped) is None:
                raise MigrationBlocked("The first code cell must be tagged parameters or use %%sql")
        if parameter_names and code_cell_index == 1:
            if require_parameter_validations and not expected_parameter_validations:
                raise MigrationBlocked(
                    "Parameterized notebooks require parameter validation contracts"
                )
            if (
                expected_parameter_validations
                and expected_parameter_validations.keys() != parameter_names
            ):
                raise MigrationBlocked("Parameter validation contracts must exactly cover declared parameters")
            try:
                bridge_tree = ast.parse(source)
                compile(bridge_tree, "<parameter-bridge>", "exec")
            except SyntaxError as exception:
                raise MigrationBlocked("The parameter bridge must contain valid Python") from exception
            bridge_calls = [node for node in ast.walk(bridge_tree) if isinstance(node, ast.Call)]
            conf_set_calls = [call for call in bridge_calls if _is_spark_conf_set_call(call)]
            invalid_imports = [
                node
                for node in ast.walk(bridge_tree)
                if isinstance(node, ast.ImportFrom)
                or (
                    isinstance(node, ast.Import)
                    and any(alias.name != "re" or alias.asname is not None for alias in node.names)
                )
            ]
            uses_re_fullmatch = any(
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "fullmatch"
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "re"
                for call in bridge_calls
            )
            import_re_indexes = [
                index
                for index, statement in enumerate(bridge_tree.body)
                if isinstance(statement, ast.Import)
                and len(statement.names) == 1
                and statement.names[0].name == "re"
                and statement.names[0].asname is None
            ]
            re_use_indexes = [
                index
                for index, statement in enumerate(bridge_tree.body)
                if any(
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "fullmatch"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "re"
                    for node in ast.walk(statement)
                )
            ]
            imports_re_before_use = (
                not uses_re_fullmatch
                or (
                    bool(import_re_indexes)
                    and min(import_re_indexes) < min(re_use_indexes)
                )
            )
            forbidden_calls = [
                call
                for call in bridge_calls
                if not _is_allowed_bridge_call(call, parameter_names)
            ]
            forbidden_attributes = [
                node
                for node in ast.walk(bridge_tree)
                if _is_forbidden_bridge_attribute(node)
            ]
            forbidden_constructs = [
                node
                for node in ast.walk(bridge_tree)
                if isinstance(node, FORBIDDEN_BRIDGE_CONSTRUCTS)
            ]
            transported_parameters: set[str] = set()
            transported_parameter_keys: set[tuple[str, str]] = set()
            transported_namespaces: set[str] = set()
            for call in conf_set_calls:
                if len(call.args) != 2 or call.keywords:
                    raise MigrationBlocked("Every spark.conf.set call must contain one key and one scalar value")
                key = call.args[0]
                if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                    raise MigrationBlocked("Every spark.conf.set key must be a literal string")
                parameter_name = _spark_conf_parameter_name(call.args[1], parameter_names)
                if parameter_name is None:
                    raise MigrationBlocked(
                        "Every spark.conf.set value must be str() of exactly one declared parameter"
                    )
                key_match = re.fullmatch(
                    r"spark\.synapseMigration\.([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)",
                    key.value,
                )
                if key_match is None or key_match.group(2) != parameter_name:
                    raise MigrationBlocked("Every spark.conf.set key must match its declared parameter")
                procedure_namespace = key_match.group(1)
                transported_namespaces.add(procedure_namespace)
                if (
                    expected_procedure_namespaces
                    and procedure_namespace not in expected_procedure_namespaces
                ):
                    if len(expected_procedure_namespaces) == 1:
                        expected_namespace = next(iter(expected_procedure_namespaces))
                        raise MigrationBlocked(
                            "Every spark.conf.set key must use the expected procedure namespace "
                            f"{expected_namespace}"
                        )
                    raise MigrationBlocked(
                        "Every spark.conf.set key must use one of the approved procedure namespaces: "
                        + ", ".join(sorted(expected_procedure_namespaces))
                    )
                parameter_key = (procedure_namespace, parameter_name)
                if parameter_key in transported_parameter_keys:
                    raise MigrationBlocked(
                        "Every namespaced declared parameter must be transported exactly once"
                    )
                transported_parameter_keys.add(parameter_key)
                transported_parameters.add(parameter_name)
            if (
                expected_namespaced_parameters
                and transported_parameter_keys != expected_namespaced_parameters
            ):
                raise MigrationBlocked(
                    "Notebook parameter transports do not exactly match manifest "
                    "namespace and parameter bindings"
                )
            if not expected_procedure_namespaces and len(transported_namespaces) > 1:
                raise MigrationBlocked("Every spark.conf.set key must use one procedure namespace")
            if (
                expected_procedure_namespaces
                and transported_namespaces != expected_procedure_namespaces
            ):
                raise MigrationBlocked(
                    "Every approved parameterized procedure namespace must be transported; expected exactly the approved procedure namespaces: "
                    + ", ".join(sorted(expected_procedure_namespaces))
                )
            if (
                forbidden_attributes
                or invalid_imports
                or not imports_re_before_use
                or forbidden_calls
                or forbidden_constructs
                or not _has_only_allowed_bridge_statements(bridge_tree, parameter_names)
                or transported_parameters != parameter_names
                or not _bridge_has_validation_before_transport(
                    bridge_tree,
                    parameter_names,
                    parameter_defaults,
                    nullable_parameter_names,
                    expected_parameter_validations,
                )
            ):
                raise MigrationBlocked(
                    "The second code cell must be a validation-only Python bridge that transports "
                    "every declared parameter exactly once"
                )
            code_cell_index += 1
            continue
        code_cell_index += 1
        if re.match(r"%%sql[ \t]*(?:\r?\n|$)", stripped) is None:
            raise MigrationBlocked("Every executable transformation cell must use %%sql")
        sql = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        if not sql.strip():
            raise MigrationBlocked("Spark SQL cell cannot be empty")
        referenced_parameter_keys.update(
            re.findall(
                r"\$\{spark\.synapseMigration\.([A-Za-z_][A-Za-z0-9_]*)\."
                r"([A-Za-z_][A-Za-z0-9_]*)\}",
                sql,
            )
        )
        try:
            parse_sql(sql)
        except Exception as exception:
            raise MigrationBlocked(f"Target Spark parser rejected notebook cell {index}: {exception}") from exception
        parsed += 1
    if expected_procedure_namespaces and not parameter_names:
        raise MigrationBlocked(
            "Expected procedure namespaces cannot validate a parameterless notebook; "
            "verify its procedure identity through the approved manifest mapping"
        )
    unknown_nullable_parameters = nullable_parameter_names - parameter_names
    if unknown_nullable_parameters:
        raise MigrationBlocked(
            "Nullable parameter metadata names undeclared parameters: "
            + ", ".join(sorted(unknown_nullable_parameters))
        )
    unknown_validation_parameters = expected_parameter_validations.keys() - parameter_names
    if unknown_validation_parameters:
        raise MigrationBlocked(
            "Parameter validation metadata names undeclared parameters: "
            + ", ".join(sorted(unknown_validation_parameters))
        )
    if (
        expected_namespaced_parameters
        and referenced_parameter_keys != expected_namespaced_parameters
    ):
        raise MigrationBlocked(
            "Notebook SQL substitutions do not exactly match manifest namespace "
            "and parameter bindings"
        )
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
    started_at: str | None = None,
    completed_at: str | None = None,
    duration_seconds: float | None = None,
    attempt: int | None = None,
) -> dict[str, Any]:
    if status == "Succeeded" and (
        not isinstance(input_hash, str)
        or not input_hash.strip()
        or not isinstance(output_hash, str)
        or not output_hash.strip()
    ):
        raise MigrationBlocked(
            "Succeeded checkpoints require non-empty input and output hashes"
        )
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
                and item["sourceId"] == source_id
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
        if started_at is not None:
            value["startedAt"] = started_at
        if completed_at is not None:
            value["completedAt"] = completed_at
        if duration_seconds is not None:
            value["durationSeconds"] = duration_seconds
        if attempt is not None:
            value["attempt"] = attempt
        if checkpoint is None:
            objects.append(value)
        else:
            attempt_history = checkpoint.get("attemptHistory", [])
            if not isinstance(attempt_history, list) or not all(
                isinstance(item, Mapping) for item in attempt_history
            ):
                raise MigrationBlocked("Checkpoint attemptHistory must be an array of JSON objects")
            prior_attempt = checkpoint.get("attempt")
            if (
                attempt is not None
                and isinstance(prior_attempt, int)
                and not isinstance(prior_attempt, bool)
                and attempt > prior_attempt
            ):
                prior_record = {
                    key: prior_value
                    for key, prior_value in checkpoint.items()
                    if key != "attemptHistory"
                }
                attempt_history = [*attempt_history, prior_record]
            if attempt_history:
                value["attemptHistory"] = attempt_history
            checkpoint.clear()
            checkpoint.update(value)

    return update_manifest(path, mutate)


def checkpoint_is_reusable(
    item: Mapping[str, Any],
    input_hash: str,
    current_output_hash: str,
) -> bool:
    return (
        item.get("status") == "Succeeded"
        and item.get("inputHash") == input_hash
        and item.get("outputHash") == current_output_hash
    )


@dataclass(frozen=True)
class SchemaDeploymentObject:
    source_id: str
    sql: str
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class SchemaDeploymentResult:
    source_id: str
    status: str
    statement_id: str | None
    reused_checkpoint: bool
    blocker: str | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exception:
        raise MigrationBlocked(f"Invalid telemetry timestamp: {value}") from exception
    if parsed.tzinfo is None:
        raise MigrationBlocked("Telemetry timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def record_phase_telemetry(
    path: Path,
    *,
    phase: str,
    status: str,
    started_at: str,
    completed_at: str,
    object_counts: Mapping[str, int],
    retry_count: int,
    token_usage: int | None = None,
) -> dict[str, Any]:
    if not phase.strip():
        raise MigrationBlocked("Telemetry phase cannot be empty")
    if status not in {"Completed", "Failed", "Blocked", "Partial"}:
        raise MigrationBlocked(f"Unsupported phase telemetry status: {status}")
    if retry_count < 0 or any(
        not isinstance(value, int) or value < 0 for value in object_counts.values()
    ):
        raise MigrationBlocked("Telemetry counts cannot be negative")
    if token_usage is not None and token_usage < 0:
        raise MigrationBlocked("Token usage cannot be negative")
    started = _parse_utc_timestamp(started_at)
    completed = _parse_utc_timestamp(completed_at)
    if completed < started:
        raise MigrationBlocked("Telemetry completion cannot precede its start")

    def mutate(manifest: dict[str, Any]) -> None:
        telemetry = manifest.setdefault("telemetry", [])
        if not isinstance(telemetry, list):
            raise MigrationBlocked("Migration manifest telemetry must be an array")
        telemetry.append(
            {
                "phase": phase,
                "status": status,
                "startedAt": started_at,
                "completedAt": completed_at,
                "durationSeconds": round((completed - started).total_seconds(), 3),
                "objectCounts": dict(sorted(object_counts.items())),
                "retryCount": retry_count,
                "tokenUsage": token_usage,
                "tokenUsageStatus": "Reported" if token_usage is not None else "Unavailable",
            }
        )

    return update_manifest(path, mutate)


def _ordered_schema_objects(
    objects: Iterable[SchemaDeploymentObject],
    satisfied_dependencies: Iterable[str],
) -> list[SchemaDeploymentObject]:
    supplied = list(objects)
    by_id: dict[str, SchemaDeploymentObject] = {}
    for item in supplied:
        if not item.source_id.strip():
            raise MigrationBlocked("Schema deployment source IDs cannot be empty")
        key = item.source_id
        if key in by_id:
            raise MigrationBlocked(f"Duplicate schema deployment source ID: {item.source_id}")
        require_single_schema_statement(item.sql)
        by_id[key] = item

    satisfied = set(satisfied_dependencies)
    unknown = sorted(
        dependency
        for item in supplied
        for dependency in item.dependencies
        if dependency not in by_id and dependency not in satisfied
    )
    if unknown:
        raise MigrationBlocked(
            f"Schema dependencies are not supplied or satisfied: {', '.join(unknown)}"
        )

    ordered: list[SchemaDeploymentObject] = []
    pending = dict(by_id)
    while pending:
        ready = sorted(
            (
                item
                for item in pending.values()
                if all(dependency not in pending for dependency in item.dependencies)
            ),
            key=lambda item: item.source_id,
        )
        if not ready:
            raise MigrationBlocked(
                "Schema dependency cycle detected: "
                + ", ".join(sorted(item.source_id for item in pending.values()))
            )
        for item in ready:
            ordered.append(item)
            del pending[item.source_id]
    return ordered


def _checkpoint_for_input(
    path: Path,
    *,
    datamart_id: str,
    source_id: str,
    stage: str,
    input_hash: str,
    current_output_hash: str | None,
    allow_succeeded_without_output_hash: bool = False,
) -> Mapping[str, Any] | None:
    if not path.exists():
        return None
    manifest = _load_json_object(path, "Migration manifest")
    recorded_hash = manifest.get("manifestHash")
    if not isinstance(recorded_hash, str) or recorded_hash != sha256_bytes(
        canonical_json({key: value for key, value in manifest.items() if key != "manifestHash"})
    ):
        raise MigrationBlocked("Migration manifest integrity hash is missing or invalid")
    if manifest.get("datamartId") != datamart_id:
        raise MigrationBlocked("Checkpoint datamart does not match the manifest owner")
    objects = manifest.get("objects")
    if not isinstance(objects, list):
        return None
    for item in objects:
        if not (
            isinstance(item, Mapping)
            and isinstance(item.get("sourceId"), str)
            and item["sourceId"] == source_id
            and isinstance(item.get("stage"), str)
            and item["stage"].casefold() == stage.casefold()
        ):
            continue
        if item.get("status") == "InProgress":
            raise MigrationBlocked(
                f"Schema deployment state is indeterminate for {source_id}; "
                "verify the target manually before resuming"
            )
        if (
            item.get("status") == "Succeeded"
            and current_output_hash is None
            and not allow_succeeded_without_output_hash
        ):
            raise MigrationBlocked(
                f"Target readback is unavailable for previously succeeded {source_id}; "
                "verify the target manually before resuming"
            )
        if current_output_hash is not None and checkpoint_is_reusable(
            item,
            input_hash,
            current_output_hash,
        ):
            return item
    return None


def _next_checkpoint_attempt(
    path: Path,
    *,
    datamart_id: str,
    source_id: str,
    stage: str,
) -> int:
    if not path.exists():
        return 1
    manifest = _load_json_object(path, "Migration manifest")
    recorded_hash = manifest.get("manifestHash")
    if not isinstance(recorded_hash, str) or recorded_hash != sha256_bytes(
        canonical_json({key: value for key, value in manifest.items() if key != "manifestHash"})
    ):
        raise MigrationBlocked("Migration manifest integrity hash is missing or invalid")
    if manifest.get("datamartId") != datamart_id:
        raise MigrationBlocked("Checkpoint datamart does not match the manifest owner")
    objects = manifest.get("objects")
    if not isinstance(objects, list):
        return 1
    checkpoint = next(
        (
            item
            for item in objects
            if isinstance(item, Mapping)
            and isinstance(item.get("sourceId"), str)
            and item["sourceId"] == source_id
            and isinstance(item.get("stage"), str)
            and item["stage"].casefold() == stage.casefold()
        ),
        None,
    )
    if checkpoint is None:
        return 1
    prior_attempt = checkpoint.get("attempt")
    if prior_attempt is None:
        return 1
    if (
        not isinstance(prior_attempt, int)
        or isinstance(prior_attempt, bool)
        or prior_attempt < 1
    ):
        raise MigrationBlocked("Checkpoint attempt must be a positive integer")
    return prior_attempt + 1


def sanitize_error_message(message: str, *, maximum_length: int = 500) -> str:
    sanitized = " ".join(message.split())
    sanitized = SENSITIVE_DOUBLE_QUOTED_ERROR_VALUE_PATTERN.sub(
        lambda match: f'{match.group(1)}"[REDACTED]"',
        sanitized,
    )
    sanitized = SENSITIVE_SINGLE_QUOTED_ERROR_VALUE_PATTERN.sub(
        lambda match: f"{match.group(1)}'[REDACTED]'",
        sanitized,
    )
    sanitized = SENSITIVE_ERROR_VALUE_PATTERN.sub(
        lambda match: f"{match.group(1)}[REDACTED]",
        sanitized,
    )
    sanitized = SENSITIVE_QUERY_VALUE_PATTERN.sub(
        lambda match: f"{match.group(1)}[REDACTED]",
        sanitized,
    )
    if len(sanitized) <= maximum_length:
        return sanitized
    return f"{sanitized[: maximum_length - 3]}..."


def execute_livy_schema_statement(
    transport: Transport,
    *,
    statements_url: str,
    sql: str,
    timeout_seconds: float = 900,
    poll_interval_seconds: float = 2,
    max_retry_attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
    transport_error_types: tuple[type[Exception], ...] = (OSError,),
) -> tuple[str, Mapping[str, Any]]:
    if max_retry_attempts < 1:
        raise ValueError("max_retry_attempts must be at least 1")
    retryable_poll_statuses = {429, 500, 502, 503, 504}
    response: Response | None = None
    for retry_index in range(max_retry_attempts):
        try:
            response = transport(
                "POST",
                statements_url,
                headers={**SKILL_HEADER, "Content-Type": "application/json"},
                json=livy_statement_payload(sql),
            )
        except transport_error_types as exception:
            raise LivySubmissionIndeterminate(
                "Livy statement transport failed during submission: "
                f"{sanitize_error_message(str(exception))}; verify the target manually"
            ) from exception
        if response.status_code == 429 and retry_index + 1 < max_retry_attempts:
            sleep(min(poll_interval_seconds * (2**retry_index), 30))
            continue
        break
    if response is None:
        raise RuntimeError("Livy submission retry loop completed without a response")
    if response.status_code in {500, 502, 503, 504}:
        raise LivySubmissionIndeterminate(
            f"Livy statement submission returned HTTP {response.status_code}; "
            "the DDL outcome is indeterminate, so verify the target manually"
        )
    if response.status_code not in {200, 201, 202}:
        raise MigrationBlocked(
            f"Livy statement submission failed with HTTP {response.status_code}: "
            f"{sanitize_error_message(response.content.decode('utf-8', errors='replace'))}"
        )
    try:
        submitted = _json_object(response, "Livy statement submission")
    except MigrationBlocked as exception:
        raise LivySubmissionIndeterminate(
            f"Livy accepted the statement but its submission response was invalid: {exception}; "
            "verify the target manually"
        ) from exception
    statement_id = submitted.get("id")
    if not isinstance(statement_id, (str, int)):
        raise LivySubmissionIndeterminate(
            "Livy accepted the statement but did not return an id; verify the target manually"
        )
    statement_id_text = str(statement_id)
    poll_url = f"{statements_url.rstrip('/')}/{statement_id_text}"
    deadline = time.monotonic() + timeout_seconds

    def sleep_before_deadline(delay_seconds: float) -> None:
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            raise LivySubmissionIndeterminate(
                f"Timed out waiting for Livy statement {statement_id_text} after {timeout_seconds}s",
                statement_id_text,
            )
        sleep(min(delay_seconds, remaining_seconds))
        if time.monotonic() >= deadline:
            raise LivySubmissionIndeterminate(
                f"Timed out waiting for Livy statement {statement_id_text} after {timeout_seconds}s",
                statement_id_text,
            )

    retry_index = 0
    while True:
        try:
            poll_response = transport("GET", poll_url, headers=dict(SKILL_HEADER))
        except transport_error_types as exception:
            if retry_index + 1 >= max_retry_attempts:
                raise LivySubmissionIndeterminate(
                    f"Livy statement transport failed while polling {statement_id_text}: "
                    f"{sanitize_error_message(str(exception))}",
                    statement_id_text,
                ) from exception
            sleep_before_deadline(min(poll_interval_seconds * (2**retry_index), 30))
            retry_index += 1
            continue
        if poll_response.status_code in retryable_poll_statuses:
            if retry_index + 1 >= max_retry_attempts:
                raise LivySubmissionIndeterminate(
                    f"Livy statement poll exhausted retries with HTTP {poll_response.status_code}",
                    statement_id_text,
                )
            sleep_before_deadline(min(poll_interval_seconds * (2**retry_index), 30))
            retry_index += 1
            continue
        if poll_response.status_code != 200:
            raise LivySubmissionIndeterminate(
                f"Livy statement poll failed with HTTP {poll_response.status_code}: "
                f"{sanitize_error_message(poll_response.content.decode('utf-8', errors='replace'))}",
                statement_id_text,
            )
        retry_index = 0
        try:
            statement = _json_object(poll_response, "Livy statement poll")
        except MigrationBlocked as exception:
            raise LivySubmissionIndeterminate(
                f"Livy statement {statement_id_text} returned an invalid poll response: {exception}; "
                "verify the target manually",
                statement_id_text,
            ) from exception
        state = statement.get("state")
        if isinstance(state, str) and state.casefold() in LIVY_TERMINAL_STATEMENT_STATES:
            if state.casefold() != "available":
                raise LivySubmissionIndeterminate(
                    f"Livy statement {statement_id_text} finished in state {state}: "
                    f"{sanitize_error_message(json.dumps(statement.get('output'), sort_keys=True))}",
                    statement_id_text,
                )
            output = statement.get("output")
            if not isinstance(output, Mapping) or output.get("status") != "ok":
                raise LivySubmissionIndeterminate(
                    f"Livy statement {statement_id_text} returned a non-success output: "
                    f"{sanitize_error_message(json.dumps(output, sort_keys=True))}",
                    statement_id_text,
                )
            return statement_id_text, statement
        if time.monotonic() >= deadline:
            raise LivySubmissionIndeterminate(
                f"Timed out waiting for Livy statement {statement_id_text} after {timeout_seconds}s",
                statement_id_text,
            )
        sleep_before_deadline(poll_interval_seconds)


def deploy_schema_objects(
    transport: Transport,
    *,
    statements_url: str,
    manifest_path: Path,
    datamart_id: str,
    objects: Iterable[SchemaDeploymentObject],
    read_target_state: Callable[[SchemaDeploymentObject], Mapping[str, Any] | None],
    satisfied_dependencies: Iterable[str] = (),
    now: Callable[[], str] = _utc_now,
    sleep: Callable[[float], None] = time.sleep,
    timeout_seconds: float = 900,
    poll_interval_seconds: float = 2,
    transport_error_types: tuple[type[Exception], ...] = (OSError,),
) -> list[SchemaDeploymentResult]:
    ordered = _ordered_schema_objects(objects, satisfied_dependencies)
    failed_or_blocked: set[str] = set()
    results: list[SchemaDeploymentResult] = []
    readback_error_types = (MigrationBlocked,) + transport_error_types
    for item in ordered:
        blocked_dependency = next(
            (
                dependency
                for dependency in item.dependencies
                if dependency in failed_or_blocked
            ),
            None,
        )
        input_hash = sha256_bytes(require_single_schema_statement(item.sql).encode("utf-8"))
        if blocked_dependency is not None:
            _checkpoint_for_input(
                manifest_path,
                datamart_id=datamart_id,
                source_id=item.source_id,
                stage="DeploySchema",
                input_hash=input_hash,
                current_output_hash=None,
                allow_succeeded_without_output_hash=True,
            )
            blocker = f"Dependency did not complete: {blocked_dependency}"
            attempt = _next_checkpoint_attempt(
                manifest_path,
                datamart_id=datamart_id,
                source_id=item.source_id,
                stage="DeploySchema",
            )
            record_checkpoint(
                manifest_path,
                source_id=item.source_id,
                stage="DeploySchema",
                status="Blocked",
                datamart_id=datamart_id,
                input_hash=input_hash,
                blocker=blocker,
                attempt=attempt,
            )
            failed_or_blocked.add(item.source_id)
            results.append(
                SchemaDeploymentResult(item.source_id, "Blocked", None, False, blocker)
            )
            continue

        try:
            target_state = read_target_state(item)
        except readback_error_types as exception:
            try:
                _checkpoint_for_input(
                    manifest_path,
                    datamart_id=datamart_id,
                    source_id=item.source_id,
                    stage="DeploySchema",
                    input_hash=input_hash,
                    current_output_hash=None,
                )
            except MigrationBlocked as checkpoint_exception:
                raise MigrationBlocked(
                    sanitize_error_message(
                        f"{checkpoint_exception}; target readback failed: {exception}"
                    )
                ) from exception
            blocker = sanitize_error_message(
                f"Target readback is unavailable for {item.source_id}; "
                f"verify the target manually before resuming: {exception}"
            )
            attempt = _next_checkpoint_attempt(
                manifest_path,
                datamart_id=datamart_id,
                source_id=item.source_id,
                stage="DeploySchema",
            )
            record_checkpoint(
                manifest_path,
                source_id=item.source_id,
                stage="DeploySchema",
                status="Blocked",
                datamart_id=datamart_id,
                input_hash=input_hash,
                blocker=blocker,
                attempt=attempt,
            )
            raise MigrationBlocked(blocker) from exception

        reusable = _checkpoint_for_input(
            manifest_path,
            datamart_id=datamart_id,
            source_id=item.source_id,
            stage="DeploySchema",
            input_hash=input_hash,
            current_output_hash=(
                sha256_bytes(canonical_json(target_state))
                if target_state is not None
                else None
            ),
        )
        if reusable is not None:
            identifiers = reusable.get("identifiers")
            statement_id = (
                identifiers.get("statementId") if isinstance(identifiers, Mapping) else None
            )
            results.append(
                SchemaDeploymentResult(item.source_id, "Succeeded", statement_id, True)
            )
            continue

        attempt = _next_checkpoint_attempt(
            manifest_path,
            datamart_id=datamart_id,
            source_id=item.source_id,
            stage="DeploySchema",
        )
        started_at = now()
        started = _parse_utc_timestamp(started_at)
        record_checkpoint(
            manifest_path,
            source_id=item.source_id,
            stage="DeploySchema",
            status="InProgress",
            datamart_id=datamart_id,
            input_hash=input_hash,
            started_at=started_at,
            attempt=attempt,
        )
        remote_mutated = False
        statement_id: str | None = None
        try:
            statement_id, _statement = execute_livy_schema_statement(
                transport,
                statements_url=statements_url,
                sql=item.sql,
                timeout_seconds=timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
                sleep=sleep,
                transport_error_types=transport_error_types,
            )
            remote_mutated = True
            completed_at = now()
            completed = _parse_utc_timestamp(completed_at)
            target_state = read_target_state(item)
            if target_state is None:
                raise MigrationBlocked(
                    f"Target readback was unavailable after deploying {item.source_id}"
                )
            record_checkpoint(
                manifest_path,
                source_id=item.source_id,
                stage="DeploySchema",
                status="Succeeded",
                datamart_id=datamart_id,
                input_hash=input_hash,
                output_hash=sha256_bytes(canonical_json(target_state)),
                identifiers={"statementId": statement_id},
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=round((completed - started).total_seconds(), 3),
                attempt=attempt,
            )
            results.append(
                SchemaDeploymentResult(item.source_id, "Succeeded", statement_id, False)
            )
        except Exception as exception:
            if remote_mutated or isinstance(exception, LivySubmissionIndeterminate):
                blocker = sanitize_error_message(
                    f"Schema deployment state is indeterminate for {item.source_id}: {exception}; "
                    "verify the target manually before resuming"
                )
                if isinstance(exception, LivySubmissionIndeterminate):
                    statement_id = exception.statement_id
                record_checkpoint(
                    manifest_path,
                    source_id=item.source_id,
                    stage="DeploySchema",
                    status="InProgress",
                    datamart_id=datamart_id,
                    input_hash=input_hash,
                    identifiers=(
                        {"statementId": statement_id} if statement_id is not None else None
                    ),
                    blocker=blocker,
                    started_at=started_at,
                    attempt=attempt,
                )
                raise MigrationBlocked(blocker) from exception
            if not isinstance(exception, readback_error_types):
                raise
            completed_at = now()
            completed = _parse_utc_timestamp(completed_at)
            blocker = sanitize_error_message(str(exception))
            record_checkpoint(
                manifest_path,
                source_id=item.source_id,
                stage="DeploySchema",
                status="Failed",
                datamart_id=datamart_id,
                input_hash=input_hash,
                blocker=blocker,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=round((completed - started).total_seconds(), 3),
                attempt=attempt,
            )
            failed_or_blocked.add(item.source_id)
            results.append(
                SchemaDeploymentResult(item.source_id, "Failed", None, False, blocker)
            )
    return results


def require_schema_ready(manifest: Mapping[str, Any], expected_schema: Mapping[str, Any]) -> None:
    expected_objects = expected_schema.get("objects", [])
    if not isinstance(expected_objects, list) or not expected_objects:
        raise MigrationBlocked("Expected schema must contain at least one object")
    expected_ids = [item.get("sourceStableId") for item in expected_objects if isinstance(item, Mapping)]
    if len(expected_ids) != len(expected_objects) or any(
        not isinstance(source_id, str) or not source_id.strip() for source_id in expected_ids
    ):
        raise MigrationBlocked("Every expected schema object must have a non-empty string sourceStableId")
    expected_id_set = set(expected_ids)
    if len(expected_id_set) != len(expected_ids):
        raise MigrationBlocked("Expected schema sourceStableId values must be unique")

    manifest_objects = manifest.get("objects", [])
    if not isinstance(manifest_objects, list) or not all(isinstance(item, Mapping) for item in manifest_objects):
        raise MigrationBlocked("Schema manifest objects must be an array of JSON objects")

    checkpoints: dict[tuple[str, str], Mapping[str, Any]] = {}
    for item in manifest_objects:
        source_id = item.get("sourceId")
        stage = item.get("stage")
        if not isinstance(source_id, str) or source_id not in expected_id_set:
            continue
        if not isinstance(stage, str) or stage.casefold() not in {"schema", "metadata"}:
            continue
        key = (source_id, stage.casefold())
        if key in checkpoints:
            raise MigrationBlocked("Schema manifest contains a duplicate object checkpoint")
        checkpoints[key] = item

    required = {(source_id, stage) for source_id in expected_ids for stage in ("schema", "metadata")}
    if set(checkpoints) != required or any(
        item.get("status") != "Succeeded"
        or not isinstance(item.get("inputHash"), str)
        or not item["inputHash"].strip()
        or not isinstance(item.get("outputHash"), str)
        or not item["outputHash"].strip()
        for item in checkpoints.values()
    ):
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