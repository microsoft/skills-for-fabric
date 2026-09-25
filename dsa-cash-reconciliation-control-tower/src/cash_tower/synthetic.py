from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd


def generate_synthetic_files(directory: str | Path) -> list[tuple[str, Path]]:
    """Create four synthetic source files covering clean and exception paths."""
    base = Path(directory)
    paths = {source: base / source for source in ("SnapPay", "BluePay", "BMO", "JDE")}
    for folder in paths.values():
        folder.mkdir(parents=True, exist_ok=True)

    snap = [
        _snap("S-CLEAN", "B-CLEAN", "R-CLEAN", "100.00"),
        _snap("S-GROUP-1", "B-GROUP", "R-GROUP", "40.00"),
        _snap("S-GROUP-2", "B-GROUP", "R-GROUP", "60.00"),
        _snap("S-LATE", "B-LATE", "R-LATE", "20.00"),
        _snap("S-NOBANK", "B-NOBANK", "R-NOBANK", "30.00"),
        _snap("S-NOGL", "B-NOGL", "R-NOGL", "25.00"),
        _snap("S-MISSBLUE", "B-MISSBLUE", "R-MISSBLUE", "12.00"),
        _snap("S-DUP", "B-DUP", "R-DUP", "5.00"),
        _snap("S-DUP", "B-DUP", "R-DUP", "5.00"),
        _snap("S-MISMATCH", "B-MISMATCH", "R-MISMATCH", "10.00"),
        _snap("S-REJECT", "B-REJECT", "R-REJECT", "-8.00", "REJECT"),
        _snap("S-REVERSAL", "B-REVERSAL", "R-REVERSAL", "-4.00", "REVERSAL"),
        _snap("S-REFUND", "B-REFUND", "R-REFUND", "-3.00", "REFUND"),
        _snap("", "B-BLANK", "R-BLANK", "6.00"),
        _snap("S-BAD-DATE", "B-BAD-DATE", "R-BAD-DATE", "7.00", date="not-a-date"),
        _snap("S-BAD-AMOUNT", "B-BAD-AMOUNT", "R-BAD-AMOUNT", "not-money"),
    ]
    blue = [
        _blue("S-CLEAN", "R-CLEAN", "100.00", "B-CLEAN"),
        _blue("S-GROUP-1", "R-GROUP", "40.00", "B-GROUP"),
        _blue("S-GROUP-2", "R-GROUP", "60.00", "B-GROUP"),
        _blue("S-LATE", "R-LATE", "20.00", "B-LATE", settle="2026-09-01"),
        _blue("S-NOBANK", "R-NOBANK", "30.00", "B-NOBANK"),
        _blue("S-NOGL", "R-NOGL", "25.00", "B-NOGL"),
        _blue("S-DUP", "R-DUP", "5.00", "B-DUP"),
        _blue("S-MISMATCH", "R-MISMATCH", "11.00", "B-MISMATCH"),
    ]
    bank = [
        _bank("R-CLEAN", "100.00"),
        _bank("R-GROUP", "100.00", date="2026-09-01"),
        _bank("R-LATE", "20.00", date="2026-09-03"),
        _bank("R-NOGL", "25.00"),
        _bank("R-MISMATCH", "11.00"),
    ]
    gl = [
        _gl("B-CLEAN", "100.00"),
        _gl("B-GROUP", "100.00"),
        _gl("B-LATE", "20.00"),
        _gl("B-NOBANK", "30.00"),
        _gl("B-MISMATCH", "10.00"),
    ]
    generated: list[tuple[str, Path]] = []
    specifications: list[tuple[str, list[dict[str, Any]], str, str]] = [
        ("SnapPay", snap, "snap_pay_synthetic.xlsx", "xlsx"),
        ("BluePay", blue, "blue_pay_synthetic.xlsx", "xlsx"),
        ("BMO", bank, "bmo_synthetic.csv", "csv"),
        ("JDE", gl, "jde_synthetic.csv", "csv"),
    ]
    for source, rows, filename, extension in specifications:
        destination = paths[source] / filename
        frame = pd.DataFrame([{**row, "synthetic_fixture_id": uuid4().hex} for row in rows])
        if extension == "xlsx":
            frame.to_excel(destination, sheet_name="Transactions", index=False, engine="openpyxl")
        else:
            frame.to_csv(destination, index=False)
        generated.append((source, destination))
    return generated


def _snap(
    transaction: str, batch: str, backend: str, amount: str, status: str = "CAPTURED",
    date: str = "2026-09-01", settle: str = "2026-09-01",
) -> dict[str, Any]:
    return {
        "transaction_ref": transaction, "payment_type": "Card", "batch_ref": batch,
        "net_amount": amount, "transaction_dt": date, "settlement_dt": settle,
        "transaction_status": status, "backend_ref": backend, "customer_ref": "",
    }


def _blue(
    transaction: str, backend: str, amount: str, batch: str,
    settle: str = "2026-09-01",
) -> dict[str, Any]:
    return {
        "transaction_ref": transaction, "backend_ref": backend, "net_amount": amount,
        "transaction_dt": "2026-09-01", "settlement_dt": settle, "transaction_status": "SETTLED",
        "batch_ref": batch, "customer_ref": "",
    }


def _bank(backend: str, amount: str, date: str = "2026-09-01") -> dict[str, Any]:
    return {
        "bank_txn_ref": f"BANK-{backend}", "customer_ref": "", "backend_ref": backend,
        "net_amount": amount, "posting_dt": date, "settlement_dt": date,
        "transaction_status": "POSTED", "batch_ref": "",
    }


def _gl(batch: str, amount: str) -> dict[str, Any]:
    return {
        "batch_ref": batch, "net_amount": amount, "posting_dt": "2026-09-02",
        "transaction_status": "POSTED", "transaction_ref": "", "payment_type": "Card",
        "backend_ref": "", "customer_ref": "",
    }
