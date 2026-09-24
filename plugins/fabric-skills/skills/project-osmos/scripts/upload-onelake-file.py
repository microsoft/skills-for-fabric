#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
"""Upload one local file to the Files area of a Microsoft Fabric Lakehouse."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path, PurePosixPath

from python_runtime import require_supported_python


require_supported_python()

ONELAKE_HOST = "https://onelake.dfs.fabric.microsoft.com"
API_VERSION = "2021-08-06"
DEFAULT_TIMEOUT_SECONDS = 60.0


def validated_uuid(value: str, name: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise ValueError(f"{name} must be a UUID") from exc


def validated_destination(value: str) -> PurePosixPath:
    destination = PurePosixPath(value)
    if destination.is_absolute() or not destination.parts or destination.parts[0] != "Files":
        raise ValueError("--destination must be a relative path under Files/")
    if len(destination.parts) < 2 or any(part in ("", ".", "..") for part in destination.parts):
        raise ValueError("--destination must identify a file without traversal segments")
    return destination


def build_url(workspace_id: str, lakehouse_id: str, path: PurePosixPath, query: dict[str, str]) -> str:
    return (
        f"{ONELAKE_HOST}/{workspace_id}/{lakehouse_id}/"
        f"{urllib.parse.quote(path.as_posix(), safe='/')}?{urllib.parse.urlencode(query)}"
    )


def send_request(
    method: str,
    url: str,
    token: str,
    *,
    data: bytes | None = None,
    allowed_statuses: tuple[int, ...] = (200,),
    allowed_errors: tuple[tuple[int, str], ...] = (),
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
            "x-ms-version": API_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            if response.status not in allowed_statuses:
                raise RuntimeError(f"OneLake returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        error_code = exc.headers.get("x-ms-error-code", "")
        if (exc.code, error_code) not in allowed_errors:
            raise RuntimeError(
                f"OneLake returned HTTP {exc.code} ({error_code or 'unknown error'})"
            ) from exc


def upload(
    source: Path,
    workspace_id: str,
    lakehouse_id: str,
    destination: PurePosixPath,
    token: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, int | str]:
    content = source.read_bytes()

    current = PurePosixPath("Files")
    for part in destination.parent.parts[1:]:
        current /= part
        send_request(
            "PUT",
            build_url(workspace_id, lakehouse_id, current, {"resource": "directory"}),
            token,
            allowed_statuses=(201,),
            allowed_errors=((409, "PathAlreadyExists"),),
            timeout_seconds=timeout_seconds,
        )

    send_request(
        "PUT",
        build_url(workspace_id, lakehouse_id, destination, {"resource": "file"}),
        token,
        allowed_statuses=(201,),
        timeout_seconds=timeout_seconds,
    )
    send_request(
        "PATCH",
        build_url(
            workspace_id,
            lakehouse_id,
            destination,
            {"action": "append", "position": "0"},
        ),
        token,
        data=content,
        allowed_statuses=(202,),
        timeout_seconds=timeout_seconds,
    )
    send_request(
        "PATCH",
        build_url(
            workspace_id,
            lakehouse_id,
            destination,
            {"action": "flush", "position": str(len(content))},
        ),
        token,
        allowed_statuses=(200,),
        timeout_seconds=timeout_seconds,
    )

    return {
        "bytes": len(content),
        "destination": destination.as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def read_private_token_file(path: Path) -> str:
    with path.open(encoding="utf-8") as token_file:
        if os.name != "nt" and stat.S_IMODE(os.fstat(token_file.fileno()).st_mode) & 0o077:
            raise PermissionError("--token-file must not be accessible by group or other users")
        return token_file.read().strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--lakehouse-id", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--token-file", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args()

    if args.timeout_seconds <= 0:
        raise SystemExit("--timeout-seconds must be greater than zero")
    token = read_private_token_file(args.token_file)
    if not token:
        raise SystemExit("--token-file is empty")

    result = upload(
        args.source,
        validated_uuid(args.workspace_id, "--workspace-id"),
        validated_uuid(args.lakehouse_id, "--lakehouse-id"),
        validated_destination(args.destination),
        token,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
