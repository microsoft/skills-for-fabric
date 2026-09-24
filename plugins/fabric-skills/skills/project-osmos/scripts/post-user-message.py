#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
"""Post a user follow-up and safely continue the same Project Osmos task.

Usage (Bash; select PYTHON_RUNNER using references/python-helper-runtime.md):
    "${PYTHON_RUNNER[@]}" skills/project-osmos/scripts/post-user-message.py \\
        --base-url https://.../aichat --task-id <uuid> \\
        --token-file <path> --message "also dedupe by invoice_id" --output json

The token is read from --token-file, never argv/env. On non-Windows systems,
group/other permissions are rejected before reading; use chmod 600.
"""

from __future__ import annotations

import argparse
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from python_runtime import require_supported_python
from task_status import is_task_running, is_task_terminal, status_label


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
    if parsed.scheme.lower() != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("--base-url must be an absolute HTTPS URL without query or fragment")
    if parsed.path.rstrip("/").casefold().endswith("/aichat") is False:
        raise ValueError("--base-url path must end with /aichat")
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
    normalized_trusted_base = normalize_base_url(trusted_base)
    if base_url != normalized_trusted_base:
        raise ValueError("--base-url must match tasks_base in the trusted routing file")
    return base_url


def normalize_task_id(value: str) -> str:
    try:
        return str(uuid.UUID(value.strip()))
    except ValueError as exc:
        raise ValueError("--task-id must be a UUID") from exc


def http_request(
    url: str,
    auth_header: str,
    timeout: float,
    *,
    method: str = "GET",
    body: bytes | None = None,
    content_type: str | None = None,
) -> HttpResult:
    headers = {"Authorization": auth_header}
    if content_type:
        headers["Content-Type"] = content_type
    if method == "POST" and body is None:
        body = b""
        headers["Content-Length"] = "0"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return HttpResult(response.status, response.read(), url)
    except urllib.error.HTTPError as exc:
        return HttpResult(exc.code, exc.read() if exc.fp else b"", url)
    except (urllib.error.URLError, OSError) as exc:
        return HttpResult(0, f"{type(exc).__name__}: {exc}".encode(), url)


def failure_message(action: str, result: HttpResult) -> str:
    if result.status == 0:
        return f"{action} failed before receiving an HTTP response: {result.text[:500]}"
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
) -> ContinuationResult:
    """Post the message first, then start one run only when none is active."""
    task_id = normalize_task_id(task_id)
    task_url = f"{normalize_base_url(base_url)}/{task_id}"
    task_before = parse_task(http_request(task_url, auth_header, timeout))
    running_before = is_task_running(task_before)
    terminal_before = is_task_terminal(task_before)

    message_id, body = build_message_payload(message, author_name, source)
    message_result = http_request(
        f"{task_url}/messages",
        auth_header,
        timeout,
        method="POST",
        body=body,
        content_type="application/json",
    )
    if not message_result.ok:
        raise ContinuationError(failure_message("user message post", message_result))

    task_after = parse_task(
        http_request(task_url, auth_header, timeout),
        "post-message status recheck",
    )
    running_after = is_task_running(task_after)
    status_after = status_label(task_after.get("status"))
    run_start_attempted = False
    run_started = False
    run_active = running_after
    run_start_outcome = "not_needed"

    if not running_after:
        run_start_attempted = True
        run_result = http_request(f"{task_url}/run", auth_header, timeout, method="POST")
        if run_result.ok:
            run_started = True
            run_active = True
            run_start_outcome = "started"
        elif run_result.status == 409:
            conflict_task = parse_task(
                http_request(task_url, auth_header, timeout),
                "run-conflict status lookup",
            )
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
            raise ContinuationError(
                f"user message {message_id} was posted, but {failure_message('same-task run start', run_result)}"
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
        )
    except ContinuationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(asdict(result), sort_keys=True) if args.output == "json" else result.message_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
