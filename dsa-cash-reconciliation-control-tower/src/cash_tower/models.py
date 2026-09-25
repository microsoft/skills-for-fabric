from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4


@dataclass
class SourceRecord:
    source: str
    transaction_id: str | None = None
    account_type: str | None = None
    batch_number: str | None = None
    backend_id: str | None = None
    customer_reference: str | None = None
    amount: Decimal | None = None
    transaction_date: date | None = None
    settlement_date: date | None = None
    status: str | None = None
    source_file: str = ""
    source_worksheet: str = ""
    source_row: int = 0
    file_hash: str = ""
    raw_values: dict[str, Any] = field(default_factory=dict)
    quality_issues: list[str] = field(default_factory=list)
    record_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["amount"] = str(self.amount) if self.amount is not None else None
        result["transaction_date"] = self.transaction_date.isoformat() if self.transaction_date else None
        result["settlement_date"] = self.settlement_date.isoformat() if self.settlement_date else None
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SourceRecord":
        fields = dict(value)
        fields["amount"] = Decimal(fields["amount"]) if fields.get("amount") is not None else None
        fields["transaction_date"] = date.fromisoformat(fields["transaction_date"]) if fields.get("transaction_date") else None
        fields["settlement_date"] = date.fromisoformat(fields["settlement_date"]) if fields.get("settlement_date") else None
        return cls(**fields)


@dataclass
class LedgerRow:
    reconciliation_id: str
    source_record_id: str
    source: str
    status: str
    exception_type: str
    match_rule: str
    fields_used: list[str]
    source_file: str
    source_worksheet: str
    source_row: int
    transaction_id: str | None
    account_type: str | None
    batch_number: str | None
    backend_id: str | None
    customer_reference: str | None
    amount: Decimal | None
    amount_variance: Decimal
    transaction_date: date | None
    settlement_date: date | None
    lineage: dict[str, list[dict[str, Any]]]
    raw_values: dict[str, Any]
    quality_issues: list[str]
    algorithm_status: str
    override_status: str | None = None
    manual_override_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["amount"] = str(self.amount) if self.amount is not None else None
        result["amount_variance"] = str(self.amount_variance)
        result["transaction_date"] = self.transaction_date.isoformat() if self.transaction_date else None
        result["settlement_date"] = self.settlement_date.isoformat() if self.settlement_date else None
        return result


@dataclass
class ManualOverride:
    override_id: str
    reconciliation_id: str
    prior_status: str
    revised_status: str
    reason: str
    preparer: str
    timestamp: datetime
    approver: str | None = None
    supporting_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result
