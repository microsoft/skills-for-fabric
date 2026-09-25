from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from cash_tower.models import LedgerRow, SourceRecord

ZERO = Decimal("0")
REJECT_WORDS = ("reject", "reversal", "refund")


class _UnionFind:
    def __init__(self, keys: list[str]):
        self.parent = {key: key for key in keys}

    def find(self, key: str) -> str:
        if self.parent[key] != key:
            self.parent[key] = self.find(self.parent[key])
        return self.parent[key]

    def union(self, left: str, right: str) -> None:
        root_left, root_right = self.find(left), self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


@dataclass
class MatchResult:
    ledger: list[LedgerRow]
    candidates: list[dict[str, Any]] = field(default_factory=list)


def reconcile(
    records: list[SourceRecord],
    amount_tolerance: Decimal = Decimal("0.01"),
    settlement_window_days: int = 3,
) -> MatchResult:
    """Apply exact-key matching in a deterministic, reviewable waterfall."""
    uf = _UnionFind([record.record_id for record in records])
    rules: dict[str, list[str]] = defaultdict(list)
    fields: dict[str, set[str]] = defaultdict(set)
    mismatch: set[str] = set()
    timing: set[str] = set()
    variances: dict[str, list[Decimal]] = defaultdict(list)

    def link(members: list[SourceRecord], rule: str, used_fields: list[str],
             amount_variance: Decimal = ZERO, as_timing: bool = False,
             as_mismatch: bool = False) -> None:
        if not members:
            return
        first = members[0].record_id
        for member in members[1:]:
            uf.union(first, member.record_id)
        for member in members:
            rules[member.record_id].append(rule)
            fields[member.record_id].update(used_fields)
            variances[member.record_id].append(amount_variance)
            if as_timing:
                timing.add(member.record_id)
            if as_mismatch:
                mismatch.add(member.record_id)

    # Duplicate transaction identifiers are never auto-matched.
    by_source_id: dict[tuple[str, str], list[SourceRecord]] = defaultdict(list)
    for record in records:
        if record.transaction_id:
            by_source_id[(record.source, record.transaction_id)].append(record)
    duplicate_ids = {
        item.record_id for group in by_source_id.values() if len(group) > 1 for item in group
    }
    invalid_ids = {item.record_id for item in records if item.quality_issues}

    snappay = [item for item in records if item.source == "SnapPay"]
    bluepay = [item for item in records if item.source == "BluePay"]
    bmo = [item for item in records if item.source == "BMO"]
    jde = [item for item in records if item.source == "JDE"]
    rejected = {
        item.record_id for item in records
        if item.status and any(word in item.status.casefold() for word in REJECT_WORDS)
    }

    # Step 1: exact transaction identifier, followed by amount tolerance.
    snap_by_id = _group(snappay, lambda r: r.transaction_id)
    blue_by_id = _group(bluepay, lambda r: r.transaction_id)
    for identifier in sorted(snap_by_id.keys() & blue_by_id.keys()):
        left, right = snap_by_id[identifier], blue_by_id[identifier]
        if any(item.record_id in invalid_ids for item in left + right):
            continue
        if len(left) != 1 or len(right) != 1:
            duplicate_ids.update(item.record_id for item in left + right)
            continue
        if left[0].record_id in duplicate_ids or right[0].record_id in duplicate_ids:
            continue
        difference = _sum_amount(left) - _sum_amount(right)
        link(left + right, "SnapPay-BluePay exact transaction ID",
             ["transaction_id", "amount"], difference,
             as_mismatch=abs(difference) > amount_tolerance)

    # Step 2: exact backend/customer reference, grouped totals support settlement files.
    blue_by_ref = _group(bluepay, _reference_key)
    bmo_by_ref = _group(bmo, _reference_key)
    for reference in sorted(blue_by_ref.keys() & bmo_by_ref.keys()):
        left, right = blue_by_ref[reference], bmo_by_ref[reference]
        if any(item.record_id in invalid_ids for item in left + right):
            continue
        if any(item.record_id in duplicate_ids for item in left + right):
            continue
        difference = _sum_amount(left) - _sum_amount(right)
        settlement_lag = _settlement_lag(left, right)
        is_timing = 0 < settlement_lag <= settlement_window_days
        fields_used = sorted({
            _reference_field(item) for item in left + right if _reference_field(item)
        })
        link(left + right, "BluePay-BMO exact backend/customer reference",
             fields_used + ["amount"],
             difference, as_timing=is_timing and abs(difference) <= amount_tolerance,
             as_mismatch=abs(difference) > amount_tolerance)

    # Step 3: exact batch number and grouped batch totals. Prefer SnapPay to avoid double counting
    # the same underlying transactions already represented in BluePay.
    upstream: dict[str, list[SourceRecord]] = {}
    for batch in sorted({item.batch_number for item in snappay + bluepay if item.batch_number}):
        snap_batch = [item for item in snappay if item.batch_number == batch]
        upstream[batch] = snap_batch or [item for item in bluepay if item.batch_number == batch]
    jde_by_batch = _group(jde, lambda r: r.batch_number)
    for batch in sorted(upstream.keys() & jde_by_batch.keys()):
        left, right = upstream[batch], jde_by_batch[batch]
        if any(item.record_id in invalid_ids for item in left + right):
            continue
        if any(item.record_id in duplicate_ids for item in left + right):
            continue
        difference = _sum_amount(left) - _sum_amount(right)
        link(left + right, "Payment-JDE exact batch number",
             ["batch_number", "amount"], difference,
             as_mismatch=abs(difference) > amount_tolerance)

    # Date proximity is advisory only. It never unions components or changes confirmed status.
    candidates = _date_candidates(records, uf, settlement_window_days)

    components: dict[str, list[SourceRecord]] = defaultdict(list)
    for record in records:
        components[uf.find(record.record_id)].append(record)

    ledger: list[LedgerRow] = []
    for component in components.values():
        source_names = {item.source for item in component}
        ids = {item.record_id for item in component}
        lineage = {
            source: [
                {
                    "transaction_id": item.transaction_id,
                    "batch_number": item.batch_number,
                    "backend_id": item.backend_id,
                    "customer_reference": item.customer_reference,
                    "amount": str(item.amount) if item.amount is not None else None,
                    "transaction_date": item.transaction_date.isoformat() if item.transaction_date else None,
                    "settlement_date": item.settlement_date.isoformat() if item.settlement_date else None,
                    "source_file": item.source_file,
                    "source_worksheet": item.source_worksheet,
                    "source_row": item.source_row,
                    "record_id": item.record_id,
                }
                for item in component if item.source == source
            ]
            for source in ("SnapPay", "BluePay", "BMO", "JDE")
        }
        all_rules = list(dict.fromkeys(rule for item in component for rule in rules[item.record_id]))
        all_fields = sorted(set().union(*(fields[item.record_id] for item in component)))
        is_reject = bool(ids & rejected)
        is_duplicate = bool(ids & duplicate_ids)
        is_mismatch = bool(ids & mismatch)
        is_timing = bool(ids & timing)
        if is_reject:
            status = "Reject/Reversal/Refund"
        elif is_duplicate:
            status = "Duplicate Identifier"
        elif is_mismatch:
            status = "Amount Mismatch"
        elif ids & invalid_ids:
            status = "Unmatched / Research Required"
        elif is_timing:
            status = "Timing Difference"
        elif {"SnapPay", "BluePay", "BMO", "JDE"}.issubset(source_names):
            status = "Fully Matched"
        elif "SnapPay" in source_names and "BluePay" not in source_names:
            status = "Missing from BluePay"
        elif "BluePay" in source_names and "BMO" not in source_names:
            status = "Missing from Bank"
        elif "SnapPay" in source_names and "BMO" not in source_names:
            status = "Missing from Bank"
        elif "BMO" in source_names and "BluePay" not in source_names:
            status = "Missing from BluePay"
        elif ("SnapPay" in source_names or "BluePay" in source_names or "BMO" in source_names) and "JDE" not in source_names:
            status = "Missing from GL"
        else:
            status = "Unmatched / Research Required"
        exception_type = "" if status == "Fully Matched" else status
        component_variance = next(
            (value for item in component for value in variances[item.record_id] if value != ZERO),
            ZERO,
        )
        reconciliation_id = str(uuid4())
        for item in component:
            ledger.append(LedgerRow(
                reconciliation_id=reconciliation_id,
                source_record_id=item.record_id,
                source=item.source,
                status=status,
                exception_type=exception_type,
                match_rule="; ".join(all_rules) if all_rules else "No confirmed match",
                fields_used=all_fields,
                source_file=item.source_file,
                source_worksheet=item.source_worksheet,
                source_row=item.source_row,
                transaction_id=item.transaction_id,
                account_type=item.account_type,
                batch_number=item.batch_number,
                backend_id=item.backend_id,
                customer_reference=item.customer_reference,
                amount=item.amount,
                amount_variance=component_variance,
                transaction_date=item.transaction_date,
                settlement_date=item.settlement_date,
                lineage=lineage,
                raw_values=item.raw_values,
                quality_issues=item.quality_issues,
                algorithm_status=status,
            ))
    return MatchResult(ledger=ledger, candidates=candidates)


