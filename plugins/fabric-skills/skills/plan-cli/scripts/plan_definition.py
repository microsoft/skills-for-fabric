#!/usr/bin/env python3
"""Strict offline helpers for Fabric Plan definition envelopes."""

from __future__ import annotations

import argparse
import base64
from decimal import Decimal
import json
import math
import re
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit


PUBLIC_API_ORIGIN = "https://api.fabric.microsoft.com"
PUBLIC_BASES = {
    "production": PUBLIC_API_ORIGIN,
    "daily": PUBLIC_API_ORIGIN,
    "msit": PUBLIC_API_ORIGIN,
}
_VISUAL_PATH = re.compile(
    r"^sheets/(?P<sheet>[^/]+)/visuals/(?P<visual>[^/]+)/(?P<file>[^/]+\.json)$"
)


class PlanDefinitionError(ValueError):
    """The supplied Plan definition cannot be used safely."""


def public_base(ring: str = "production") -> str:
    # Every supported ring resolves to the one public Fabric API origin. There is
    # deliberately no environment override: URLs built here carry credentials
    # later, so they must never point at a caller-supplied host.
    if ring not in PUBLIC_BASES:
        raise PlanDefinitionError(
            f"Unsupported public API ring {ring!r}; omit --ring to use the public origin."
        )
    return PUBLIC_BASES[ring]


def validate_scoped_url(url: str, ring: str) -> str:
    expected = urlsplit(public_base(ring))
    parsed = _https_url(url)
    if (
        parsed.netloc != expected.netloc
        or not parsed.path.startswith("/v1/")
    ):
        raise PlanDefinitionError(
            f"Refusing URL outside the selected {ring} Fabric /v1 host."
        )
    return url


def _https_url(url: str) -> SplitResult:
    if not isinstance(url, str) or not url or any(
        ord(char) <= 32 or ord(char) == 127 for char in url
    ) or "\\" in url:
        raise PlanDefinitionError("Malformed HTTPS URL.")
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https" or not parsed.hostname
            or parsed.netloc != parsed.hostname
            or parsed.port is not None or parsed.username is not None
            or parsed.password is not None or "#" in url
        ):
            raise ValueError
    except ValueError:
        raise PlanDefinitionError("Malformed HTTPS URL.") from None
    return parsed


def _operation_uuid(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value
    ) or uuid.UUID(value).int == 0:
        raise PlanDefinitionError("Operation ID must be a nonzero hyphenated UUID.")
    return str(uuid.UUID(value))


def _operation_path(path: str) -> str:
    match = re.fullmatch(r"/v1/operations/([^/]+)(?:/result)?", path)
    if not match:
        raise PlanDefinitionError("LRO URL must identify an operation endpoint.")
    return _operation_uuid(match[1])


def lro_operation_url(
    ring: str, operation_id: str | None = None, location: str | None = None
) -> str:
    """Resolve response metadata without authorizing a new credential host."""
    base = public_base(ring)
    identifier = _operation_uuid(operation_id) if operation_id is not None else None
    parsed = _https_url(location) if location is not None else None
    location_id = _operation_path(parsed.path) if parsed is not None else None
    if identifier is not None:
        if location_id is not None and location_id != identifier:
            raise PlanDefinitionError("LRO Location and x-ms-operation-id conflict.")
        return validate_scoped_url(f"{base}/v1/operations/{identifier}", ring)
    if location is None:
        raise PlanDefinitionError("LRO requires x-ms-operation-id or a same-host Location.")
    validate_scoped_url(location, ring)
    if parsed.path.endswith("/result"):
        raise PlanDefinitionError("Initial LRO Location must identify a status endpoint.")
    return location


def lro_result_url(operation_url: str, ring: str) -> str:
    validate_scoped_url(operation_url, ring)
    parsed = urlsplit(operation_url)
    _operation_path(parsed.path)
    path = parsed.path if parsed.path.rstrip("/").endswith("/result") else (
        f"{parsed.path.rstrip('/')}/result"
    )
    result = urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ""))
    return validate_scoped_url(result, ring)


def load_json(value: str | bytes) -> Any:
    def constant(_value):
        raise PlanDefinitionError("Non-finite JSON numbers are not supported.")

    def number(text):
        if Decimal(text).copy_abs() > 9007199254740991:
            raise PlanDefinitionError("Unsafe JSON numeric precision.")
        result = float(text)
        if not math.isfinite(result):
            raise PlanDefinitionError("Non-finite JSON numbers are not supported.")
        return result

    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise PlanDefinitionError("Duplicate JSON properties are not supported.")
            result[key] = item
        return result

    try:
        loaded = json.loads(value, parse_constant=constant, parse_float=number, object_pairs_hook=unique)
    except (ArithmeticError, ValueError, TypeError, RecursionError):
        raise PlanDefinitionError("Invalid JSON; contents suppressed.") from None
    _reject_lone_surrogates(loaded)
    return loaded


def _reject_lone_surrogates(value: Any) -> None:
    """Reject escaped unpaired surrogates, which UTF-8 output cannot encode.

    json.loads joins valid escaped pairs into one character, so any surrogate
    code point left in a key or string is unpaired.
    """
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            stack.extend(item.keys())
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, str) and any("\ud800" <= ch <= "\udfff" for ch in item):
            raise PlanDefinitionError("Unpaired Unicode surrogate in JSON text; contents suppressed.")


