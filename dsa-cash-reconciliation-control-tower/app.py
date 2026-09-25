from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cash_tower.configuration import validate_configuration
from cash_tower.overrides import record_manual_override
from cash_tower.pipeline import run_reconciliation
from cash_tower.reporting import export_reconciliation_workbook
from cash_tower.repository import SQLiteRepository
from cash_tower.sharepoint import GraphSharePointClient, SharePointSettings
from cash_tower.synthetic import generate_synthetic_files


def _apply_filters(rows: list[dict]) -> list[dict]:
    with st.sidebar:
        st.divider()
        st.subheader("Record filters")
        sources = sorted({row["source"] for row in rows})
        selected_sources = st.multiselect("Processor / source", sources, default=sources)
        payment_types = sorted({row["account_type"] for row in rows if row.get("account_type")})
        selected_types = st.multiselect("Payment type", payment_types, default=payment_types)
        statuses = sorted({row["status"] for row in rows})
        selected_statuses = st.multiselect("Match status", statuses, default=statuses)
        exceptions = sorted({row["exception_type"] for row in rows if row.get("exception_type")})
        selected_exceptions = st.multiselect("Exception type", exceptions, default=exceptions)
        start = st.date_input("Transaction date from", value=None, key="filter_start")
        end = st.date_input("Transaction date to", value=None, key="filter_end")
        batch = st.text_input("Batch", key="filter_batch").strip().casefold()
        transaction = st.text_input("Transaction ID", key="filter_transaction").strip().casefold()
        backend = st.text_input("Backend ID", key="filter_backend").strip().casefold()
        file_name = st.text_input("File", key="filter_file").strip().casefold()
    output = []
    for row in rows:
        if row["source"] not in selected_sources or row["status"] not in selected_statuses:
            continue
        if row.get("account_type") and row["account_type"] not in selected_types:
            continue
        if row.get("exception_type") and row["exception_type"] not in selected_exceptions:
            continue
        parsed_date = date.fromisoformat(row["transaction_date"]) if row.get("transaction_date") else None
        if start and parsed_date and parsed_date < start:
            continue
        if end and parsed_date and parsed_date > end:
            continue
        if batch and batch not in (row.get("batch_number") or "").casefold():
            continue
        if transaction and transaction not in (row.get("transaction_id") or "").casefold():
            continue
        if backend and backend not in (row.get("backend_id") or "").casefold():
            continue
        if file_name and file_name not in row["source_file"].casefold():
            continue
        output.append(row)
    return output


def _show_executive_summary(run: dict | None, controls: dict, rows: list[dict]) -> None:
    st.subheader("Executive Summary")
    if not run:
        return
    statuses = {status: sum(item["status"] == status for item in rows)
                for status in {row["status"] for row in rows}}
    columns = st.columns(5)
    columns[0].metric("Source rows", len(rows))
    columns[1].metric("Fully matched", statuses.get("Fully Matched", 0))
    columns[2].metric("Timing differences", statuses.get("Timing Difference", 0))
    columns[3].metric("Unresolved", sum(
        count for status, count in statuses.items()
        if status not in {"Fully Matched", "Timing Difference", "Reject/Reversal/Refund"}
    ))
    columns[4].metric("Date-only candidates", len(run["candidates"]))
    st.caption(f"Run {run['run_id']} · {controls['status']} · {run['period_start']} to {run['period_end']}")
    st.dataframe(pd.DataFrame(controls.get("sources", [])), use_container_width=True, hide_index=True)


def _show_exception_queue(rows: list[dict], run: dict | None) -> None:
    st.subheader("Exception Queue")
    st.dataframe(pd.DataFrame([row for row in rows if row["status"] != "Fully Matched"]),
                 use_container_width=True, hide_index=True)
    if run and run["candidates"]:
        st.subheader("Candidate matches — human review only")
        st.caption("Date proximity never creates a confirmed match or changes the algorithmic status.")
        st.dataframe(pd.DataFrame(run["candidates"]), use_container_width=True, hide_index=True)


