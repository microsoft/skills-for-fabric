# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
"""Normalize Project Osmos task status values returned by deployed routes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from python_runtime import require_supported_python


require_supported_python()

TERMINAL_STRINGS = {"completed", "failed", "cancelled", "canceled"}
STATUS_BY_CODE = {0: "Created", 1: "Running", 2: "Cancelling", 3: "Cancelled", 4: "Completed", 5: "Failed"}


def status_label(status: Any) -> str:
    if status is None:
        return "Created"
    if isinstance(status, bool):
        return str(status)
    if isinstance(status, int):
        return STATUS_BY_CODE.get(status, f"Status {status}")
    if isinstance(status, str):
        value = status.strip()
        if not value:
            return "Created"
        if value.isdigit():
            return STATUS_BY_CODE.get(int(value), f"Status {value}")
        return value
    return str(status)


def is_terminal_status(status: Any) -> bool:
    return status_label(status).casefold() in TERMINAL_STRINGS


def task_run_details(task: Mapping[str, Any]) -> Mapping[str, Any]:
    run_details = task.get("runDetails")
    return run_details if isinstance(run_details, Mapping) else {}


def _has_value(value: Any) -> bool:
    return bool(value.strip()) if isinstance(value, str) else bool(value)


def is_task_terminal(task: Mapping[str, Any]) -> bool:
    if is_terminal_status(task.get("status")):
        return True
    run_details = task_run_details(task)
    return _has_value(run_details.get("completedAt")) or _has_value(run_details.get("errorMessage"))


def is_task_running(task: Mapping[str, Any]) -> bool:
    return status_label(task.get("status")).casefold() == "running" and not is_task_terminal(task)