def decode_parts(envelope: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise PlanDefinitionError("Definition envelope must be an object.")
    definition = envelope.get("definition")
    if not isinstance(definition, dict) or not isinstance(definition.get("parts"), list):
        raise PlanDefinitionError("Definition envelope must contain definition.parts.")

    decoded: dict[str, Any] = {}
    for index, part in enumerate(definition["parts"]):
        if not isinstance(part, dict):
            raise PlanDefinitionError(f"Definition part {index} is not an object.")
        path = part.get("path")
        if not isinstance(path, str) or not path or path in decoded:
            raise PlanDefinitionError(f"Definition part {index} has a missing or duplicate path.")
        if part.get("payloadType") != "InlineBase64":
            raise PlanDefinitionError(f"Part {path!r} is not InlineBase64.")
        payload = part.get("payload")
        if not isinstance(payload, str):
            raise PlanDefinitionError(f"Part {path!r} has no string payload.")
        try:
            raw = base64.b64decode(payload, validate=True)
            text = raw.decode("utf-8")
            document = load_json(text)
        except ValueError as exc:
            raise PlanDefinitionError(f"Part {path!r} is not valid base64 UTF-8 JSON.") from exc
        if not isinstance(document, dict):
            raise PlanDefinitionError(f"Part {path!r} must decode to a JSON object.")
        decoded[path] = document

    if "definition.json" not in decoded:
        raise PlanDefinitionError("Decoded definition is missing definition.json.")
    return decoded


def map_definition(parts: dict[str, Any]) -> dict[str, Any]:
    root = parts.get("definition.json")
    if not isinstance(root, dict) or not isinstance(root.get("sheets"), list):
        raise PlanDefinitionError("definition.json must contain a sheets array.")

    seen_sheets: set[str] = set()
    seen_visuals: set[tuple[str, str]] = set()
    sheets: list[dict[str, Any]] = []
    for sheet in root["sheets"]:
        if not isinstance(sheet, dict):
            raise PlanDefinitionError("Every sheet entry must be an object.")
        sheet_id = sheet.get("recordGuid")
        if not isinstance(sheet_id, str) or not sheet_id or sheet_id in seen_sheets:
            raise PlanDefinitionError("Sheet recordGuid values must be nonempty and unique.")
        seen_sheets.add(sheet_id)
        sheet_path = f"sheets/{sheet_id}/sheet.json"
        visuals = []
        references = sheet.get("workloadItemEntityVisuals", [])
        if not isinstance(references, list):
            raise PlanDefinitionError(f"Sheet {sheet_id!r} has an invalid visual list.")
        for visual in references:
            if not isinstance(visual, dict):
                raise PlanDefinitionError(f"Sheet {sheet_id!r} has an invalid visual reference.")
            visual_id = visual.get("visualId")
            key = (sheet_id, visual_id)
            if not isinstance(visual_id, str) or not visual_id or key in seen_visuals:
                raise PlanDefinitionError("Visual IDs must be nonempty and unique within a sheet.")
            seen_visuals.add(key)
            prefix = f"sheets/{sheet_id}/visuals/{visual_id}/"
            visuals.append(
                {
                    "id": visual_id,
                    "type": visual.get("visualType"),
                    "parts": sorted(path for path in parts if path.startswith(prefix)),
                }
            )
        sheets.append(
            {
                "id": sheet_id,
                "name": sheet.get("displayName"),
                "type": sheet.get("sheetType"),
                "sheetPartPresent": sheet_path in parts,
                "visuals": visuals,
            }
        )

    orphan_visual_parts = []
    for path in parts:
        match = _VISUAL_PATH.fullmatch(path)
        if match and (match["sheet"], match["visual"]) not in seen_visuals:
            orphan_visual_parts.append(path)
    if orphan_visual_parts:
        raise PlanDefinitionError(
            f"Visual parts do not map to definition.json: {', '.join(sorted(orphan_visual_parts))}"
        )
    summary = {"name": root.get("workloadItemName"), "sheets": sheets}
    if isinstance(root.get("semanticModelReference"), dict):
        summary["semanticModel"] = root["semanticModelReference"]
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("envelope", type=Path, nargs="?")
    # Optional and kept for compatibility; every value resolves to the same public origin.
    parser.add_argument("--ring", choices=tuple(PUBLIC_BASES), default="production",
                        help=argparse.SUPPRESS)
    parser.add_argument("--lro", action="store_true")
    parser.add_argument("--operation-id")
    parser.add_argument("--location")
    args = parser.parse_args(argv)
    if args.lro and args.envelope is not None:
        parser.error("--lro does not accept an envelope.")
    if not args.lro and (
        args.envelope is None or args.operation_id is not None or args.location is not None
    ):
        parser.error("Supply an envelope, or use --lro with response headers.")
    try:
        if args.lro:
            operation = lro_operation_url(args.ring, args.operation_id, args.location)
            summary = {
                "operationUrl": operation,
                "resultUrl": lro_result_url(operation, args.ring),
                "networkUsed": False,
            }
        else:
            envelope = load_json(args.envelope.read_text(encoding="utf-8"))
            parts = decode_parts(envelope)
            summary = map_definition(parts)
            summary["partPaths"] = sorted(parts)
    except UnicodeDecodeError:
        parser.exit(2, "plan definition error: envelope is not valid UTF-8; contents suppressed.\n")
    except (OSError, json.JSONDecodeError, PlanDefinitionError) as exc:
        parser.exit(2, f"plan definition error: {exc}\n")
    summary["ring"] = args.ring
    summary["publicBase"] = public_base(args.ring)
    output = json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False)
    sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
