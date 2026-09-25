from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from cash_tower.adapters import AdapterConfigurationError, SourceAdapter
from cash_tower.configuration import validate_configuration
from cash_tower.controls import calculate_controls
from cash_tower.matching import reconcile
from cash_tower.models import SourceRecord
from cash_tower.normalization import normalize_amount, normalize_identifier
from cash_tower.overrides import record_manual_override
from cash_tower.pipeline import run_reconciliation
from cash_tower.reporting import SHEET_NAMES, export_reconciliation_workbook
from cash_tower.repository import SQLiteRepository
from cash_tower.synthetic import generate_synthetic_files

PROJECT = __import__("pathlib").Path(__file__).resolve().parents[1]
SYNTHETIC_CONFIG = PROJECT / "config" / "synthetic_column_mappings.yaml"
PERIOD_START = date(2026, 9, 1)
PERIOD_END = date(2026, 9, 30)


@pytest.fixture
def synthetic_run(tmp_path):
    files = generate_synthetic_files(tmp_path / "source")
    repository = SQLiteRepository(tmp_path / "ledger.sqlite")
    result = run_reconciliation(
        files, SYNTHETIC_CONFIG, repository, PERIOD_START, PERIOD_END
    )
    return result, files, repository


def _status_for(run, transaction_id):
    row = next(row for row in run["ledger"] if row.transaction_id == transaction_id)
    return row.status


def test_synthetic_end_to_end_bridge_is_zero(synthetic_run):
    run, _, _ = synthetic_run
    assert run["status"] == "Complete"
    assert run["controls"]["bridge_passed"]
    assert all(row["bridge_row_difference"] == 0 for row in run["controls"]["sources"])
    assert all(row["bridge_dollar_difference"] == Decimal("0") for row in run["controls"]["sources"])
    assert len(run["ledger"]) == sum(row["input_rows"] for row in run["controls"]["sources"])


def test_clean_one_to_one_match_has_full_lineage(synthetic_run):
    run, _, _ = synthetic_run
    row = next(row for row in run["ledger"] if row.transaction_id == "S-CLEAN")
    assert row.status == "Fully Matched"
    assert "SnapPay-BluePay exact transaction ID" in row.match_rule
    assert set(row.lineage) == {"SnapPay", "BluePay", "BMO", "JDE"}
    assert all(len(row.lineage[source]) == 1 for source in row.lineage)
    assert all(item["source_file"] and item["source_worksheet"] and item["source_row"]
               for lineage in row.lineage.values() for item in lineage)


def test_many_to_one_bank_settlement_reconciles_grouped_totals(synthetic_run):
    run, _, _ = synthetic_run
    rows = [row for row in run["ledger"] if row.transaction_id in {"S-GROUP-1", "S-GROUP-2"}]
    assert rows and all(row.status == "Fully Matched" for row in rows)
    assert "BluePay-BMO exact backend/customer reference" in rows[0].match_rule
    bank_amounts = [Decimal(item["amount"]) for item in rows[0].lineage["BMO"]]
    assert sum(bank_amounts) == Decimal("100.00")


def test_later_bank_settlement_is_timing_not_lost_match(synthetic_run):
    run, _, _ = synthetic_run
    row = next(row for row in run["ledger"] if row.transaction_id == "S-LATE")
    assert row.status == "Timing Difference"
    assert row.lineage["BMO"][0]["settlement_date"] == "2026-09-03"


def test_bluepay_backend_id_matches_bmo_customer_reference_exactly():
    blue = SourceRecord(
        source="BluePay", transaction_id="BP-1", backend_id="REF-1",
        amount=Decimal("25.00"), transaction_date=date(2026, 9, 1),
    )
    bank = SourceRecord(
        source="BMO", customer_reference="REF-1",
        amount=Decimal("25.00"), transaction_date=date(2026, 9, 1),
    )
    result = reconcile([blue, bank])
    assert result.ledger[0].reconciliation_id == result.ledger[1].reconciliation_id
    assert "backend_id" in result.ledger[0].fields_used
    assert "customer_reference" in result.ledger[0].fields_used
    assert "BluePay-BMO exact backend/customer reference" in result.ledger[0].match_rule


def test_missing_bank_and_missing_gl_classifications(synthetic_run):
    run, _, _ = synthetic_run
    assert _status_for(run, "S-NOBANK") == "Missing from Bank"
    assert _status_for(run, "S-NOGL") == "Missing from GL"
    assert _status_for(run, "S-MISSBLUE") == "Missing from BluePay"


