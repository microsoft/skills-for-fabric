from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from cash_tower.models import SourceRecord
from cash_tower.normalization import normalize_amount, normalize_date, normalize_identifier

CANONICAL_FIELDS = (
    "transaction_id", "account_type", "batch_number", "backend_id",
    "customer_reference", "amount", "transaction_date", "settlement_date", "status",
)
DATE_FIELDS = {"transaction_date", "settlement_date"}
ID_FIELDS = set(CANONICAL_FIELDS) - DATE_FIELDS - {"amount"}


class AdapterConfigurationError(ValueError):
    """Configuration does not describe usable source columns or worksheets."""


def load_mapping_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or not isinstance(config.get("sources"), dict):
        raise AdapterConfigurationError("Mapping YAML must contain a 'sources' mapping.")
    return config


class SourceAdapter:
    def __init__(self, source: str, configuration: dict[str, Any]):
        self.source = source
        self.configuration = configuration

    @classmethod
    def from_yaml(cls, source: str, path: str | Path) -> "SourceAdapter":
        config = load_mapping_config(path)
        if source not in config["sources"]:
            raise AdapterConfigurationError(f"No mapping configured for source {source!r}.")
        return cls(source, config["sources"][source])

    def read(self, path: str | Path, file_hash: str | None = None) -> list[SourceRecord]:
        file_path = Path(path)
        digest = file_hash or hashlib.sha256(file_path.read_bytes()).hexdigest()
        extension = file_path.suffix.lower()
        if extension == ".csv":
            sheets = {"CSV": pd.read_csv(file_path, dtype=object, keep_default_na=False)}
        elif extension in {".xlsx", ".xlsm"}:
            sheets = pd.read_excel(file_path, sheet_name=None, dtype=object, engine="openpyxl")
        else:
            raise AdapterConfigurationError(f"Unsupported file type {extension!r} for {self.source}.")

        allowed = self.configuration.get("worksheets", []) if extension != ".csv" else []
        placeholders = [name for name in allowed if str(name).startswith("<")]
        if placeholders:
            raise AdapterConfigurationError(
                f"{self.source} worksheet mapping contains example placeholders {placeholders!r}; "
                "replace them in config/column_mappings.yaml."
            )
        if allowed:
            selected = {name: frame for name, frame in sheets.items() if name in allowed}
            if not selected:
                raise AdapterConfigurationError(
                    f"{self.source} workbook {file_path.name!r} has no configured worksheet; "
                    f"expected one of {allowed!r}, found {list(sheets)!r}."
                )
            sheets = selected

        records: list[SourceRecord] = []
        for worksheet, frame in sheets.items():
            records.extend(self._adapt_frame(frame, file_path.name, worksheet, digest))
        return records

    def _adapt_frame(
        self, frame: pd.DataFrame, file_name: str, worksheet: str, digest: str
    ) -> list[SourceRecord]:
        mapping = self.configuration.get("columns", {})
        headers = {str(column).strip(): column for column in frame.columns}
        resolved: dict[str, Any] = {}
        for canonical, candidates in mapping.items():
            candidates = candidates if isinstance(candidates, list) else [candidates]
            found = next((headers[str(candidate).strip()] for candidate in candidates
                          if str(candidate).strip() in headers and not str(candidate).startswith("<")), None)
            if found is not None:
                resolved[canonical] = found

        missing = [field for field in self.configuration.get("required", [])
                   if field not in resolved]
        required_any = self.configuration.get("required_any", [])
        if required_any and not any(field in resolved for field in required_any):
            missing.append(f"one of {required_any}")
        if missing:
            raise AdapterConfigurationError(
                f"{self.source} workbook {file_name!r}, worksheet {worksheet!r}: "
                f"required canonical columns could not be mapped: {missing}. "
                f"Available headers: {list(headers)!r}. Update config/column_mappings.yaml."
            )

        records = []
        for row_number, (_, row) in enumerate(frame.iterrows(), start=2):
            raw = {str(key): _json_safe(value) for key, value in row.items()}
            values = {field: row[column] for field, column in resolved.items()}
            normalized: dict[str, Any] = {}
            for key, value in values.items():
                if key == "amount":
                    normalized[key] = normalize_amount(value)
                elif key in DATE_FIELDS:
                    normalized[key] = normalize_date(value)
                elif key in ID_FIELDS:
                    normalized[key] = normalize_identifier(value)
                else:
                    normalized[key] = normalize_identifier(value)

            issues = []
            for required in self.configuration.get("required", []):
                value = normalized.get(required)
                if value is None or value == "":
                    issues.append(f"Blank required field: {required}")
            if self.configuration.get("required_any") and not any(
                normalized.get(field) for field in self.configuration["required_any"]
            ):
                issues.append(
                    "Blank required field: one of " + ", ".join(self.configuration["required_any"])
                )
            for field_name in DATE_FIELDS.intersection(normalized):
                raw_value = values.get(field_name)
                if raw_value is not None and str(raw_value).strip() and normalized[field_name] is None:
                    issues.append(f"Malformed date: {field_name}")
            if "amount" in normalized and values.get("amount") not in (None, "") and normalized["amount"] is None:
                issues.append("Malformed amount: amount")

            records.append(SourceRecord(
                source=self.source,
                transaction_id=normalized.get("transaction_id"),
                account_type=normalized.get("account_type"),
                batch_number=normalized.get("batch_number"),
                backend_id=normalized.get("backend_id"),
                customer_reference=normalized.get("customer_reference"),
                amount=normalized.get("amount"),
                transaction_date=normalized.get("transaction_date"),
                settlement_date=normalized.get("settlement_date"),
                status=normalized.get("status"),
                source_file=file_name,
                source_worksheet=worksheet,
                source_row=row_number,
                file_hash=digest,
                raw_values=raw,
                quality_issues=issues,
            ))
        return records


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, (dict, list, tuple)):
        try:
            if bool(pd.isna(value)):
                return None
        except (TypeError, ValueError):
            pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.loads(json.dumps(value, default=str))


class SnapPayAdapter(SourceAdapter):
    def __init__(self, configuration: dict[str, Any]):
        super().__init__("SnapPay", configuration)


class BluePayAdapter(SourceAdapter):
    def __init__(self, configuration: dict[str, Any]):
        super().__init__("BluePay", configuration)


class BMOAdapter(SourceAdapter):
    def __init__(self, configuration: dict[str, Any]):
        super().__init__("BMO", configuration)


class JDEAdapter(SourceAdapter):
    def __init__(self, configuration: dict[str, Any]):
        super().__init__("JDE", configuration)


ADAPTER_TYPES = {
    "SnapPay": SnapPayAdapter,
    "BluePay": BluePayAdapter,
    "BMO": BMOAdapter,
    "JDE": JDEAdapter,
}
