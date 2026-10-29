from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from cash_tower.models import SourceRecord
from cash_tower.normalization import normalize_amount, normalize_date, normalize_identifier
from openpyxl import load_workbook

CANONICAL_FIELDS = (
    "transaction_id", "account_type", "batch_number", "backend_id",
    "customer_reference", "amount", "transaction_date", "settlement_date", "status",
    "payment_type", "document_number", "document_type",
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
            sheet_rows = [("CSV", pd.read_csv(file_path, dtype=object, keep_default_na=False), 1)]
        elif extension in {".xlsx", ".xlsm"}:
            workbook = load_workbook(file_path, read_only=True, data_only=True)
            try:
                sheet_names = workbook.sheetnames
                header_rows = self.configuration.get("header_rows", {})
                allowed = self.configuration.get("worksheets", [])
                placeholders = [name for name in allowed if str(name).startswith("<")]
                if placeholders:
                    raise AdapterConfigurationError(
                        f"{self.source} worksheet mapping contains example placeholders {placeholders!r}; "
                        "replace them before processing data."
                    )
                if allowed:
                    selected_names = [name for name in sheet_names if name in allowed]
                    if not selected_names:
                        raise AdapterConfigurationError(
                            f"{self.source} workbook {file_path.name!r} has no configured worksheet; "
                            f"expected one of {allowed!r}, found {sheet_names!r}."
                        )
                else:
                    selected_names = sheet_names
                sheet_rows = []
                for name in selected_names:
                    configured_header = header_rows.get(name, 1)
                    header_row = self._resolve_header_row(workbook[name], configured_header)
                    frame = pd.read_excel(
                        file_path, sheet_name=name, header=header_row - 1,
                        dtype=object, engine="openpyxl",
                    )
                    sheet_rows.append((name, frame, header_row))
            finally:
                workbook.close()
        else:
            raise AdapterConfigurationError(f"Unsupported file type {extension!r} for {self.source}.")

        records: list[SourceRecord] = []
        for worksheet, frame, header_row in sheet_rows:
            records.extend(self._adapt_frame(frame, file_path.name, worksheet, digest, header_row))
        return records

    def _resolve_header_row(self, worksheet: Any, configured_header: Any) -> int:
        if isinstance(configured_header, int) and configured_header > 0:
            return configured_header
        if configured_header != "detect":
            raise AdapterConfigurationError(
                f"{self.source} worksheet {worksheet.title!r} has invalid header row configuration."
            )
        candidates = self.configuration.get("columns", {})
        expected = {
            str(name).strip()
            for values in candidates.values()
            for name in (values if isinstance(values, list) else [values])
            if name and not str(name).startswith("<")
        }
        expected.update(
            str(value).strip() for value in self.configuration.get("status_fields", [])
        )
        best_row, best_score = None, 0
        for row_number, row in enumerate(worksheet.iter_rows(max_row=50, values_only=True), start=1):
            score = sum(str(value).strip() in expected for value in row if value is not None)
            if score > best_score:
                best_row, best_score = row_number, score
        if best_row is None or best_score < 2:
            raise AdapterConfigurationError(
                f"{self.source} workbook worksheet {worksheet.title!r}: could not identify "
                "a header row from the configured exact source headers."
            )
        return best_row

    def _adapt_frame(
        self, frame: pd.DataFrame, file_name: str, worksheet: str, digest: str,
        header_row: int = 1,
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

        calculated_amount = bool(self.configuration.get("amount_calculation"))
        missing = [
            field for field in self.configuration.get("required", [])
            if field not in resolved and not (field == "amount" and calculated_amount)
        ]
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
        status_fields = self.configuration.get("status_fields", [])
        amount_calculation = self.configuration.get("amount_calculation")
        document_type_parse = self.configuration.get("document_type_parse")
        for row_number, (_, row) in enumerate(frame.iterrows(), start=header_row + 1):
            if not any(_has_value(value) for value in row.values):
                continue
            raw = {str(key): _json_safe(value) for key, value in row.items()}
            values = {field: row[column] for field, column in resolved.items()}
            if amount_calculation:
                debit_field = amount_calculation["debit"]
                credit_field = amount_calculation["credit"]
                debit_column = headers.get(debit_field)
                credit_column = headers.get(credit_field)
                if debit_column is None or credit_column is None:
                    raise AdapterConfigurationError(
                        f"{self.source} workbook {file_name!r}, worksheet {worksheet!r}: "
                        f"amount calculation requires observed columns {debit_field!r} and {credit_field!r}."
                    )
                debit_raw, credit_raw = row[debit_column], row[credit_column]
                debit_present = _has_value(debit_raw)
                credit_present = _has_value(credit_raw)
                debit = normalize_amount(debit_raw) if debit_present else 0
                credit = normalize_amount(credit_raw) if credit_present else 0
                if not debit_present and not credit_present:
                    values["amount"] = None
                    amount_error = False
                elif debit is None or credit is None:
                    values["amount"] = None
                    amount_error = True
                elif amount_calculation.get("operation") == "credit_minus_debit":
                    values["amount"] = credit - debit
                    amount_error = False
                else:
                    raise AdapterConfigurationError(
                        f"{self.source} has unsupported amount calculation "
                        f"{amount_calculation.get('operation')!r}."
                    )
                if debit_raw not in (None, "") or credit_raw not in (None, ""):
                    values["amount_calculation_inputs"] = (debit_raw, credit_raw)
            else:
                amount_error = False
            if status_fields:
                status_values = []
                for header_name in status_fields:
                    column = headers.get(str(header_name).strip())
                    if column is not None and _has_value(row[column]):
                        status_values.append(str(row[column]).strip())
                values["status"] = " | ".join(value for value in status_values if value) or None
            if document_type_parse:
                source_column = headers.get(document_type_parse["column"])
                if source_column is None:
                    raise AdapterConfigurationError(
                        f"{self.source} workbook {file_name!r}, worksheet {worksheet!r}: "
                        f"document type parsing requires observed column {document_type_parse['column']!r}."
                    )
                source_value = row[source_column]
                pattern = re.compile(document_type_parse["pattern"])
                match = pattern.search(str(source_value).strip()) if _has_value(source_value) else None
                values["document_type"] = match.group(1).strip() if match else source_value
            normalized: dict[str, Any] = {}
            for key, value in values.items():
                if key == "amount":
                    normalized[key] = value if amount_calculation and not amount_error else normalize_amount(value)
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
                if _has_value(raw_value) and normalized[field_name] is None:
                    issues.append(f"Malformed date: {field_name}")
            if "amount" in normalized and _has_value(values.get("amount")) and normalized["amount"] is None:
                issues.append("Malformed amount: amount")
            if amount_error:
                issues.append("Malformed amount: debit/credit calculation")

            records.append(SourceRecord(
                source=self.source,
                transaction_id=normalized.get("transaction_id"),
                account_type=normalized.get("account_type"),
                batch_number=normalized.get("batch_number"),
                backend_id=normalized.get("backend_id"),
                customer_reference=normalized.get("customer_reference"),
                payment_type=normalized.get("payment_type"),
                document_number=normalized.get("document_number"),
                document_type=normalized.get("document_type"),
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


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    try:
        if bool(pd.isna(value)):
            return False
    except (TypeError, ValueError):
        pass
    return bool(str(value).strip())


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