def test_duplicate_identifier_and_amount_mismatch(synthetic_run):
    run, _, _ = synthetic_run
    duplicate_rows = [row for row in run["ledger"] if row.transaction_id == "S-DUP"]
    assert len(duplicate_rows) >= 2
    assert all(row.status == "Duplicate Identifier" for row in duplicate_rows)
    mismatch = next(row for row in run["ledger"] if row.transaction_id == "S-MISMATCH")
    assert mismatch.status == "Amount Mismatch"
    assert mismatch.amount_variance == Decimal("-1.00")


def test_identifiers_and_signed_decimal_normalization_are_safe():
    assert normalize_identifier(" 0000123 ") == "0000123"
    assert normalize_identifier(123.0) == "123"
    assert normalize_amount("(1,234.50)") == Decimal("-1234.50")
    assert normalize_amount("not-an-amount") is None


@pytest.mark.parametrize("transaction_id", ["S-REJECT", "S-REVERSAL", "S-REFUND"])
def test_reject_reversal_and_refund_are_separately_preserved(transaction_id, synthetic_run):
    run, _, _ = synthetic_run
    row = next(row for row in run["ledger"] if row.transaction_id == transaction_id)
    assert row.status == "Reject/Reversal/Refund"
    assert row.raw_values["transaction_status"] in {"REJECT", "REVERSAL", "REFUND"}


def test_blank_identifier_malformed_date_and_amount_are_rejected_to_research(synthetic_run):
    run, _, _ = synthetic_run
    bad_records = [row for row in run["ledger"] if row.quality_issues]
    assert any("Blank required field: transaction_id" in row.quality_issues for row in bad_records)
    assert any("Malformed date: transaction_date" in row.quality_issues for row in bad_records)
    assert any("Malformed amount: amount" in row.quality_issues for row in bad_records)
    assert all(row.status == "Unmatched / Research Required" for row in bad_records)


def test_date_only_candidate_never_becomes_a_confirmed_match():
    left = SourceRecord(
        source="SnapPay", transaction_id="S-ONE", amount=Decimal("10"),
        transaction_date=date(2026, 9, 1), source_file="left.csv",
    )
    right = SourceRecord(
        source="BluePay", transaction_id="B-DIFFERENT", backend_id="REF-DIFFERENT",
        amount=Decimal("10"), transaction_date=date(2026, 9, 2), source_file="right.csv",
    )
    result = reconcile([left, right], settlement_window_days=3)
    assert result.candidates
    assert all(candidate["candidate_only"] for candidate in result.candidates)
    assert {row.status for row in result.ledger} == {"Missing from BluePay", "Missing from Bank"}


def test_duplicate_file_hash_is_registered_once(tmp_path):
    repository = SQLiteRepository(tmp_path / "ledger.sqlite")
    file_metadata = {"sha256": "synthetic-hash", "name": "same.csv", "source": "SnapPay"}
    assert repository.register_file(file_metadata)
    assert not repository.register_file(file_metadata)
    assert repository.is_file_registered("synthetic-hash")


def test_duplicate_source_files_do_not_create_an_empty_successful_run(tmp_path):
    files = generate_synthetic_files(tmp_path / "source")
    repository = SQLiteRepository(tmp_path / "ledger.sqlite")
    first = run_reconciliation(files, SYNTHETIC_CONFIG, repository, PERIOD_START, PERIOD_END)
    assert first["status"] == "Complete"
    with pytest.raises(ValueError, match="(?i)duplicate files do not create"):
        run_reconciliation(files, SYNTHETIC_CONFIG, repository, PERIOD_START, PERIOD_END)
    assert len(repository.list_runs()) == 1
    subsequent_period = run_reconciliation(
        files, SYNTHETIC_CONFIG, repository, date(2026, 10, 1), date(2026, 10, 31)
    )
    assert subsequent_period["run_id"] != first["run_id"]


def test_missing_ledger_row_fails_the_completeness_bridge(synthetic_run):
    run, _, _ = synthetic_run
    controls = calculate_controls(run["records"], run["ledger"][:-1], "broken-run")
    assert controls["status"] == "Critical"
    assert not controls["bridge_passed"]
    assert controls["bridge_issues"]