def _group(records: list[SourceRecord], key_fn: Any) -> dict[Any, list[SourceRecord]]:
    result: dict[Any, list[SourceRecord]] = defaultdict(list)
    for record in records:
        key = key_fn(record)
        if key:
            result[key].append(record)
    return dict(result)


def _reference_key(record: SourceRecord) -> str | None:
    if record.backend_id:
        return record.backend_id
    if record.customer_reference:
        return record.customer_reference
    return None


def _reference_field(record: SourceRecord) -> str | None:
    if record.backend_id:
        return "backend_id"
    if record.customer_reference:
        return "customer_reference"
    return None


def _sum_amount(records: list[SourceRecord]) -> Decimal:
    return sum((item.amount or ZERO for item in records), ZERO)


def _settlement_lag(blue_records: list[SourceRecord], bank_records: list[SourceRecord]) -> int:
    bp_dates = [item.settlement_date or item.transaction_date for item in blue_records]
    bank_dates = [item.settlement_date or item.transaction_date for item in bank_records]
    valid_left = [item for item in bp_dates if isinstance(item, date)]
    valid_right = [item for item in bank_dates if isinstance(item, date)]
    if not valid_left or not valid_right:
        return 0
    return (max(valid_right) - max(valid_left)).days


def _date_candidates(
    records: list[SourceRecord], uf: _UnionFind, window_days: int
) -> list[dict[str, Any]]:
    candidates = []
    left_sources = {"SnapPay", "BluePay"}
    date_index: dict[tuple[str, date], list[SourceRecord]] = defaultdict(list)
    for record in records:
        if record.source in {"BluePay", "BMO"} and record.transaction_date:
            date_index[(record.source, record.transaction_date)].append(record)
    for left in records:
        if left.source not in left_sources or not left.transaction_date:
            continue
        target_sources = ("BluePay",) if left.source == "SnapPay" else ("BMO",)
        for source in target_sources:
            for delta in range(-window_days, window_days + 1):
                try:
                    target_date = left.transaction_date + timedelta(days=delta)
                except OverflowError:
                    continue
                for right in date_index.get((source, target_date), []):
                    if uf.find(left.record_id) == uf.find(right.record_id):
                        continue
                    candidates.append({
                        "left_record_id": left.record_id,
                        "left_source": left.source,
                        "right_record_id": right.record_id,
                        "right_source": right.source,
                        "date_delta_days": abs(delta),
                        "candidate_only": True,
                        "reason": "Date window only; no confirmed key match",
                    })
    return candidates
