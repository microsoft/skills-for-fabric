#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
"""Validate a composed Project Osmos instruction against a character limit.

Usage (Bash):
    Select and initialize PYTHON_RUNNER as described in
    skills/project-osmos/references/python-helper-runtime.md, then run:
    "${PYTHON_RUNNER[@]}" skills/project-osmos/scripts/check-instruction-length.py --path instruction.txt --limit 9500

Prints JSON containing the measured character count and exits nonzero when the
instruction exceeds the limit. The instruction content is never printed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from python_runtime import require_supported_python


require_supported_python()


def measure(path: Path, limit: int) -> dict[str, int | bool | str]:
    """Measure Unicode characters without exposing instruction content."""
    characters = len(path.read_text(encoding="utf-8"))
    return {
        "path": str(path),
        "characters": characters,
        "limit": limit,
        "remaining": limit - characters,
        "within_limit": characters <= limit,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=9500)
    args = parser.parse_args()
    if args.limit <= 0:
        raise SystemExit("--limit must be greater than zero")
    result = measure(args.path, args.limit)
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0 if result["within_limit"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