def test_manual_override_is_audited_without_rewriting_algorithm_result(synthetic_run):
    run, _, repository = synthetic_run
    ledger_row = next(row for row in run["ledger"] if row.status == "Missing from GL")
    algorithm_status = ledger_row.algorithm_status
    override = record_manual_override(
        repository, run["run_id"], ledger_row.reconciliation_id, algorithm_status,
        "Fully Matched", "Approved using synthetic evidence", "synthetic-preparer",
        "synthetic-approver", "SYNTH-REF-001",
    )
    persisted = repository.get_run(run["run_id"])
    stored_row = next(row for row in persisted["ledger"]
                      if row["reconciliation_id"] == ledger_row.reconciliation_id)
    assert stored_row["algorithm_status"] == algorithm_status
    assert persisted["overrides"][0]["revised_status"] == "Fully Matched"
    assert persisted["overrides"][0]["approver"] == "synthetic-approver"
    assert persisted["overrides"][0]["override_id"] == override.override_id


def test_override_requires_auditable_fields_and_correct_prior_status(synthetic_run):
    run, _, repository = synthetic_run
    row = run["ledger"][0]
    with pytest.raises(ValueError, match="prior_status"):
        record_manual_override(repository, run["run_id"], row.reconciliation_id,
                               "incorrect", "Fully Matched", "reason", "preparer")
    with pytest.raises(ValueError, match="required"):
        record_manual_override(repository, run["run_id"], row.reconciliation_id,
                               row.algorithm_status, "Fully Matched", "", "preparer")


def test_adapter_fails_clearly_when_required_columns_are_missing(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame([{"wrong_header": "value"}]).to_csv(path, index=False)
    adapter = SourceAdapter("SnapPay", {
        "required": ["transaction_id"],
        "columns": {"transaction_id": ["transaction_ref"]},
    })
    with pytest.raises(AdapterConfigurationError, match="required canonical columns"):
        adapter.read(path)


def test_configuration_validation_distinguishes_template_from_synthetic():
    assert validate_configuration(PROJECT / "config" / "column_mappings.yaml")
    assert validate_configuration(SYNTHETIC_CONFIG) == []


def test_export_contains_required_sheets_and_detail_counts(synthetic_run, tmp_path):
    run, _, repository = synthetic_run
    persisted = repository.get_run(run["run_id"])
    output = export_reconciliation_workbook(tmp_path / "reconciliation.xlsx", persisted)
    workbook = pd.ExcelFile(output)
    assert workbook.sheet_names == SHEET_NAMES
    ledger = pd.read_excel(output, sheet_name="Reconciliation Ledger")
    summary = pd.read_excel(output, sheet_name="Executive Summary")
    metric = summary.loc[summary["metric"] == "Source Rows", "value"].iloc[0]
    assert int(metric) == len(ledger)
    controls = pd.read_excel(output, sheet_name="Control Totals")
    assert (controls["bridge_row_difference"] == 0).all()
    assert (controls["bridge_dollar_difference"] == 0).all()


def test_reporting_period_excludes_out_of_period_rows_and_logs_them(tmp_path):
    files = generate_synthetic_files(tmp_path / "source")
    repository = SQLiteRepository(tmp_path / "ledger.sqlite")
    result = run_reconciliation(
        files, SYNTHETIC_CONFIG, repository, date(2026, 9, 1), date(2026, 9, 1)
    )
    assert result["status"] == "Complete"
    assert any(entry.get("outside_period_rows", 0) for entry in result["run_log"])


def test_sharepoint_metadata_is_captured_without_preauthorized_url(tmp_path):
    files = generate_synthetic_files(tmp_path / "source")
    source, path = files[0]
    files[0] = (source, path, {
        "modified_at": "2026-09-01T00:00:00Z",
        "e_tag": "fixture-etag",
        "size": 123,
    })
    repository = SQLiteRepository(tmp_path / "ledger.sqlite")
    run = run_reconciliation(
        files, SYNTHETIC_CONFIG, repository, PERIOD_START, PERIOD_END
    )
    inventory = next(item for item in run["inventory"] if item["name"] == path.name)
    assert inventory["modified_at"] == "2026-09-01T00:00:00Z"
    assert inventory["e_tag"] == "fixture-etag"
    assert "download_url" not in inventory
    assert "local_path" not in inventory


def test_streamlit_app_renders_without_startup_exceptions(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("RECONCILIATION_DB", str(tmp_path / "streamlit.sqlite"))
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path / "reports"))
    app = AppTest.from_file(str(PROJECT / "app.py"), default_timeout=20).run()
    assert not app.exception
