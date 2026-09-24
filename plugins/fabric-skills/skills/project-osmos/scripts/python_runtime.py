# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
"""Shared Python compatibility guard for Project Osmos helpers."""

import sys


MINIMUM_PYTHON = (3, 11)


def require_supported_python(version_info=None, executable=None):
    """Exit before helper work begins when Python is too old."""
    current = tuple(version_info or sys.version_info)
    if current[:2] >= MINIMUM_PYTHON:
        return

    version = ".".join(str(part) for part in current[:3])
    interpreter = executable or sys.executable or "python"
    minimum = ".".join(str(part) for part in MINIMUM_PYTHON)
    raise SystemExit(
        f"Project Osmos helpers require Python {minimum} or newer; "
        f"{interpreter} is Python {version}. Activate or expose a compatible "
        "existing interpreter. No packages or environments were changed."
    )