def _show_lineage(rows: list[dict], run: dict | None, repository: SQLiteRepository) -> None:
    st.subheader("Transaction Lineage")
    if not run or not rows:
        st.info("No records match the current filters.")
        return
    groups = {row["reconciliation_id"]: row for row in rows}
    reconciliation_id = st.selectbox("Reconciliation record", list(groups))
    selected = groups[reconciliation_id]
    st.write({
        "Algorithm status": selected["algorithm_status"],
        "Current status": selected.get("override_status") or selected["status"],
        "Match rule": selected["match_rule"],
        "Fields used": selected["fields_used"],
        "Amount variance": selected["amount_variance"],
    })
    for source in ("SnapPay", "BluePay", "BMO", "JDE"):
        st.markdown(f"**{source}**")
        source_rows = selected["lineage"].get(source, [])
        if source_rows:
            st.dataframe(pd.DataFrame(source_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("No source row in this reconciliation group.")
    st.markdown("**Selected raw row values**")
    st.json(selected.get("raw_values", {}))
    st.markdown("**Manual override audit**")
    prior_overrides = [
        item for item in run["overrides"]
        if item["reconciliation_id"] == reconciliation_id
    ]
    if prior_overrides:
        st.dataframe(pd.DataFrame(prior_overrides), use_container_width=True, hide_index=True)
    else:
        st.caption("No manual overrides have been recorded for this group.")
    override_form = st.form("manual_override")
    statuses = [
        "Fully Matched", "Timing Difference", "Missing from BluePay", "Missing from Bank",
        "Missing from GL", "Amount Mismatch", "Reject/Reversal/Refund",
        "Duplicate Identifier", "Unmatched / Research Required",
    ]
    revised = override_form.selectbox("Revised status", statuses)
    reason = override_form.text_input("Reason (required)")
    preparer = override_form.text_input("Preparer (required)")
    approver = override_form.text_input("Approver (optional)")
    supporting_reference = override_form.text_input("Supporting reference (optional)")
    if override_form.form_submit_button("Record manual override"):
        try:
            record_manual_override(
                repository, run["run_id"], reconciliation_id,
                selected["algorithm_status"], revised, reason, preparer,
                approver, supporting_reference,
            )
            st.success("Override recorded separately; algorithmic status is unchanged.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def _show_controls(controls: dict, rows: list[dict]) -> None:
    st.subheader("Control Totals")
    if not controls:
        return
    st.dataframe(pd.DataFrame(controls.get("sources", [])), use_container_width=True, hide_index=True)
    st.metric("Filtered source detail rows", len(rows))
    st.write("Source-to-output bridge:", "PASS" if controls["bridge_passed"] else "CRITICAL")
    for issue in controls.get("bridge_issues", []):
        st.error(issue)


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    st.set_page_config(page_title="DSA Cash Reconciliation Control Tower", layout="wide")
    st.title("DSA Cash Reconciliation Control Tower")
    st.caption("Controlled cash reconciliation · SnapPay → BluePay → BMO Bank → JD Edwards GL")

    database = os.getenv("RECONCILIATION_DB", str(PROJECT_ROOT / "data" / "reconciliation.sqlite"))
    repository = SQLiteRepository(database)
    production_config = PROJECT_ROOT / "config" / "column_mappings.yaml"
    synthetic_config = PROJECT_ROOT / "config" / "synthetic_column_mappings.yaml"
    with st.sidebar:
        st.header("Reconciliation")
        period_start = st.date_input("Reporting period start", value=date(2026, 9, 1), key="period_start")
        period_end = st.date_input("Reporting period end", value=date(2026, 9, 30), key="period_end")
        if st.button("Run synthetic demonstration", use_container_width=True):
            synthetic_files = generate_synthetic_files(PROJECT_ROOT / "data" / "synthetic")
            result = run_reconciliation(
                synthetic_files, synthetic_config, repository, period_start, period_end
            )
            st.session_state["selected_run"] = result["run_id"]
            st.success(f"Synthetic run {result['run_id']} completed with status {result['status']}.")

        if st.button("List and ingest SharePoint files", use_container_width=True):
            try:
                mapping_errors = validate_configuration(production_config)
                if mapping_errors:
                    st.error("Replace the production mapping placeholders before connecting to SharePoint.")
                    for error in mapping_errors:
                        st.write(f"- {error}")
                    st.stop()
                settings = SharePointSettings.from_environment()
                graph = GraphSharePointClient(settings)
                with production_config.open(encoding="utf-8") as config_file:
                    config = yaml.safe_load(config_file)
                files = graph.list_files(
                    config.get("sharepoint", {}).get("source_folders", {}),
                    period_start,
                    period_end,
                )
                downloaded = []
                duplicates = 0
                for metadata in files:
                    source = metadata["source"]
                    destination = PROJECT_ROOT / "data" / "raw" / source
                    downloaded_metadata = graph.download_file(metadata, destination)
                    if repository.is_file_registered(
                        downloaded_metadata["sha256"],
                        period_start.isoformat(),
                        period_end.isoformat(),
                    ):
                        duplicates += 1
                        continue
                    downloaded.append((
                        source, Path(downloaded_metadata["local_path"]), downloaded_metadata
                    ))
                if not downloaded:
                    st.info(f"No new approved files downloaded. Previously ingested duplicates skipped: {duplicates}.")
                elif duplicates:
                    st.error(
                        f"Run not created: {duplicates} already-ingested file(s) were present alongside "
                        "new files. Process a complete, non-duplicate source set to avoid a partial population."
                    )
                else:
                    result = run_reconciliation(
                        downloaded, production_config, repository, period_start, period_end
                    )
                    st.session_state["selected_run"] = result["run_id"]
                    st.success(
                        f"SharePoint run {result['run_id']} status: {result['status']}; "
                        f"files skipped as duplicates: {duplicates}."
                    )
            except (OSError, ValueError, RuntimeError, KeyError, requests.RequestException) as exc:
                st.error(f"SharePoint ingestion failed: {exc}")

    runs = repository.list_runs()
    selected_run_id = st.session_state.get("selected_run")
    current_run = None
    if runs:
        periods = sorted({(run["period_start"], run["period_end"]) for run in runs}, reverse=True)
        selected_period = st.selectbox(
            "Reporting period",
            periods,
            format_func=lambda period: f"{period[0]} to {period[1]}",
        )
        period_runs = [
            run for run in runs
            if (run["period_start"], run["period_end"]) == selected_period
        ]
        run_ids = [run["run_id"] for run in period_runs]
        if selected_run_id not in run_ids:
            selected_run_id = run_ids[0]
        selected_run_id = st.selectbox(
            "Reconciliation run", run_ids,
            index=run_ids.index(selected_run_id),
            format_func=lambda run_id: next(
                f"{item['created_at']} · {item['status']} · {run_id[:8]}"
                for item in period_runs if item["run_id"] == run_id
            ),
        )
        st.session_state["selected_run"] = selected_run_id
        current_run = repository.get_run(selected_run_id)

    pages = [
        "Executive Summary", "Exception Queue", "Transaction Lineage",
        "Control Totals", "Reconciliation Run History", "Configuration Validation",
    ]
    page = st.radio("Page", pages, horizontal=True, label_visibility="collapsed")
    if current_run:
        controls = current_run["controls"]
        override_by_id = {item["reconciliation_id"]: item for item in current_run["overrides"]}
        for row in current_run["ledger"]:
            override = override_by_id.get(row["reconciliation_id"])
            if override:
                row["override_status"] = override["revised_status"]
                row["manual_override_id"] = override["override_id"]
        if controls["status"] == "Critical":
            st.error("CRITICAL: source-to-output completeness bridge failed. This run cannot be marked complete.")
        else:
            st.success("Completeness bridge passed for every source.")
        filtered = _apply_filters(current_run["ledger"])
    else:
        controls, filtered = {}, []
        st.info("No reconciliation runs yet. Use the synthetic demonstration or configure SharePoint.")

    if page == "Executive Summary":
        _show_executive_summary(current_run, controls, filtered)
    elif page == "Exception Queue":
        _show_exception_queue(filtered, current_run)
    elif page == "Transaction Lineage":
        _show_lineage(filtered, current_run, repository)
    elif page == "Control Totals":
        _show_controls(controls, filtered)
    elif page == "Reconciliation Run History":
        st.subheader("Reconciliation Run History")
        st.dataframe(pd.DataFrame(runs), use_container_width=True, hide_index=True)
    elif page == "Configuration Validation":
        st.subheader("Configuration Validation")
        config_choice = st.selectbox(
            "Mapping configuration", ["Production mapping template", "Synthetic demo mapping"]
        )
        config_path = production_config if config_choice.startswith("Production") else synthetic_config
        errors = validate_configuration(config_path)
        if errors:
            st.warning(f"{len(errors)} configuration item(s) need attention.")
            st.dataframe(pd.DataFrame({"issue": errors}), use_container_width=True, hide_index=True)
        else:
            st.success("Configuration contains all required source mappings and no example placeholders.")
        st.code(str(config_path))

    if current_run:
        report_path = PROJECT_ROOT / os.getenv("REPORT_OUTPUT_DIR", "output") / f"reconciliation_{selected_run_id}.xlsx"
        export_reconciliation_workbook(report_path, current_run)
        st.download_button(
            "Download reconciliation Excel workbook",
            data=report_path.read_bytes(),
            file_name=report_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    main()
