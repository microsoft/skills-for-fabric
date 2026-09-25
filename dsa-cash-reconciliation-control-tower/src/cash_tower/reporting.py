from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

SHEET_NAMES = [
    "Executive Summary",
    "Control Totals",
    "Reconciliation Ledger",
    "Exception Queue",
    "Timing Differences",
    "Rejects Reversals Refunds",
    "Missing from Bank",
    "Missing from GL",
    "Amount Mismatches",
    "Duplicate IDs",
    "Manual Overrides",
    "Source File Inventory",
    "Data Quality Issues",
    "Run Log",
    "Data Dictionary",
]

DATA_DICTIONARY = [
    {"field": "reconciliation_id", "definition": "Stable grouping identifier for source rows linked by confirmed exact-key rules."},
    {"field": "source_record_id", "definition": "Unique source-row identifier retained by the reconciliation ledger."},
    {"field": "source", "definition": "Source system: SnapPay, BluePay, BMO, or JDE."},
    {"field": "status", "definition": "Algorithmic disposition; overrides are shown separately and do not replace it."},
    {"field": "match_rule", "definition": "Deterministic rule(s) used to connect rows; date-only candidates are not included as confirmed rules."},
    {"field": "fields_used", "definition": "Exact canonical fields used in matching."},
    {"field": "amount", "definition": "Signed normalized source amount; raw source text remains in raw_values."},
    {"field": "amount_variance", "definition": "Grouped amount difference at the applicable match step (left total minus right total)."},
    {"field": "source_file", "definition": "Original workbook or CSV basename."},
    {"field": "source_worksheet", "definition": "Worksheet name, or CSV for delimited input."},
    {"field": "source_row", "definition": "One-based spreadsheet row including header row; first data row is 2."},
    {"field": "raw_values", "definition": "Original row values serialized without normalization for review lineage."},
    {"field": "quality_issues", "definition": "Blank required fields or malformed date/amount issues from adapter validation."},
    {"field": "algorithm_status", "definition": "Immutable original algorithmic status, even when an approved override exists."},
    {"field": "override_status", "definition": "Reviewer-approved replacement disposition, maintained in the separate override audit table."},
]


def export_reconciliation_workbook(
    destination: str | Path, run: dict[str, Any]
) -> Path:
    """Build the fixed-sheet review workbook from one persisted run."""
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    ledger = run.get("ledger", [])
    controls = run.get("controls", {})
    overrides = run.get("overrides", [])
    inventory = run.get("inventory", [])
    run_log = run.get("run_log", [])

    effective_rows = []
    overrides_by_reconciliation: dict[str, dict[str, Any]] = {}
    for override in overrides:
        overrides_by_reconciliation[override["reconciliation_id"]] = override
    for row in ledger:
        override = overrides_by_reconciliation.get(row["reconciliation_id"])
        effective_rows.append({
            **row,
            "override_status": override["revised_status"] if override else None,
            "manual_override_id": override["override_id"] if override else None,
        })

    by_status = lambda status: [row for row in effective_rows if row["status"] == status]
    detail_sheets = {
        "Reconciliation Ledger": effective_rows,
        "Exception Queue": [
            *[row for row in effective_rows if row["status"] != "Fully Matched"],
            *[{
                **candidate,
                "status": "Candidate Match - Human Review Required",
                "exception_type": "Date window only; no confirmed key match",
            } for candidate in run.get("candidates", [])],
        ],
        "Timing Differences": by_status("Timing Difference"),
        "Rejects Reversals Refunds": by_status("Reject/Reversal/Refund"),
        "Missing from Bank": by_status("Missing from Bank"),
        "Missing from GL": by_status("Missing from GL"),
        "Amount Mismatches": by_status("Amount Mismatch"),
        "Duplicate IDs": by_status("Duplicate Identifier"),
        "Manual Overrides": overrides,
        "Source File Inventory": inventory,
        "Data Quality Issues": [
            {"source_record_id": row["source_record_id"], "source": row["source"],
             "source_file": row["source_file"], "source_worksheet": row["source_worksheet"],
             "source_row": row["source_row"], "quality_issue": issue}
            for row in effective_rows for issue in row.get("quality_issues", [])
        ],
        "Run Log": run_log + [
            {"level": "ERROR", "message": issue} for issue in controls.get("bridge_issues", [])
        ],
        "Data Dictionary": DATA_DICTIONARY,
    }
    source_controls = controls.get("sources", [])
    executive = [
        {"metric": "Run ID", "value": run.get("run_id", "")},
        {"metric": "Run Status", "value": controls.get("status", "Critical")},
        {"metric": "Completeness Bridge Passed", "value": bool(controls.get("bridge_passed", False))},
        {"metric": "Source Rows", "value": len(ledger)},
        {"metric": "Fully Matched Rows", "value": sum(row["status"] == "Fully Matched" for row in ledger)},
        {"metric": "Timing Difference Rows", "value": sum(row["status"] == "Timing Difference" for row in ledger)},
        {"metric": "Reject/Reversal/Refund Rows", "value": sum(row["status"] == "Reject/Reversal/Refund" for row in ledger)},
        {"metric": "Unresolved Rows", "value": sum(
            row["status"] not in {"Fully Matched", "Timing Difference", "Reject/Reversal/Refund"}
            for row in ledger
        )},
        {"metric": "Date-only Candidate Matches", "value": len(run.get("candidates", []))},
        {"metric": "Manual Overrides", "value": len(overrides)},
    ]
    for summary in source_controls:
        for key in ("input_rows", "input_dollars", "matched_rows", "matched_dollars",
                    "timing_rows", "timing_dollars", "unresolved_rows", "unresolved_dollars"):
            executive.append({
                "metric": f"{summary['source']} {key.replace('_', ' ').title()}",
                "value": summary[key],
            })

    with pd.ExcelWriter(destination_path, engine="openpyxl") as writer:
        pd.DataFrame(executive).pipe(_excel_frame).to_excel(
            writer, sheet_name="Executive Summary", index=False
        )
        pd.DataFrame(source_controls).pipe(_excel_frame).to_excel(
            writer, sheet_name="Control Totals", index=False
        )
        for sheet_name in SHEET_NAMES[2:]:
            rows = detail_sheets.get(sheet_name, [])
            pd.DataFrame(rows).pipe(_excel_frame).to_excel(
                writer, sheet_name=sheet_name, index=False
            )
        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column_cells in sheet.columns:
                width = min(max(max(len(str(cell.value or "")) for cell in column_cells) + 2, 12), 48)
                sheet.column_dimensions[column_cells[0].column_letter].width = width
    return destination_path


def _excel_frame(frame: pd.DataFrame) -> pd.DataFrame:
    def excel_value(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return value
    if frame.empty:
        return frame
    return frame.map(excel_value)
