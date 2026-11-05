# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
"""Resolve Project Osmos auth, token, and task routing.

This helper performs the same sequence documented in the Project Osmos skill:

1. Acquire a Power BI bearer token with Azure CLI, optionally scoped to an
   explicit resource tenant.
2. Read workspace and lakehouse metadata from the selected Fabric API host.
3. Capture the routed Fabric home cluster from response headers.
4. Exchange the bearer token for an MWC token.
5. If the global token exchange returns "Tenant not authorized for cluster",
   retry token exchange on the routed home cluster observed in step 3.
6. Write a local token file plus non-secret Bash and PowerShell exports for
   task lifecycle and follow-up helpers.

Usage (Bash; select PYTHON_RUNNER using references/python-helper-runtime.md):
    "${PYTHON_RUNNER[@]}" scripts/resolve-auth-and-routing.py \\
      --workspace-id <workspace-guid> \\
      --lakehouse-id <lakehouse-guid> \\
      --output-dir .dataprojects/auth

Add --resource-tenant-id <tenant-guid> only for an explicit tenant override.

Then source the generated env file:
    source .dataprojects/auth/env.sh

For PowerShell:
    . .dataprojects/auth/env.ps1
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from python_runtime import require_supported_python
from capacity_preflight import CapacityCheck, inspect_capacity, require_execution_capacity
from task_routes import (
    PUBLIC_PORTAL, onelake_origin, parse_lakehouse_url, portal_target, task_base,
    validate_backend_origin, validate_routing,
)


require_supported_python()

PBI_RESOURCE = "https://analysis.windows.net/powerbi/api"
DEFAULT_FABRIC_API_HOST = "https://api.fabric.microsoft.com"
DEFAULT_WORKLOAD_TYPE = "SparkCore"
CLUSTER_AUTH_ERROR = "Tenant not authorized for cluster"
FABRIC_SKILL_HEADER = "x-ms-fabric-skill"
FABRIC_SKILL_NAME = "project-osmos"


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: bytes
    headers: dict[str, str]
    url: str


@dataclass(frozen=True)
class WorkspaceContext:
    workspace: dict[str, Any]
    lakehouse: dict[str, Any]
    capacity_id: str
    home_cluster_uri: str | None
    workspace_result: HttpResult
    lakehouse_result: HttpResult


@dataclass(frozen=True)
class TokenExchange:
    token_data: dict[str, Any]
    token_result: HttpResult
    token_base_used: str
    global_token_base: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--resource-tenant-id",
        help="Optional tenant ID that owns the target Fabric workspace. Omit it to use the current Azure CLI session.",
    )
    parser.add_argument(
        "--tenant-id",
        dest="legacy_tenant_id",
        help="Deprecated alias for --resource-tenant-id.",
    )
    parser.add_argument(
        "--normalize-resource-tenant-env",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--workspace-id", help="Fabric workspace object ID.")
    parser.add_argument("--lakehouse-id", help="Default Spark-session lakehouse object ID.")
    parser.add_argument("--output-dir", type=Path, help="Directory for token/env/routing outputs.")
    parser.add_argument("--portal-url", help="Selected Lakehouse browser URL; retains its target.")
    parser.add_argument("--existing-routing", type=Path, help="Original routing.json for same-task refresh or preflight.")
    parser.add_argument("--expected-capacity-id", help="Stop if workspace metadata differs from this saved capacity.")
    parser.add_argument("--check-capacity-only", action="store_true", help="Read-only execution preflight; no token/output writes.")
    parser.add_argument("--purpose", choices=("execute", "inspect"), default="execute")
    parser.add_argument("--allow-unknown-capacity", action="store_true",
                        help="Use only after explicit user acknowledgment of unknown eligibility for this execution.")
    parser.add_argument("--fabric-api-host", help="Optional API origin; must match the selected portal or saved context.")
    parser.add_argument("--workload-type", default=DEFAULT_WORKLOAD_TYPE, help="MWC workload type.")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--token-resource",
        default=PBI_RESOURCE,
        help="Azure CLI resource for the bearer token. Defaults to the Power BI API resource.",
    )
    args = parser.parse_args(argv)
    if not args.normalize_resource_tenant_env:
        missing = [
            option
            for option, value in (
                ("--workspace-id", args.workspace_id),
                ("--lakehouse-id", args.lakehouse_id),
                ("--output-dir", args.output_dir),
            )
            if value is None and not (option == "--output-dir" and args.check_capacity_only)
        ]
        if missing:
            parser.error(f"the following arguments are required: {', '.join(missing)}")
    return args


def select_resource_tenant_id(
    resource_tenant_id: str | None,
    legacy_tenant_id: str | None,
    *,
    resource_label: str = "--resource-tenant-id",
    legacy_label: str = "--tenant-id",
) -> str | None:
    def normalize(value: str | None, label: str) -> str | None:
        if value is None or not value.strip():
            return None
        try:
            return str(UUID(value.strip()))
        except ValueError as exc:
            raise ValueError(f"{label} must be a valid GUID") from exc

    selected = normalize(resource_tenant_id, resource_label)
    legacy = normalize(legacy_tenant_id, legacy_label)
    if selected and legacy and selected != legacy:
        raise ValueError(f"{resource_label} and {legacy_label} disagree; select the tenant that owns the workspace")
    return selected or legacy


def normalize_base_url(value: str) -> str:
    trimmed = value.strip().rstrip("/")
    if not trimmed:
        raise ValueError("base URL cannot be empty")
    if "://" not in trimmed:
        trimmed = f"https://{trimmed}"
    parsed = urllib.parse.urlsplit(trimmed)
    if parsed.scheme.lower() != "https":
        raise ValueError("base URL must use HTTPS")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("base URL must be an absolute HTTPS URL without credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("base URL must not contain a query or fragment")
    return trimmed


def normalize_fabric_api_host(value: str, expected: str = DEFAULT_FABRIC_API_HOST) -> str:
    normalized = normalize_base_url(value)
    parsed = urllib.parse.urlsplit(normalized)
    expected_parts = urllib.parse.urlsplit(expected)
    if parsed.hostname != expected_parts.hostname or parsed.port not in (None, 443) or parsed.path not in ("", "/"):
        raise ValueError(f"--fabric-api-host must be {expected}")
    return expected


def normalize_uuid(value: str, label: str) -> str:
    try:
        if not isinstance(value, str):
            raise ValueError("UUID must be a string")
        return str(UUID(value.strip()))
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid UUID") from exc


def get_bearer_token(resource_tenant_id: str | None, resource: str) -> str:
    command = [
        shutil.which("az") or "az",
        "account",
        "get-access-token",
    ]
    if resource_tenant_id:
        command.extend(["--tenant", resource_tenant_id])
    command.extend(["--resource", resource, "--query", "accessToken", "-o", "tsv"])
    try:
        token = subprocess.check_output(command, text=True).strip()
    except (subprocess.CalledProcessError, OSError) as exc:
        if resource_tenant_id:
            message = (
                "failed to acquire an Azure CLI token for the selected resource tenant. "
                "Run az login --tenant <resource-tenant-id> --allow-no-subscriptions before retrying"
            )
        else:
            message = (
                "failed to acquire an Azure CLI token from the current session. Run az login before retrying, "
                "or provide --resource-tenant-id when the workspace belongs to another tenant"
            )
        raise RuntimeError(message) from exc
    if not token:
        raise RuntimeError("Azure CLI returned an empty bearer token")
    return token


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(
    url: str,
    bearer_token: str,
    *,
    timeout: float,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    allow_http_error: bool = False,
) -> HttpResult:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Accept": "application/json",
        FABRIC_SKILL_HEADER: FABRIC_SKILL_NAME,
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.build_opener(RejectRedirects()).open(request, timeout=timeout) as response:
            body = response.read()
            response_headers = {key.lower(): value for key, value in response.headers.items()}
            return HttpResult(status=response.status, body=body, headers=response_headers, url=url)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        if allow_http_error:
            response_headers = {key.lower(): value for key, value in exc.headers.items()}
            return HttpResult(status=exc.code, body=body, headers=response_headers, url=url)
        message = body.decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc}") from exc


def decode_json(result: HttpResult) -> dict[str, Any]:
    try:
        data = json.loads(result.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"{result.url} returned non-JSON response: {result.body[:500]!r}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{result.url} returned JSON {type(data).__name__}, expected object")
    return data


def response_header(result: HttpResult, name: str) -> str | None:
    value = result.headers.get(name.lower())
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def token_error_message(result: HttpResult) -> str:
    try:
        data = decode_json(result)
    except RuntimeError:
        return result.body.decode("utf-8", "replace")
    error = data.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
    message = data.get("message")
    if isinstance(message, str):
        return message
    return json.dumps(data)


def shell_export(name: str, value: str) -> str:
    return f"export {name}={shlex.quote(value)}"


def powershell_export(name: str, value: str) -> str:
    escaped = value.replace("'", "''")
    return f"$env:{name} = '{escaped}'"


def write_private_text(path: Path, text: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)
    try:
        if os.name != "nt":
            os.fchmod(descriptor, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(descriptor, "w", encoding="utf-8") as private_file:
            descriptor = -1
            private_file.write(text)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def resolve_workspace_context(args: argparse.Namespace, fabric_api_host: str, bearer: str) -> WorkspaceContext:
    workspace_url = f"{fabric_api_host}/v1/workspaces/{args.workspace_id}"
    workspace_result = request_json(workspace_url, bearer, timeout=args.timeout)
    workspace = decode_json(workspace_result)
    if workspace.get("id") is not None and normalize_uuid(workspace["id"], "workspace id") != args.workspace_id:
        raise ValueError("Workspace response ID differs from the selected workspace")
    capacity_id = workspace.get("capacityId")
    if not isinstance(capacity_id, str) or not capacity_id:
        raise RuntimeError(f"workspace response did not include capacityId: {workspace_url}")
    capacity_id = normalize_uuid(capacity_id, "workspace capacityId")

    lakehouse_url = f"{fabric_api_host}/v1/workspaces/{args.workspace_id}/lakehouses/{args.lakehouse_id}"
    lakehouse_result = request_json(lakehouse_url, bearer, timeout=args.timeout)
    lakehouse = decode_json(lakehouse_result)
    if lakehouse.get("id") is not None and normalize_uuid(lakehouse["id"], "Lakehouse id") != args.lakehouse_id:
        raise ValueError("Lakehouse response ID differs from the selected Lakehouse")

    home_cluster_uri = response_header(workspace_result, "home-cluster-uri") or response_header(
        lakehouse_result,
        "home-cluster-uri",
    )
    return WorkspaceContext(
        workspace=workspace,
        lakehouse=lakehouse,
        capacity_id=capacity_id,
        home_cluster_uri=home_cluster_uri,
        workspace_result=workspace_result,
        lakehouse_result=lakehouse_result,
    )


def exchange_mwc_token(
    args: argparse.Namespace,
    bearer: str,
    fabric_api_host: str,
    context: WorkspaceContext,
) -> TokenExchange:
    token_bases = [fabric_api_host]
    if context.home_cluster_uri:
        routed_base = validate_backend_origin(normalize_base_url(context.home_cluster_uri))
        if routed_base not in token_bases:
            token_bases.append(routed_base)

    token_payload = {
        "capacityObjectId": context.capacity_id,
        "workloadType": args.workload_type,
        "workspaceObjectId": args.workspace_id,
        "artifactObjectIds": [args.lakehouse_id],
    }

    token_result: HttpResult | None = None
    token_base_used: str | None = None
    first_error: str | None = None
    for index, token_base in enumerate(token_bases):
        token_url = f"{token_base}/metadata/v201606/generatemwctoken"
        result = request_json(
            token_url,
            bearer,
            timeout=args.timeout,
            method="POST",
            payload=token_payload,
            allow_http_error=True,
        )
        if 200 <= result.status < 300:
            token_result = result
            token_base_used = token_base
            break

        error_message = token_error_message(result)
        if index == 0:
            first_error = f"HTTP {result.status}: {error_message}"
        if CLUSTER_AUTH_ERROR not in error_message or index + 1 >= len(token_bases):
            raise RuntimeError(f"generatemwctoken failed at {token_url}: HTTP {result.status}: {error_message}")

    if token_result is None or token_base_used is None:
        raise RuntimeError(first_error or "generatemwctoken did not return a token response")

    return TokenExchange(
        token_data=decode_json(token_result),
        token_result=token_result,
        token_base_used=token_base_used,
        global_token_base=fabric_api_host,
    )


def build_routing_payload(
    args: argparse.Namespace,
    fabric_api_host: str,
    context: WorkspaceContext,
    token_exchange: TokenExchange,
    token_file: Path,
    resource_tenant_id: str | None,
) -> tuple[dict[str, str], dict[str, Any], str]:
    token_data = token_exchange.token_data
    mwc_token = token_data.get("Token") or token_data.get("token") or token_data.get("mwcToken")
    if not isinstance(mwc_token, str) or not mwc_token:
        raise RuntimeError("generatemwctoken response did not include Token")
    target_uri_host = token_data.get("TargetUriHost") or token_data.get("mwcTokenTargetUriHost")
    if not isinstance(target_uri_host, str) or not target_uri_host:
        raise RuntimeError("generatemwctoken response did not include TargetUriHost")
    sparkcore_host = validate_backend_origin(normalize_base_url(target_uri_host))
    tasks_base = task_base(sparkcore_host, context.capacity_id, args.workspace_id, args.lakehouse_id)
    generatemwc_url = f"{token_exchange.token_base_used}/metadata/v201606/generatemwctoken"
    exports = {
        "RESOURCE_TENANT_ID": resource_tenant_id or "",
        "TENANT_ID": resource_tenant_id or "",
        "FABRIC_API_HOST": fabric_api_host,
        "GENERATEMWC_URL": generatemwc_url,
        "CAPACITY_ID": context.capacity_id,
        "WORKSPACE_ID": args.workspace_id,
        "LAKEHOUSE_ID": args.lakehouse_id,
        "TOKEN_FILE": str(token_file),
        "TASKS_BASE": tasks_base,
    }
    target = getattr(args, "target_context", portal_target(PUBLIC_PORTAL))
    exports["FABRIC_PORTAL_URL"] = target["portal_base_url"]
    exports["ENVIRONMENT"] = target["environment"]
    routing = {
        **target,
        "resource_tenant_id": resource_tenant_id,
        "fabric_api_host": fabric_api_host,
        "generatemwc_url": generatemwc_url,
        "home_cluster_uri": context.home_cluster_uri,
        "capacity_id": context.capacity_id,
        "workspace_id": args.workspace_id,
        "workspace_name": context.workspace.get("displayName"),
        "lakehouse_id": args.lakehouse_id,
        "lakehouse_name": context.lakehouse.get("displayName"),
        "sparkcore_host": sparkcore_host,
        "tasks_base": tasks_base,
        "token_file": str(token_file),
        "token_exchange_retried_on_home_cluster": token_exchange.token_base_used != token_exchange.global_token_base,
        "request_ids": {
            "workspace": response_header(context.workspace_result, "requestid"),
            "lakehouse": response_header(context.lakehouse_result, "requestid"),
            "generatemwctoken": response_header(token_exchange.token_result, "requestid"),
        },
    }
    properties = context.lakehouse.get("properties", {})
    files_path = properties.get("oneLakeFilesPath") if isinstance(properties, dict) else None
    if isinstance(files_path, str) and files_path:
        parts = urllib.parse.urlsplit(files_path)
        if parts.scheme not in ("abfss", "https") or not parts.hostname:
            raise ValueError("Lakehouse returned an invalid OneLake files path")
        routing["onelake_host"] = onelake_origin(f"https://{parts.hostname}")
    return exports, routing, mwc_token


def capacity_get(url: str, bearer: str, timeout: float) -> dict[str, Any]:
    try:
        result = request_json(url, bearer, timeout=timeout, allow_http_error=True)
    except TimeoutError as exc:
        raise RuntimeError("Capacity metadata request timed out; retry the metadata lookup before execution.") from exc
    if result.status != 200:
        action = {
            401: "Refresh sign-in in the selected resource tenant.",
            403: "Verify read permissions or ask someone with capacity visibility to verify the SKU.",
            404: "Verify the selected workspace and metadata endpoint; do not switch environments.",
            429: f"Throttled; wait Retry-After {response_header(result, 'retry-after') or 'unspecified'} before retrying.",
        }.get(result.status, "Retry metadata lookup only after resolving the service/network failure.")
        raise RuntimeError(f"Capacity metadata HTTP {result.status}. {action}")
    return decode_json(result)


def write_outputs(output_dir: Path, exports: dict[str, str], routing: dict[str, Any], mwc_token: str) -> None:
    token_file = output_dir / "mwc-token"
    env_file = output_dir / "env.sh"
    ps_env_file = output_dir / "env.ps1"
    routing_file = output_dir / "routing.json"
    write_private_text(token_file, mwc_token)
    env_file.write_text("\n".join(shell_export(key, value) for key, value in exports.items()) + "\n", encoding="utf-8")
    ps_env_file.write_text(
        "\n".join(powershell_export(key, value) for key, value in exports.items()) + "\n",
        encoding="utf-8",
    )
    routing_file.write_text(json.dumps(routing, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.normalize_resource_tenant_env:
        resource_tenant_id = select_resource_tenant_id(
            os.environ.get("RESOURCE_TENANT_ID"),
            os.environ.get("TENANT_ID"),
            resource_label="RESOURCE_TENANT_ID",
            legacy_label="TENANT_ID",
        )
        if resource_tenant_id:
            print(resource_tenant_id)
        return 0

    resource_tenant_id = select_resource_tenant_id(args.resource_tenant_id, args.legacy_tenant_id)
    args.workspace_id = normalize_uuid(args.workspace_id, "--workspace-id")
    args.lakehouse_id = normalize_uuid(args.lakehouse_id, "--lakehouse-id")
    expected_capacity = (
        normalize_uuid(args.expected_capacity_id, "--expected-capacity-id")
        if args.expected_capacity_id else None
    )
    if args.check_capacity_only and args.purpose != "execute":
        raise ValueError("--check-capacity-only is an execution preflight, not an inspection bypass")
    output_dir = args.output_dir
    saved = None
    saved_path = args.existing_routing
    if saved_path is None and output_dir and (output_dir / "routing.json").exists():
        saved_path = output_dir / "routing.json"
    if saved_path:
        destination_route = output_dir / "routing.json" if output_dir else None
        if (destination_route and destination_route.exists()
                and destination_route.resolve() != saved_path.resolve()
                and destination_route.read_bytes() != saved_path.read_bytes()):
            raise ValueError("Output directory contains different saved routing; no credentials requested")
        saved = json.loads(saved_path.read_text(encoding="utf-8"))
        if not isinstance(saved, dict):
            raise ValueError("Saved routing must be a JSON object")
        validate_routing(saved)
        if saved["workspace_id"] != args.workspace_id or saved["lakehouse_id"] != args.lakehouse_id:
            raise ValueError("Saved workspace or Lakehouse differs; do not overwrite another task's context")
        if expected_capacity and expected_capacity != saved["capacity_id"]:
            raise ValueError("Expected capacity differs from saved routing; verify the assignment")
        expected_capacity = saved["capacity_id"]
        saved_tenant = saved.get("resource_tenant_id")
        if saved_tenant:
            saved_tenant = normalize_uuid(saved_tenant, "saved resource_tenant_id")
            if resource_tenant_id and resource_tenant_id != saved_tenant:
                raise ValueError("Resource tenant differs from saved routing; do not switch tenants")
            resource_tenant_id = saved_tenant
    target = portal_target(saved.get("portal_base_url") or PUBLIC_PORTAL) if saved else portal_target(PUBLIC_PORTAL)
    if args.portal_url:
        selected = parse_lakehouse_url(args.portal_url)
        if selected["workspace_id"] != args.workspace_id or selected["lakehouse_id"] != args.lakehouse_id:
            raise ValueError("Portal URL must identify the selected workspace and Lakehouse")
        selected_target = {key: selected[key] for key in target}
        if saved and selected_target != target:
            raise ValueError("Portal target differs from saved routing; do not switch targets")
        target = selected_target
    if args.fabric_api_host:
        normalize_fabric_api_host(args.fabric_api_host, target["fabric_api_host"])
    args.target_context = target
    fabric_api_host = target["fabric_api_host"]
    bearer = get_bearer_token(resource_tenant_id, args.token_resource)
    if args.purpose == "execute":
        try:
            workspace = capacity_get(f"{fabric_api_host}/v1/workspaces/{args.workspace_id}", bearer, args.timeout)
        except RuntimeError as exc:
            raise RuntimeError(
                f"Cannot verify current workspace capacity assignment; resolve the error and retry: {exc}"
            ) from exc
        else:
            if workspace.get("id") is not None and normalize_uuid(workspace["id"], "workspace id") != args.workspace_id:
                raise ValueError("Workspace response ID differs from the selected workspace")
            if not workspace.get("capacityId"):
                raise ValueError(
                    "Workspace has no current capacity assignment; stop execution and verify the assignment"
                )
            current_capacity = normalize_uuid(workspace["capacityId"], "workspace capacityId")
            if expected_capacity and current_capacity != expected_capacity:
                raise ValueError("Workspace capacity changed; stop execution and verify the assignment")
            if fabric_api_host == DEFAULT_FABRIC_API_HOST:
                check = inspect_capacity(workspace, fabric_api_host, lambda url: capacity_get(url, bearer, args.timeout))
            else:
                check = CapacityCheck("service-managed", current_capacity, None,
                                      "Selected target's service enforces execution eligibility.")
        if fabric_api_host != DEFAULT_FABRIC_API_HOST and check.classification == "unknown":
            raise RuntimeError(check.reason)
        print(json.dumps({"capacity_preflight": check.to_dict(),
                          "unknown_acknowledged": args.allow_unknown_capacity and check.classification == "unknown"}),
              file=sys.stderr)
        if fabric_api_host == DEFAULT_FABRIC_API_HOST:
            require_execution_capacity(check, allow_unknown=args.allow_unknown_capacity)
        if args.check_capacity_only:
            return 0
    context = resolve_workspace_context(args, fabric_api_host, bearer)
    if expected_capacity and context.capacity_id != expected_capacity:
        raise ValueError("Workspace capacity changed; stop refresh and verify the assignment")
    if args.purpose == "execute" and check.capacity_id and context.capacity_id != check.capacity_id:
        raise ValueError("Workspace capacity changed during preflight; stop and verify the assignment")
    token_exchange = exchange_mwc_token(args, bearer, fabric_api_host, context)
    token_file = output_dir / "mwc-token"
    exports, routing, mwc_token = build_routing_payload(
        args,
        fabric_api_host,
        context,
        token_exchange,
        token_file,
        resource_tenant_id,
    )
    validate_routing(routing)
    if saved:
        for key in ("fabric_api_host", "workspace_id", "lakehouse_id", "capacity_id", "sparkcore_host"):
            if saved[key] != routing[key]:
                raise ValueError(f"Refreshed {key} differs from saved routing; no outputs written")
        routing["tasks_base"] = saved["tasks_base"]
        exports["TASKS_BASE"] = saved["tasks_base"]
    output_dir.mkdir(parents=True, exist_ok=True)
    write_outputs(output_dir, exports, routing, mwc_token)

    env_file = output_dir / "env.sh"
    ps_env_file = output_dir / "env.ps1"
    print(json.dumps(routing, indent=2))
    print("", file=sys.stderr)
    print(f"Wrote token file: {token_file}", file=sys.stderr)
    print(f"Wrote env exports: {env_file}", file=sys.stderr)
    print(f"Wrote PowerShell env exports: {ps_env_file}", file=sys.stderr)
    print(f"Run: source {shlex.quote(str(env_file))}", file=sys.stderr)
    print(f"PowerShell: . '{ps_env_file}'", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - command-line helper must surface exact failure.
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
