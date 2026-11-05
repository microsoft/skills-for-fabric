#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
"""Post a user follow-up and safely continue the same Project Osmos task.

Usage (Bash; select PYTHON_RUNNER using references/python-helper-runtime.md):
    "${PYTHON_RUNNER[@]}" skills/project-osmos/scripts/post-user-message.py \\
        --base-url https://.../tasks --task-id <uuid> \\
        --token-file <path> --message "also dedupe by invoice_id" --output json

The token is read from --token-file, never argv/env. On non-Windows systems,
group/other permissions are rejected before reading; use chmod 600.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from python_runtime import require_supported_python
from task_status import is_task_running, is_task_terminal, status_label
from task_routes import validate_routing


require_supported_python()

AUTH_BODY_HINTS = ("unauthorized", "token", "invalid_token", "authentication", "auth", "expired")


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: bytes
    url: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def is_auth_failure(self) -> bool:
        return self.status in (401, 403) or (
            self.status == 400 and any(hint in self.text.casefold() for hint in AUTH_BODY_HINTS)
        )


class TaskRequest(Protocol):
    def __call__(
        self, url: str, auth_header: str, timeout: float, *,
        method: str = "GET", body: bytes | None = None, content_type: str | None = None,
    ) -> HttpResult: ...


@dataclass(frozen=True)
class ContinuationResult:
    task_id: str
    message_id: str
    status_before: str
    terminal_before: bool
    running_before: bool
    status_after_message: str
    running_after_message: bool
    message_posted: bool
    run_start_attempted: bool
    run_started: bool
    run_active: bool
    run_start_outcome: str


class ContinuationError(RuntimeError):
    """A continuation step failed and must be surfaced to the user."""


def normalize_base_url(value: str) -> str:
    trimmed = value.strip().rstrip("/")
    parsed = urllib.parse.urlsplit(trimmed)
    if (parsed.scheme.lower() != "https" or not parsed.netloc or parsed.query or parsed.fragment
            or parsed.username or parsed.password):
        raise ValueError("--base-url must be an absolute HTTPS URL without query or fragment")
    if not parsed.path.endswith(("/tasks", "/aichat")):
        raise ValueError("--base-url path must end with /tasks or saved /aichat")
    return trimmed


def validate_base_url_from_routing(base_url: str, token_file: Path) -> str:
    routing_file = token_file.parent / "routing.json"
    try:
        routing = json.loads(routing_file.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"unable to read trusted routing file {routing_file}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"trusted routing file {routing_file} is not valid JSON") from exc
    trusted_base = routing.get("tasks_base") if isinstance(routing, dict) else None
    if not isinstance(trusted_base, str):
        raise ValueError(f"trusted routing file {routing_file} does not contain tasks_base")
    validate_routing(routing)
    normalized_trusted_base = normalize_base_url(trusted_base)
    if base_url != normalized_trusted_base:
        raise ValueError("--base-url must match tasks_base in the trusted routing file")
    return base_url


def normalize_task_id(value: str) -> str:
    try:
        return str(uuid.UUID(value.strip()))
    except ValueError as exc:
        raise ValueError("--task-id must be a UUID") from exc


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_request(
    url: str,
    auth_header: str,
    timeout: float,
    *,
    method: str = "GET",
    body: bytes | None = None,
    content_type: str | None = None,
) -> HttpResult:
    headers = {"Authorization": auth_header, "x-ms-fabric-skill": "project-osmos"}
    if content_type:
        headers["Content-Type"] = content_type
    if method == "POST" and body is None:
        body = b""
        headers["Content-Length"] = "0"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        try:
            with urllib.request.build_opener(RejectRedirects()).open(request, timeout=timeout) as response:
                return HttpResult(response.status, response.read(), url)
        except urllib.error.HTTPError as exc:
            return HttpResult(exc.code, exc.read() if exc.fp else b"", url)
    except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
        return HttpResult(0, f"{type(exc).__name__}: {exc}".encode(), url)


def failure_message(action: str, result: HttpResult) -> str:
    if result.status == 0:
        return f"{action} failed without a complete HTTP response: {result.text[:500]}"
    category = "authentication failed" if result.is_auth_failure() else f"HTTP {result.status}"
    detail = result.text.strip()
    return f"{action} failed ({category})" + (f": {detail[:500]}" if detail else "")


def parse_task(result: HttpResult, action: str = "live task status lookup") -> dict[str, Any]:
    if not result.ok:
        raise ContinuationError(failure_message(action, result))
    try:
        payload = json.loads(result.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ContinuationError(f"{action} returned invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContinuationError(f"{action} returned a non-object payload")
    return payload


def build_message_payload(message: str, author_name: str, source: str) -> tuple[str, bytes]:
    message_id = str(uuid.uuid4())
    payload = {
        "messages": [{
            "id": message_id,
            "role": "User",
            "content": message,
            "timestamp": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "metadata": {
                "author_name": author_name,
                "author_source": source,
            },
        }],
    }
    return message_id, json.dumps(payload).encode("utf-8")


def continue_task(
    *,
    base_url: str,
    task_id: str,
    auth_header: str,
    message: str,
    author_name: str,
    source: str,
    timeout: float,
    preflight: Callable[[], None],
    request: TaskRequest | None = None,
) -> ContinuationResult:
    """Run the caller's preflight, post the message, and start at most one run.

    The caller owns trusted routing, authentication, execution policy and any
    custom transport. Transport failures retain phase-specific recovery context
    without retries or fallback. Omitted transports use the command-line HTTP helper.
    """
    task_id = normalize_task_id(task_id)
    task_url = f"{normalize_base_url(base_url)}/{task_id}"
    preflight()
    transport = http_request if request is None else request

    def request_task(
        url: str, *, method: str = "GET", body: bytes | None = None,
        content_type: str | None = None,
    ) -> HttpResult:
        try:
            return transport(
                url, auth_header, timeout, method=method, body=body, content_type=content_type,
            )
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            return HttpResult(0, f"{type(exc).__name__}: {exc}".encode(), url)

    task_before = parse_task(request_task(task_url))
    running_before = is_task_running(task_before)
    terminal_before = is_task_terminal(task_before)

    message_id, body = build_message_payload(message, author_name, source)
    try:
        message_result = request_task(
            f"{task_url}/messages",
            method="POST",
            body=body,
            content_type="application/json",
        )
    except ContinuationError as exc:
        raise ContinuationError(
            f"user message post outcome is unknown; message ID {message_id}; {exc}. "
            "Inspect messages before retrying; do not generate a new deduplication ID."
        ) from exc
    if not message_result.ok:
        outcome = "user message post outcome is unknown; " if message_result.status == 0 else ""
        raise ContinuationError(
            f"{outcome}{failure_message('user message post', message_result)}; message ID {message_id}. "
            "Inspect messages before retrying; do not generate a new deduplication ID."
        )

    try:
        task_after = parse_task(
            request_task(task_url),
            "post-message status recheck",
        )
    except ContinuationError as exc:
        raise ContinuationError(f"user message {message_id} was posted; {exc}; do not repost it") from exc
    running_after = is_task_running(task_after)
    status_after = status_label(task_after.get("status"))
    run_start_attempted = False
    run_started = False
    run_active = running_after
    run_start_outcome = "not_needed"

    if not running_after:
        run_start_attempted = True
        try:
            run_result = request_task(f"{task_url}/run", method="POST")
        except ContinuationError as exc:
            raise ContinuationError(
                f"user message {message_id} was posted; run start outcome is unknown; "
                f"{exc}; inspect status before retrying; do not repost it"
            ) from exc
        if run_result.ok:
            run_started = True
            run_active = True
            run_start_outcome = "started"
        elif run_result.status == 409:
            try:
                conflict_task = parse_task(
                    request_task(task_url),
                    "run-conflict status lookup",
                )
            except ContinuationError as exc:
                raise ContinuationError(
                    f"user message {message_id} was posted; {exc}; "
                    "inspect status before retrying; do not repost it"
                ) from exc
            if not is_task_running(conflict_task):
                raise ContinuationError(
                    f"user message {message_id} was posted, but same-task run start returned "
                    f"HTTP 409 and the live task is {status_label(conflict_task.get('status'))}; "
                    "no second run request was sent"
                )
            status_after = status_label(conflict_task.get("status"))
            running_after = True
            run_active = True
            run_start_outcome = "already_running"
        else:
            outcome = "run start outcome is unknown; " if run_result.status == 0 else ""
            raise ContinuationError(
                f"user message {message_id} was posted; {outcome}"
                f"{failure_message('same-task run start', run_result)}; "
                "inspect status before retrying; do not repost it"
            )

    return ContinuationResult(
        task_id=task_id,
        message_id=message_id,
        status_before=status_label(task_before.get("status")),
        terminal_before=terminal_before,
        running_before=running_before,
        status_after_message=status_after,
        running_after_message=running_after,
        message_posted=True,
        run_start_attempted=run_start_attempted,
        run_started=run_started,
        run_active=run_active,
        run_start_outcome=run_start_outcome,
    )


def detect_az_user() -> str | None:
    if shutil.which("az") is None:
        return None
    try:
        result = subprocess.run(
            ["az", "account", "show", "--query", "user.name", "-o", "tsv"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return (result.stdout or "").strip() or None
    except (subprocess.SubprocessError, OSError):
        return None


def read_private_token_file(path: Path) -> str:
    with path.open(encoding="utf-8") as token_file:
        if os.name != "nt" and stat.S_IMODE(os.fstat(token_file.fileno()).st_mode) & 0o077:
            raise PermissionError("--token-file must not be accessible by group or other users")
        return token_file.read().strip()


def execution_preflight(token_file: Path, *, allow_unknown: bool, timeout: float) -> None:
    """Validate saved context and recheck the same target before execution."""
    routing_file = token_file.parent / "routing.json"
    try:
        routing = json.loads(routing_file.read_text(encoding="utf-8"))
        if not isinstance(routing, dict):
            raise ValueError("Saved routing must be an object")
        validate_routing(routing)
    except (OSError, ValueError) as exc:
        raise ContinuationError(f"Cannot validate saved execution context: {exc}") from exc
    command = [
        sys.executable, str(Path(__file__).with_name("resolve-auth-and-routing.py")),
        "--workspace-id", routing["workspace_id"], "--lakehouse-id", routing["lakehouse_id"],
        "--existing-routing", str(routing_file),
        "--expected-capacity-id", routing["capacity_id"], "--check-capacity-only", "--timeout", str(timeout),
    ]
    if routing.get("resource_tenant_id"):
        command.extend(["--resource-tenant-id", routing["resource_tenant_id"]])
    if allow_unknown:
        command.append("--allow-unknown-capacity")
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout * 105)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ContinuationError(f"Capacity preflight failed before task mutation: {exc}") from exc
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode:
        raise ContinuationError("Capacity preflight did not authorize execution; no task mutations sent")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--token-file", required=True, type=Path)
    parser.add_argument("--message", required=True)
    parser.add_argument("--author-name")
    parser.add_argument("--source", default="copilot-cli")
    parser.add_argument("--auth-scheme", default="mwctoken")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--output", choices=("id", "json"), default="id")
    parser.add_argument("--allow-unknown-capacity", action="store_true",
                        help="Only after explicit user acknowledgment of unknown eligibility for this execution.")
    args = parser.parse_args()

    try:
        base_url = normalize_base_url(args.base_url)
        task_id = normalize_task_id(args.task_id)
        validate_base_url_from_routing(base_url, args.token_file)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        token = read_private_token_file(args.token_file)
    except OSError as exc:
        print(f"error: unable to read token file {args.token_file}: {exc}", file=sys.stderr)
        return 2
    if not token:
        print("error: token file is empty", file=sys.stderr)
        return 2

    try:
        result = continue_task(
            base_url=base_url,
            task_id=task_id,
            auth_header=f"{args.auth_scheme} {token}",
            message=args.message,
            author_name=args.author_name or detect_az_user() or "unknown",
            source=args.source,
            timeout=args.timeout,
            preflight=lambda: execution_preflight(
                args.token_file, allow_unknown=args.allow_unknown_capacity, timeout=args.timeout,
            ),
        )
    except ContinuationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(asdict(result), sort_keys=True) if args.output == "json" else result.message_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
