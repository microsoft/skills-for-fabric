# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
"""Build canonical task routes and validate saved preflight context."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID
from python_runtime import require_supported_python


require_supported_python()


PUBLIC_API = "https://api.fabric.microsoft.com"
PUBLIC_PORTAL = "https://app.fabric.microsoft.com"
LABEL = r"[a-z][a-z0-9-]{0,61}[a-z0-9]|[a-z]"
UUID_PATH = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def https_origin(value: str) -> str:
    """Normalize a bare HTTPS origin before credentials can be sent."""
    if not isinstance(value, str):
        raise ValueError("Expected a bare HTTPS origin")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.port not in (None, 443)
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or any(character.isspace() or character == "\\" for character in value)):
        raise ValueError("Expected a bare HTTPS origin without credentials")
    return f"https://{parsed.hostname}"


def portal_target(url: str) -> dict[str, str]:
    """Select a Fabric target from its portal, without an environment registry."""
    if not isinstance(url, str):
        raise ValueError("Expected a Fabric portal URL")
    parsed = urlsplit(url)
    origin = https_origin(f"{parsed.scheme}://{parsed.netloc}")
    if any(character.isspace() or character == "\\" for character in url):
        raise ValueError("Portal URL contains invalid characters")
    match = re.fullmatch(rf"(?P<label>{LABEL})\.(?:fabric\.microsoft\.com|powerbi\.com)",
                         urlsplit(origin).hostname or "")
    if not match:
        raise ValueError("Expected a Fabric or Power BI HTTPS portal host")
    label = match["label"]
    environment = "production" if label == "app" else label
    if label in ("prod", "production", "api"):
        raise ValueError("Expected a portal URL, not an API or environment alias")
    return {
        "environment": environment,
        "portal_base_url": origin,
        "fabric_api_host": PUBLIC_API if label == "app" else f"https://{label}api.fabric.microsoft.com",
    }


def parse_lakehouse_url(url: str) -> dict[str, str | None]:
    url = url.strip()
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        url = f"https://{url}"
    target = portal_target(url)
    path = urlsplit(url).path
    workspace = re.match(rf"^/groups/(?P<ws>{UUID_PATH})(?:/|$)", path, re.I)
    lakehouse = re.match(
        rf"^/groups/{UUID_PATH}/lakehouses/(?P<lh>{UUID_PATH})(?:/|$)", path, re.I,
    )
    if not workspace:
        raise ValueError("Portal URL must identify a workspace")
    prefix = f"/groups/{workspace['ws']}/lakehouses/".lower()
    if path.lower().startswith(prefix) and not lakehouse:
        raise ValueError("Portal URL has an invalid Lakehouse ID")
    return {
        **target,
        "workspace_id": str(UUID(workspace["ws"])),
        "lakehouse_id": str(UUID(lakehouse["lh"])) if lakehouse else None,
    }


def validate_backend_origin(host: str) -> str:
    origin = https_origin(host)
    hostname = urlsplit(origin).hostname or ""
    if (not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+",
                         hostname)
            or not hostname.endswith((".pbidedicated.windows.net", ".analysis.windows.net"))):
        raise ValueError("Workload host must be a documented Fabric backend")
    return origin


def onelake_origin(value: str) -> str:
    origin = https_origin(value)
    if not re.fullmatch(r"[a-z0-9-]+\.dfs\.fabric\.microsoft\.com", urlsplit(origin).hostname or ""):
        raise ValueError("Expected a Fabric OneLake DFS origin")
    return origin


def task_base(host: str, capacity_id: str, workspace_id: str, lakehouse_id: str) -> str:
    return (
        f"{host}/webapi/capacities/{capacity_id}/workloads/SparkCore/"
        f"SparkCoreService/direct/v1/workspaces/{workspace_id}/artifacts/{lakehouse_id}/tasks"
    )


def validate_routing(routing: dict[str, Any]) -> str:
    """Validate saved identity/origins; service endpoints enforce authorization."""
    if not isinstance(routing, dict):
        raise ValueError("Saved routing must be a JSON object")
    environment = routing.get("environment")
    portal = routing.get("portal_base_url")
    target = portal_target(portal or PUBLIC_PORTAL)
    if (environment not in (None, "prod", "production") or target["environment"] != "production"):
        if not portal or environment != target["environment"]:
            raise ValueError("Saved API and portal must match the selected target")
    if routing.get("fabric_api_host") != target["fabric_api_host"]:
        raise ValueError("Saved API and portal must match the selected target")
    for key in ("capacity_id", "workspace_id", "lakehouse_id"):
        value = routing.get(key)
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError(f"Saved routing {key} must be a normalized UUID")
    host = routing.get("sparkcore_host", "")
    if not isinstance(host, str):
        raise ValueError("Saved routing has no sparkcore_host")
    if validate_backend_origin(host) != host:
        raise ValueError("Saved SparkCore host must be a normalized HTTPS origin")
    expected = task_base(host, routing["capacity_id"], routing["workspace_id"], routing["lakehouse_id"])
    if routing.get("tasks_base") not in (expected, expected.removesuffix("/tasks") + "/aichat"):
        raise ValueError("Saved tasks_base does not match its resource context")
    return "public" if target["fabric_api_host"] == PUBLIC_API else "internal"
