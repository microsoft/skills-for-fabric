from __future__ import annotations

import hashlib
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from cash_tower.adapters import ADAPTER_TYPES, AdapterConfigurationError, SourceAdapter, load_mapping_config
from cash_tower.controls import calculate_controls
from cash_tower.matching import reconcile
from cash_tower.models import SourceRecord
from cash_tower.repository import ReconciliationRepository

LOGGER = logging.getLogger(__name__)


def run_reconciliation(
    files: Iterable[tuple[str, str | Path] | tuple[str, str | Path, dict[str, Any]]],
    config_path: str | Path,
    repository: ReconciliationRepository,
    period_start: date,
    period_end: date,
) -> dict[str, Any]:
    if period_start > period_end:
        raise ValueError("Reporting-period start must be on or before its end.")
    config = load_mapping_config(config_path)
    run_id = str(uuid4())
    records: list[SourceRecord] = []
    inventory: list[dict[str, Any]] = []
    run_log: list[dict[str, Any]] = []
    hashes_this_run: set[str] = set()
    files_processed: set[tuple[str, str]] = set()
    duplicate_files: list[str] = []
    for file_entry in files:
        if len(file_entry) == 2:
            source, file_path_value = file_entry
            source_metadata: dict[str, Any] = {}
        else:
            source, file_path_value, source_metadata = file_entry
        path = Path(file_path_value)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        item = {
            **{
                key: value for key, value in source_metadata.items()
                if key not in {"download_url", "local_path", "sha256", "name", "source"}
            },
            "source": source, "name": path.name, "sha256": digest,
            "size": path.stat().st_size,
        }
        duplicate = digest in hashes_this_run or repository.is_file_registered(
            digest, period_start.isoformat(), period_end.isoformat()
        )
        inventory.append({**item, "duplicate": duplicate})
        if duplicate:
            duplicate_files.append(path.name)
            run_log.append({"level": "WARNING", "message": f"Duplicate file skipped: {path.name}", "sha256": digest})
            continue
        if source not in config["sources"]:
            raise AdapterConfigurationError(f"No mapping configured for source {source!r}.")
        adapter_type = ADAPTER_TYPES.get(source, SourceAdapter)
        adapter = adapter_type(config["sources"][source])
        parsed = adapter.read(path, digest)
        hashes_this_run.add(digest)
        files_processed.add((source, path.name))
        in_period = [
            record for record in parsed
            if record.transaction_date is None or period_start <= record.transaction_date <= period_end
        ]
        outside_period = len(parsed) - len(in_period)
        records.extend(in_period)
        run_log.append({
            "level": "INFO",
            "message": f"Read {len(parsed)} rows from {source}/{path.name}; retained {len(in_period)} in period",
            "outside_period_rows": outside_period,
        })

    if duplicate_files:
        raise ValueError(
            "Duplicate files do not create a run; refusing a partial or empty source population: "
            + ", ".join(duplicate_files)
        )
    if not files_processed:
        raise ValueError("No source files were processed; an empty run was not created.")

    matching_config = config.get("matching", {})
    result = reconcile(
        records=records,
        amount_tolerance=Decimal(str(matching_config.get("amount_tolerance", "0.01"))),
        settlement_window_days=int(matching_config.get("settlement_window_days", 3)),
    )
    controls = calculate_controls(records, result.ledger, run_id=run_id)
    controls["candidate_matches"] = len(result.candidates)
    controls["files_processed"] = len(files_processed)
    if result.candidates:
        run_log.append({"level": "INFO", "message": f"{len(result.candidates)} date-only candidates require human review."})
    repository.save_run(
        run_id, period_start.isoformat(), period_end.isoformat(),
        records, result.ledger, controls, result.candidates, inventory, run_log,
    )
    return {
        "run_id": run_id,
        "status": controls["status"],
        "records": records,
        "ledger": result.ledger,
        "controls": controls,
        "candidates": result.candidates,
        "inventory": inventory,
        "run_log": run_log,
    }
