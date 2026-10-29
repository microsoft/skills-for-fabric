from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def validate_configuration(path: str | Path) -> list[str]:
    errors: list[str] = []
    try:
        with Path(path).open(encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        return [f"Cannot read YAML configuration: {exc}"]
    if not isinstance(config, dict):
        return ["Configuration must be a YAML mapping."]
    sources = config.get("sources")
    if not isinstance(sources, dict):
        return ["Configuration must contain a 'sources' mapping."]
    expected_sources = {"SnapPay", "BluePay", "BMO", "JDE"}
    missing_sources = expected_sources - set(sources)
    if missing_sources:
        errors.append(f"Missing source mappings: {sorted(missing_sources)}")
    for source, source_config in sources.items():
        if not isinstance(source_config, dict):
            errors.append(f"{source}: source settings must be a mapping.")
            continue
        worksheets = source_config.get("worksheets", [])
        columns = source_config.get("columns", {})
        required = source_config.get("required", [])
        if not worksheets:
            errors.append(f"{source}: configure at least one worksheet.")
        if not required:
            errors.append(f"{source}: configure required canonical columns.")
        if not isinstance(columns, dict):
            errors.append(f"{source}: 'columns' must be a mapping.")
            continue
        for label, values in [("worksheet", worksheets), *[(f"header {key}", value if isinstance(value, list) else [value])
                                                             for key, value in columns.items()]]:
            values = values if isinstance(values, list) else [values]
            if any(str(value).startswith("<") for value in values):
                errors.append(f"{source}: replace example placeholder(s) in {label}.")
        missing_required = [field for field in required if field not in columns]
        if missing_required:
            errors.append(f"{source}: required fields missing column mapping: {missing_required}")
        required_any = source_config.get("required_any", [])
        if required_any and not any(field in columns for field in required_any):
            errors.append(f"{source}: configure at least one of these reference columns: {required_any}")
    matching = config.get("matching", {})
    try:
        if float(matching.get("amount_tolerance", -1)) < 0:
            errors.append("matching.amount_tolerance must be zero or greater.")
    except (TypeError, ValueError):
        errors.append("matching.amount_tolerance must be numeric.")
    try:
        if int(matching.get("settlement_window_days", -1)) < 0:
            errors.append("matching.settlement_window_days must be zero or greater.")
    except (TypeError, ValueError):
        errors.append("matching.settlement_window_days must be a non-negative integer.")
    return errors
