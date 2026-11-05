# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
"""Read authoritative capacity metadata and apply the public execution policy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import UUID
from python_runtime import require_supported_python


require_supported_python()


@dataclass(frozen=True)
class CapacityCheck:
    classification: str
    capacity_id: str | None
    sku: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_capacity(
    workspace: dict[str, Any], api_host: str, get_json: Callable[[str], dict[str, Any]],
) -> CapacityCheck:
    """get_json performs authenticated GETs in the already selected tenant."""
    capacity_id = workspace.get("capacityId")
    if not isinstance(capacity_id, str) or not capacity_id.strip():
        return CapacityCheck("unknown", None, None, "Workspace has no capacityId; verify its capacity assignment.")
    try:
        capacity_id = str(UUID(capacity_id.strip()))
    except ValueError:
        return CapacityCheck("unknown", None, None, "Workspace capacityId is invalid; verify metadata before routing.")
    base = f"{api_host}/v1/capacities"
    url = base
    seen = set()
    for _ in range(100):
        if url in seen:
            return CapacityCheck("unknown", capacity_id, None, "Capacity pagination repeated; retry metadata lookup.")
        seen.add(url)
        try:
            page = get_json(url)
        except RuntimeError as exc:
            return CapacityCheck("unknown", capacity_id, None, str(exc))
        rows = page.get("value")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            return CapacityCheck("unknown", capacity_id, None, "Capacities response has invalid value metadata.")
        for row in rows:
            if str(row.get("id", "")).casefold() != capacity_id.casefold():
                continue
            sku = row.get("sku")
            if not isinstance(sku, str) or not sku.strip():
                return CapacityCheck("unknown", capacity_id, None, "Assigned capacity has no authoritative SKU.")
            sku = sku.strip().upper()
            if sku == "FTL64":
                return CapacityCheck("trial", capacity_id, sku, "Trial capacity is blocked by the public execution policy.")
            # This is a nontrial classification, not an AI eligibility allowlist.
            if sku in {"F2", "F4", "F8", "F16", "F32", "F64", "F128", "F256", "F512", "F1024", "F2048",
                       "P1", "P2", "P3", "P4", "P5"}:
                return CapacityCheck("nontrial", capacity_id, sku, "Nontrial SKU; service AI eligibility still applies.")
            return CapacityCheck("unknown", capacity_id, sku, "Unrecognized SKU; trial and AI eligibility are unknown.")
        token = page.get("continuationToken")
        uri = page.get("continuationUri")
        if token is None and uri is None:
            return CapacityCheck(
                "unknown", capacity_id, None,
                "Assigned capacity is not visible. List Capacities only lists capacities where the caller "
                "is administrator or contributor; workspace access alone does not imply capacity visibility.",
            )
        if token is not None and (not isinstance(token, str) or not token):
            return CapacityCheck("unknown", capacity_id, None, "Invalid capacity continuationToken.")
        if uri is not None:
            if not isinstance(uri, str):
                return CapacityCheck("unknown", capacity_id, None, "Invalid capacity continuationUri.")
            parsed, expected = urlsplit(uri), urlsplit(base)
            query = parse_qs(parsed.query, keep_blank_values=True)
            if (parsed.scheme != expected.scheme or parsed.netloc != expected.netloc
                    or parsed.path != expected.path or parsed.fragment
                    or set(query) != {"continuationToken"} or len(query["continuationToken"]) != 1
                    or not query["continuationToken"][0]):
                return CapacityCheck("unknown", capacity_id, None, "Unsafe capacity pagination URL; no request sent.")
            url = uri
        else:
            # Fabric can return an already percent-encoded continuation token.
            url = f"{base}?{urlencode({'continuationToken': token}, safe='%')}"
    return CapacityCheck("unknown", capacity_id, None, "Capacity pagination exceeded 100 pages; narrow verification with support.")


def require_execution_capacity(check: CapacityCheck, *, allow_unknown: bool = False) -> None:
    if check.classification == "trial":
        raise RuntimeError(
            f"Project Osmos execution blocked: capacity SKU {check.sku} is trial. "
            "Select an eligible supported capacity or contact the workspace/capacity administrator. "
            "No task mutations were sent; no workspace relocation, purchase, or policy change was made."
        )
    if check.classification == "unknown" and not allow_unknown:
        raise RuntimeError(
            f"Capacity eligibility is unknown: {check.reason} "
            "Verify the selected tenant/workspace and capacity SKU with someone who already has capacity "
            "visibility; administrator access is not required for every caller. Keep read-only inspection "
            "available. Only after explicit user acknowledgment, pass --allow-unknown-capacity for this execution."
        )
