from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from cash_tower.models import LedgerRow, ManualOverride, SourceRecord


class ReconciliationRepository(Protocol):
    def save_run(
        self, run_id: str, period_start: str, period_end: str,
        records: list[SourceRecord], ledger: list[LedgerRow],
        controls: dict[str, Any], candidates: list[dict[str, Any]],
        inventory: list[dict[str, Any]], run_log: list[dict[str, Any]],
    ) -> None: ...

    def get_run(self, run_id: str) -> dict[str, Any] | None: ...

    def list_runs(self) -> list[dict[str, Any]]: ...

    def is_file_registered(
        self, digest: str, period_start: str | None = None, period_end: str | None = None
    ) -> bool: ...

    def add_override(self, run_id: str, override: ManualOverride) -> None: ...


class SQLiteRepository:
    """Prototype storage implementation; consumers depend on the repository protocol."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    controls_json TEXT NOT NULL,
                    candidates_json TEXT NOT NULL,
                    inventory_json TEXT NOT NULL,
                    run_log_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS source_records (
                    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                    record_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, record_id)
                );
                CREATE TABLE IF NOT EXISTS reconciliation_ledger (
                    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                    source_record_id TEXT NOT NULL,
                    reconciliation_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    row_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, source_record_id)
                );
                CREATE INDEX IF NOT EXISTS ix_ledger_reconciliation
                    ON reconciliation_ledger(run_id, reconciliation_id);
                CREATE TABLE IF NOT EXISTS manual_overrides (
                    override_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(run_id),
                    reconciliation_id TEXT NOT NULL,
                    prior_status TEXT NOT NULL,
                    revised_status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    preparer TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    approver TEXT,
                    supporting_reference TEXT
                );
                CREATE TABLE IF NOT EXISTS file_inventory (
                    content_hash TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS run_files (
                    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                    content_hash TEXT NOT NULL,
                    PRIMARY KEY (run_id, content_hash)
                );
                CREATE INDEX IF NOT EXISTS ix_run_files_hash ON run_files(content_hash);
                CREATE TABLE IF NOT EXISTS application_state (
                    state_key TEXT PRIMARY KEY,
                    state_value TEXT NOT NULL
                );
            """)

    def save_run(
        self, run_id: str, period_start: str, period_end: str,
        records: list[SourceRecord], ledger: list[LedgerRow],
        controls: dict[str, Any], candidates: list[dict[str, Any]],
        inventory: list[dict[str, Any]], run_log: list[dict[str, Any]],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, period_start, period_end, datetime.now(timezone.utc).isoformat(),
                 controls["status"], _json(controls), _json(candidates), _json(inventory), _json(run_log)),
            )
            connection.executemany(
                "INSERT INTO source_records VALUES (?, ?, ?, ?)",
                [(run_id, record.record_id, record.source, _json(record.to_dict())) for record in records],
            )
            connection.executemany(
                "INSERT INTO reconciliation_ledger VALUES (?, ?, ?, ?, ?, ?)",
                [(run_id, row.source_record_id, row.reconciliation_id, row.source, row.status,
                  _json(row.to_dict())) for row in ledger],
            )
            connection.executemany(
                "INSERT OR IGNORE INTO run_files VALUES (?, ?)",
                [(run_id, item["sha256"]) for item in inventory if item.get("sha256")],
            )
            for item in inventory:
                if item.get("sha256"):
                    connection.execute(
                        """INSERT OR IGNORE INTO file_inventory
                           VALUES (?, ?, ?, ?, ?)""",
                        (item["sha256"], item["name"], item.get("source", "Unknown"),
                         _json(item), datetime.now(timezone.utc).isoformat()),
                    )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            run = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if run is None:
                return None
            return {
                "run_id": run["run_id"],
                "period_start": run["period_start"],
                "period_end": run["period_end"],
                "created_at": run["created_at"],
                "status": run["status"],
                "controls": _loads(run["controls_json"]),
                "candidates": _loads(run["candidates_json"]),
                "inventory": _loads(run["inventory_json"]),
                "run_log": _loads(run["run_log_json"]),
                "records": [
                    _loads(row["record_json"]) for row in connection.execute(
                        "SELECT record_json FROM source_records WHERE run_id = ? ORDER BY source, record_id",
                        (run_id,),
                    )
                ],
                "ledger": [
                    _loads(row["row_json"]) for row in connection.execute(
                        "SELECT row_json FROM reconciliation_ledger WHERE run_id = ? ORDER BY source, source_record_id",
                        (run_id,),
                    )
                ],
                "overrides": self.list_overrides(run_id, connection),
            }

    def list_runs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT run_id, period_start, period_end, created_at, status FROM runs ORDER BY created_at DESC"
            )]

    def register_file(self, metadata: dict[str, Any]) -> bool:
        """Return True once for a new content hash and False for a duplicate."""
        digest = metadata.get("sha256")
        if not digest:
            raise ValueError("A SHA-256 digest is required for duplicate-file prevention.")
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT OR IGNORE INTO file_inventory
                   VALUES (?, ?, ?, ?, ?)""",
                (digest, metadata["name"], metadata.get("source", "Unknown"), _json(metadata),
                 datetime.now(timezone.utc).isoformat()),
            )
            return cursor.rowcount == 1

    def is_file_registered(
        self, digest: str, period_start: str | None = None, period_end: str | None = None
    ) -> bool:
        with self._connect() as connection:
            if period_start is not None and period_end is not None:
                return connection.execute(
                    """SELECT 1 FROM run_files f JOIN runs r ON r.run_id = f.run_id
                       WHERE f.content_hash = ? AND r.period_start = ? AND r.period_end = ? LIMIT 1""",
                    (digest, period_start, period_end),
                ).fetchone() is not None
            return connection.execute(
                "SELECT 1 FROM file_inventory WHERE content_hash = ?", (digest,)
            ).fetchone() is not None

    def add_override(self, run_id: str, override: ManualOverride) -> None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT row_json FROM reconciliation_ledger
                   WHERE run_id = ? AND reconciliation_id = ? LIMIT 1""",
                (run_id, override.reconciliation_id),
            ).fetchone()
            if row is None:
                raise ValueError(f"Reconciliation {override.reconciliation_id!r} is not in run {run_id!r}.")
            if _loads(row["row_json"])["algorithm_status"] != override.prior_status:
                raise ValueError("Override prior_status must equal the immutable algorithm_status.")
            if not all(value.strip() for value in (
                override.prior_status, override.revised_status, override.reason, override.preparer
            )):
                raise ValueError("Prior status, revised status, reason, and preparer are required.")
            connection.execute(
                """INSERT INTO manual_overrides VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (override.override_id, run_id, override.reconciliation_id, override.prior_status,
                 override.revised_status, override.reason, override.preparer, override.timestamp.isoformat(),
                 override.approver, override.supporting_reference),
            )

    def list_overrides(
        self, run_id: str, connection: sqlite3.Connection | None = None
    ) -> list[dict[str, Any]]:
        if connection is None:
            with self._connect() as active:
                return self.list_overrides(run_id, active)
        return [dict(row) for row in connection.execute(
            """SELECT override_id, reconciliation_id, prior_status, revised_status, reason,
                      preparer, timestamp, approver, supporting_reference
               FROM manual_overrides WHERE run_id = ? ORDER BY timestamp""",
            (run_id,),
        )]

    def get_state(self, key: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_value FROM application_state WHERE state_key = ?", (key,)
            ).fetchone()
            return row["state_value"] if row else None

    def set_state(self, key: str, value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO application_state VALUES (?, ?)", (key, value)
            )


def _json(value: Any) -> str:
    return json.dumps(value, default=_serialize, ensure_ascii=False)


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Value is not JSON serializable: {type(value).__name__}")


def _loads(value: str) -> Any:
    return json.loads(value)
