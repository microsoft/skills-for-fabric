from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from cash_tower.models import LedgerRow, SourceRecord

CATEGORIES = {
    "matched": {"Fully Matched"},
    "timing": {"Timing Difference"},
    "rejects_reversals_refunds": {"Reject/Reversal/Refund"},
}


def calculate_controls(
    records: list[SourceRecord], ledger: list[LedgerRow], run_id: str = ""
) -> dict[str, Any]:
    """Reconcile source populations against ledger disposition by source and dollars."""
    record_by_id = {record.record_id: record for record in records}
    ledger_by_id = {row.source_record_id: row for row in ledger}
    sources = sorted({record.source for record in records} | {row.source for row in ledger})
    rows = []
    bridge_issues = []
    for source in sources:
        source_records = [record for record in records if record.source == source]
        source_ledger = [row for row in ledger if row.source == source]
        input_amount = _sum(record.amount for record in source_records)
        disposition: dict[str, list[LedgerRow]] = {name: [] for name in (
            "matched", "timing", "rejects_reversals_refunds", "unresolved"
        )}
        for row in source_ledger:
            for bucket, statuses in CATEGORIES.items():
                if row.status in statuses:
                    disposition[bucket].append(row)
                    break
            else:
                disposition["unresolved"].append(row)

        valid_count = sum(not record.quality_issues for record in source_records)
        rejected_count = len(source_records) - valid_count
        assigned_ids = {row.source_record_id for row in source_ledger}
        absent = [record for record in source_records if record.record_id not in assigned_ids]
        if absent:
            bridge_issues.append(f"{source}: {len(absent)} source rows missing from ledger")
        if len(source_ledger) != len(source_records):
            bridge_issues.append(f"{source}: input row count {len(source_records)} != ledger row count {len(source_ledger)}")

        bucket_amounts = {
            bucket: _sum(row.amount for row in items)
            for bucket, items in disposition.items()
        }
        bucket_rows = {bucket: len(items) for bucket, items in disposition.items()}
        output_amount = sum(bucket_amounts.values(), Decimal("0"))
        output_rows = sum(bucket_rows.values())
        row_difference = len(source_records) - output_rows
        dollar_difference = input_amount - output_amount
        if row_difference or dollar_difference:
            bridge_issues.append(
                f"{source}: completeness bridge differs by {row_difference} rows and {dollar_difference} dollars"
            )

        rows.append({
            "source": source,
            "input_rows": len(source_records),
            "input_dollars": input_amount,
            "valid_rows": valid_count,
            "rejected_rows": rejected_count,
            "matched_rows": bucket_rows["matched"],
            "matched_dollars": bucket_amounts["matched"],
            "timing_rows": bucket_rows["timing"],
            "timing_dollars": bucket_amounts["timing"],
            "rejects_reversals_refunds_rows": bucket_rows["rejects_reversals_refunds"],
            "rejects_reversals_refunds_dollars": bucket_amounts["rejects_reversals_refunds"],
            "unresolved_rows": bucket_rows["unresolved"],
            "unresolved_dollars": bucket_amounts["unresolved"],
            "output_rows": output_rows,
            "output_dollars": output_amount,
            "bridge_row_difference": row_difference,
            "bridge_dollar_difference": dollar_difference,
            "duplicate_identifiers": sum(
                row.status == "Duplicate Identifier" for row in source_ledger
            ),
            "amount_mismatches": sum(row.status == "Amount Mismatch" for row in source_ledger),
            "missing_gl_batches": len({
                row.batch_number for row in source_ledger
                if row.status == "Missing from GL" and row.batch_number
            }),
        })
    status = "Critical" if bridge_issues else "Complete"
    return {
        "run_id": run_id,
        "status": status,
        "bridge_passed": not bridge_issues,
        "bridge_issues": bridge_issues,
        "sources": rows,
        "input_rows": sum(row["input_rows"] for row in rows),
        "input_dollars": sum((row["input_dollars"] for row in rows), Decimal("0")),
        "ledger_rows": len(ledger),
        "candidate_matches": 0,
    }


def _sum(values: Any) -> Decimal:
    return sum((value or Decimal("0") for value in values), Decimal("0"))
