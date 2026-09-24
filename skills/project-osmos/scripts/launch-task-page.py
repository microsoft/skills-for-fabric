#!/usr/bin/env python3
"""Build and optionally open the Fabric task details URL for any task."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from collections.abc import Callable
from urllib.parse import unquote, urlsplit, urlunsplit

from python_runtime import require_supported_python

require_supported_python()


OWNED_QUERY_KEYS = {"projectosmosux", "selectedpath"}
PRODUCTION_PORTAL = "https://app.fabric.microsoft.com"
PRODUCTION_HOSTS = {"app.fabric.microsoft.com", "app.powerbi.com"}
BROWSER_TIMEOUT_SECONDS = 3.0


def normalize_environment(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("environment must not be empty")
    return "prod" if normalized == "production" else normalized


def open_browser(url: str) -> bool:
    """Isolate browser controllers and their descendants from the JSON channel."""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, webbrowser; sys.exit(0 if webbrowser.open(sys.argv[1]) else 1)",
            url,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={
            key: value
            for key, value in os.environ.items()
            if key.upper() not in {"MWC_TOKEN", "PBI_TOKEN", "BEARER"}
        },
        timeout=BROWSER_TIMEOUT_SECONDS,
        check=False,
    )
    return completed.returncode == 0


def guid(value: str) -> str:
    """Return a canonical GUID or raise an argparse-compatible error."""
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid GUID: {value}") from exc


def portal_parts(
    environment: str,
    source_url: str | None,
    portal_base_url: str | None,
) -> tuple[str, str, str]:
    """Resolve the portal scheme, host, and query without guessing private hosts."""
    environment = normalize_environment(environment)
    candidate = source_url or portal_base_url
    if candidate is None:
        if environment != "prod":
            raise ValueError(
                "a source URL or portal base URL is required outside production"
            )
        candidate = PRODUCTION_PORTAL

    candidate = candidate.strip()
    normalized = (
        candidate
        if re.match(r"^[a-z][a-z0-9+.-]*://", candidate, re.I)
        else f"https://{candidate}"
    )
    parts = urlsplit(normalized)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("portal URL must include a valid HTTP(S) host")
    if (
        not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or any(character.isspace() or character == "\\" for character in candidate)
    ):
        raise ValueError("portal URL must not contain credentials or invalid host characters")
    port = parts.port
    if environment == "prod" and (
        parts.scheme != "https"
        or parts.hostname.lower() not in PRODUCTION_HOSTS
        or port not in {None, 443}
    ):
        raise ValueError("production requires a supported HTTPS Fabric portal host")
    return parts.scheme, parts.netloc, parts.query


def build_task_page_url(
    *,
    environment: str,
    workspace_id: str,
    lakehouse_id: str,
    task_id: str,
    source_url: str | None = None,
    portal_base_url: str | None = None,
) -> str:
    """Build the canonical task page while preserving non-owned query tokens."""
    scheme, netloc, query = portal_parts(
        environment,
        source_url,
        portal_base_url,
    )
    kept = [
        pair
        for pair in query.split("&")
        if pair
        and unquote(pair.split("=", 1)[0]).lower() not in OWNED_QUERY_KEYS
    ]
    if not kept:
        kept.append("experience=power-bi")
    kept.extend(
        (
            "projectOsmosUX=1",
            f"selectedPath=ProjectOsmos%2F{task_id}",
        )
    )
    path = f"/groups/{workspace_id}/lakehouses/{lakehouse_id}"
    return urlunsplit((scheme, netloc, path, "&".join(kept), ""))


def launch_task_page(
    args: argparse.Namespace,
    opener: Callable[[str], bool] = open_browser,
) -> dict[str, object]:
    """Return launch, fallback, and telemetry data without failing task creation."""
    telemetry: dict[str, object] = {
        "event_name": "project_osmos_cli_task_details_launch",
        "cli_originated": True,
        "task_created": True,
        "launch_result": "not_attempted",
        "fallback_used": False,
        "workspace_id": args.workspace_id,
        "task_id": args.task_id,
        "environment": normalize_environment(args.environment),
    }
    result: dict[str, object] = {
        "task_page_url": None,
        "warning": None,
        "telemetry": telemetry,
    }
    task_page_url = build_task_page_url(
        environment=args.environment,
        workspace_id=args.workspace_id,
        lakehouse_id=args.lakehouse_id,
        task_id=args.task_id,
        source_url=args.source_url,
        portal_base_url=args.portal_base_url,
    )
    result["task_page_url"] = task_page_url

    if args.no_open:
        return result

    timed_out = False
    try:
        opened = opener(task_page_url)
    except subprocess.TimeoutExpired:
        opened = False
        timed_out = True
    except Exception:  # noqa: BLE001 - platform browser controllers must not stop recovery.
        opened = False
    if opened:
        telemetry["launch_result"] = "opened"
    else:
        telemetry["launch_result"] = "timed_out" if timed_out else "failed"
        telemetry["fallback_used"] = True
        result["warning"] = (
            "Automatic browser launch failed; the remote task is still running. "
            "Open the Fabric task details URL shown above."
        )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", required=True, type=guid)
    parser.add_argument("--lakehouse-id", required=True, type=guid)
    parser.add_argument("--task-id", required=True, type=guid)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--source-url")
    parser.add_argument("--portal-base-url")
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Print the canonical URL without attempting a browser launch.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = launch_task_page(args)
    except ValueError as exc:
        print(f"launch-task-page: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
