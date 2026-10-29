from __future__ import annotations

import hashlib
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cash_tower.source_profile import (
    FILENAME_RULES,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    build_profile_report,
    distinct_worksheet_structures,
    missing_required_fields,
    profile_source_files,
    propose_mappings,
    save_unapproved_mapping_draft,
    snappay_header_consistency,
)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        result = yaml.safe_load(stream)
    return result if isinstance(result, dict) else {}


def _approval_is_current(config_path: Path, approval_path: Path) -> bool:
    if not config_path.is_file() or not approval_path.is_file():
        return False
    try:
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(config_path.read_bytes()).hexdigest()
        return approval.get("approved") is True and approval.get("config_sha256") == digest
    except (OSError, json.JSONDecodeError):
        return False


def _save_approved_mappings(
    config: dict[str, Any], config_path: Path, approval_path: Path, approver: str
) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
    config_path.write_text(rendered, encoding="utf-8")
    digest = hashlib.sha256(config_path.read_bytes()).hexdigest()
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text(
        json.dumps({
            "approved": True,
            "approved_by": approver.strip(),
            "config_sha256": digest,
        }, indent=2),
        encoding="utf-8",
    )


def _profile_tables(profiles: list[dict[str, Any]], mappings: dict[str, Any] | None) -> None:
    file_rows = []
    worksheet_rows = []
    for profile in profiles:
        missing = missing_required_fields(profile, mappings)
        file_rows.append({
            "Filename": profile["filename"],
            "Inferred source type": profile["source_type"],
            "Inferred adapter": profile["inferred_source"],
            "Worksheets": ", ".join(item["worksheet"] for item in profile["worksheets"]),
            "Data rows": sum(item["row_count"] for item in profile["worksheets"]),
            "Missing required fields": ", ".join(missing) if missing else "None",
            "Profile error": profile["profile_error"] or "",
            "Local path": profile["path"],
        })
        for worksheet in profile["worksheets"]:
            worksheet_rows.append({
                "Filename": profile["filename"],
                "Inferred source type": profile["source_type"],
                "Worksheet": worksheet["worksheet"],
                "Data rows": worksheet["row_count"],
                "Header row": worksheet["header_row"],
                "Headers": worksheet["headers"],
                "Missing required fields": ", ".join(missing) if missing else "None",
            })
    st.dataframe(pd.DataFrame(file_rows), width="stretch", hide_index=True)
    st.subheader("Worksheet names, row counts, and headers")
    st.dataframe(pd.DataFrame(worksheet_rows), width="stretch", hide_index=True)
    structures = distinct_worksheet_structures(profiles)
    st.subheader("Distinct worksheet structures")
    st.dataframe(pd.DataFrame([{
        "Source type": item["source_type"],
        "Worksheet": item["worksheet"],
        "Header row": item["header_row"],
        "Files with this structure": item["file_count"],
        "Data rows (profiled sheets)": item["row_count"],
        "Observed headers": item["headers"],
    } for item in structures]), width="stretch", hide_index=True)
    st.subheader("Identifier storage / leading-zero risk")
    risk_rows = []
    for profile in profiles:
        for worksheet in profile["worksheets"]:
            for risk in worksheet.get("identifier_risks", []):
                risk_rows.append({
                    "Source type": profile["source_type"],
                    "Filename": profile["filename"],
                    "Worksheet": worksheet["worksheet"],
                    "Header": risk["header"],
                    "Numeric cells": risk["numeric_cells"],
                    "Zero-padded number formats": risk["zero_padded_format_cells"],
                    "Text cells beginning with zero": risk["text_leading_zero_cells"],
                    "Numeric storage risk": risk["numeric_storage_risk"],
                    "Leading-zero text observed": risk["leading_zero_text_observed"],
                    "Review note": (
                        "Numeric identifiers may have lost leading zeroes; confirm from source specification."
                        if risk["numeric_storage_risk"] else
                        "Text values with leading zeroes are preserved; keep identifiers as text."
                        if risk["leading_zero_text_observed"] else
                        "No numeric storage or leading-zero text was detected in this identifier column."
                    ),
                })
    if risk_rows:
        st.dataframe(pd.DataFrame(risk_rows), width="stretch", hide_index=True)
    else:
        st.info("No numeric or leading-zero identifier storage risks were detected in the profiled sheets.")
    st.subheader("SnapPay daily-file consistency")
    consistency = snappay_header_consistency(profiles)
    if consistency:
        st.dataframe(pd.DataFrame([{
            "Worksheet": item["worksheet"],
            "Files": item["files"],
            "Distinct structures": item["distinct_structures"],
            "Observed header rows": item["header_rows"],
            "Headers consistent": item["headers_consistent"],
            "Header placement consistent": item["placement_consistent"],
        } for item in consistency]), width="stretch", hide_index=True)
        for item in consistency:
            if not item["placement_consistent"] or not item["headers_consistent"]:
                st.warning(
                    f"SnapPay worksheet {item['worksheet']!r} varies across daily files. "
                    "Review its per-file header row and structure before approving mappings."
                )
                st.dataframe(pd.DataFrame([
                    {"Header row": row_number, "Files": filenames}
                    for row_number, filenames in item["files_by_header_row"].items()
                ]), width="stretch", hide_index=True)
    else:
        st.info("No SnapPay daily files were detected.")


def _mapping_proposal_review(profiles: list[dict[str, Any]]) -> None:
    proposals = propose_mappings(profiles)
    st.subheader("Proposed mappings - all unapproved drafts")
    st.caption(
        "Header-based proposals are not approvals. Edit the observed header if needed, then save "
        "a separate draft; this does not change the active configuration or enable reconciliation."
    )
    if not proposals:
        st.info("No mapping candidates can be generated until source files have been profiled.")
        return
    columns = [
        "source_type", "canonical_field", "observed_header", "worksheet",
        "confidence", "reason", "header_row", "profiled_file_count", "approved",
    ]
    proposal_frame = pd.DataFrame(proposals, columns=columns)
    edited = st.data_editor(
        proposal_frame,
        width="stretch",
        hide_index=True,
        disabled=[
            "source_type", "canonical_field", "worksheet", "confidence",
            "reason", "header_row", "profiled_file_count", "approved",
        ],
        column_config={
            "source_type": "Source type",
            "canonical_field": "Canonical field",
            "observed_header": "Observed header (editable draft)",
            "worksheet": "Worksheet",
            "confidence": "Confidence",
            "reason": "Reason / required review",
            "header_row": "Header row",
            "profiled_file_count": "Files with structure",
            "approved": "Approved",
        },
    )
    invalid = []
    for row in edited.to_dict(orient="records"):
        if row["observed_header"] == "<No exact observed header>":
            continue
        available = {
            header
            for profile in profiles
            if profile["source_type"] == row["source_type"]
            for worksheet in profile["worksheets"]
            if worksheet["worksheet"] == row["worksheet"]
            for header in worksheet["headers"]
        }
        if row["observed_header"] not in available:
            invalid.append(
                f"{row['source_type']} / {row['worksheet']}: "
                f"{row['observed_header']!r} is not an observed header."
            )
    if invalid:
        for message in dict.fromkeys(invalid):
            st.error(message)
    if st.button(
        "Save proposed mappings as an unapproved draft",
        disabled=bool(invalid),
        key="save_unapproved_mapping_draft",
    ):
        draft_path = PROJECT_ROOT / "data" / "proposed_mapping_drafts.yaml"
        save_unapproved_mapping_draft(edited.to_dict(orient="records"), draft_path)
        st.success(
            "Draft saved under ignored local data/. It is explicitly unapproved, separate from "
            "the active configuration, and cannot be used to run reconciliation."
        )
    st.warning(
        "RC BLUEPAY GENERAL is structurally distinct from G.L. 1.1070. Keep it unassigned and "
        "treat it as a separate adapter/subtype draft until the source owner confirms provenance, "
        "ledger selection, and amount sign rules. Do not map it to JDE solely because its fields "
        "look like a general-ledger extract."
    )


def _build_mapping_form(
    profiles: list[dict[str, Any]], template: dict[str, Any], approved: dict[str, Any] | None
) -> dict[str, Any] | None:
    prior = approved or {}
    prior_local = prior.get("local_ingestion", {}).get("file_types", {})
    assignments: dict[str, str] = {}
    selected_sheets: dict[str, list[str]] = {}
    selected_columns: dict[str, dict[str, str]] = {}
    mapping_errors: list[str] = []

    form = st.form("approved_column_mapping_form")
    form.subheader("Confirm filename types and source-adapter assignments")
    form.caption("These source groupings are filename-based suggestions. Edit them if your files use a different system.")
    for index, (source_type, inferred_source) in enumerate(FILENAME_RULES):
        option_key = source_type + "*.xlsx"
        default_value = prior_local.get(option_key, {}).get("source", inferred_source)
        sources = ["Unassigned", "SnapPay", "BluePay", "BMO", "JDE"]
        default_index = sources.index(default_value) if default_value in sources else 0
        assignments[source_type] = form.selectbox(
            f"{source_type}*.xlsx → source adapter",
            sources,
            index=default_index,
            key=f"source_assignment_{index}",
        )

    configured_sources = deepcopy(template.get("sources", {}))
    for source in ("SnapPay", "BluePay", "BMO", "JDE"):
        source_profiles = [
            profile for profile in profiles
            if assignments.get(profile["source_type"]) == source
        ]
        form.markdown(f"#### {source} worksheet and column mapping")
        if not source_profiles:
            mapping_errors.append(f"{source}: no detected filename type is assigned to this adapter.")
            form.warning("No detected files are assigned to this source adapter.")
            continue
        observed_sheets = sorted({
            worksheet["worksheet"]
            for profile in source_profiles for worksheet in profile["worksheets"]
        })
        saved_source = prior.get("sources", {}).get(source, {})
        previous_sheets = saved_source.get("worksheets", [])
        selected_sheets[source] = form.multiselect(
            f"{source} worksheet(s)",
            observed_sheets,
            default=[name for name in previous_sheets if name in observed_sheets],
            key=f"worksheets_{source}",
        )
        available_headers = sorted({
            header
            for profile in source_profiles
            for worksheet in profile["worksheets"]
            if worksheet["worksheet"] in selected_sheets[source]
            for header in worksheet["headers"]
        })
        existing_columns = saved_source.get("columns", {})
        selected_columns[source] = {}
        for canonical in OPTIONAL_FIELDS:
            required = (
                canonical in REQUIRED_FIELDS[source]
                or canonical in saved_source.get("required_any", [])
            )
            choices = ["<Not mapped>"] + available_headers
            existing = existing_columns.get(canonical, [])
            existing_header = existing[0] if isinstance(existing, list) and existing else existing
            default_index = choices.index(existing_header) if existing_header in choices else 0
            selected = form.selectbox(
                f"{source}: {canonical}{' (required)' if required else ''}",
                choices,
                index=default_index,
                key=f"column_{source}_{canonical}",
            )
            if selected != "<Not mapped>":
                selected_columns[source][canonical] = selected
        for profile in source_profiles:
            if not any(
                worksheet["worksheet"] in selected_sheets[source]
                for worksheet in profile["worksheets"]
            ):
                mapping_errors.append(
                    f"{profile['filename']}: select at least one of this workbook's observed worksheets."
                )
            for worksheet in profile["worksheets"]:
                if worksheet["worksheet"] not in selected_sheets[source]:
                    continue
                missing_headers = [
                    field for field in REQUIRED_FIELDS[source]
                    if selected_columns[source].get(field) not in worksheet["headers"]
                ]
                if missing_headers:
                    mapping_errors.append(
                        f"{profile['filename']} / {worksheet['worksheet']}: "
                        f"required headers are not mapped or absent: {missing_headers}."
                    )
        required_any = configured_sources.get(source, {}).get("required_any", [])
        if required_any and not any(selected_columns[source].get(field) for field in required_any):
            mapping_errors.append(f"{source}: map at least one of {required_any}.")
        for profile in source_profiles:
            for worksheet in profile["worksheets"]:
                if worksheet["worksheet"] not in selected_sheets[source]:
                    continue
                if required_any and not any(
                    selected_columns[source].get(field) in worksheet["headers"]
                    for field in required_any
                ):
                    mapping_errors.append(
                        f"{profile['filename']} / {worksheet['worksheet']}: "
                        f"map one observed reference field from {required_any}."
                    )

    approver = form.text_input("Mapping approver / preparer (required)", key="mapping_approver").strip()
    submitted = form.form_submit_button("Save and approve mappings")
    if not submitted:
        return None
    if not approver:
        mapping_errors.append("Enter the mapping approver/preparer before approval.")
    if not profiles:
        mapping_errors.append("Profile the local source files before approving mappings.")
    if any(profile["profile_error"] for profile in profiles):
        mapping_errors.append("Resolve workbook profile errors before approving mappings.")
    if "Unassigned" in assignments.values():
        mapping_errors.append("Assign all five filename types to a source adapter or explicitly map each one.")
    detected_types = {profile["source_type"] for profile in profiles}
    missing_types = [prefix for prefix, _ in FILENAME_RULES if prefix not in detected_types]
    if missing_types:
        mapping_errors.append("Profile representative workbooks for all filename types: " + ", ".join(missing_types))

    result = deepcopy(template)
    result["sources"] = {}
    for source in ("SnapPay", "BluePay", "BMO", "JDE"):
        source_template = deepcopy(template.get("sources", {}).get(source, {}))
        source_template["worksheets"] = selected_sheets.get(source, [])
        source_template["columns"] = {
            field: [header] for field, header in selected_columns.get(source, {}).items()
        }
        result["sources"][source] = source_template
    result["local_ingestion"] = {
        "reporting_period": "2026-09",
        "file_types": {
            source_type + "*.xlsx": {
                "source_type": source_type,
                "source": assignments[source_type],
            }
            for source_type, _ in FILENAME_RULES
        },
    }
    mapping_errors.extend(validate_configuration_data(result))
    if mapping_errors:
        for error in dict.fromkeys(mapping_errors):
            st.error(error)
        return None

    approval_path = PROJECT_ROOT / "data" / "mapping_approval.json"
    config_path = PROJECT_ROOT / "data" / "approved_column_mappings.yaml"
    _save_approved_mappings(result, config_path, approval_path, approver)
    st.success(
        "Mappings saved and approved locally. No reconciliation was run. "
        "The approval applies only to the exact saved mapping file."
    )
    st.rerun()


def validate_configuration_data(config: dict[str, Any]) -> list[str]:
    sources = config.get("sources", {})
    issues: list[str] = []
    for source in ("SnapPay", "BluePay", "BMO", "JDE"):
        source_config = sources.get(source, {})
        worksheets = source_config.get("worksheets", [])
        if not worksheets:
            issues.append(f"{source}: select at least one observed worksheet.")
        columns = source_config.get("columns", {})
        required_missing = [
            field for field in REQUIRED_FIELDS[source]
            if not columns.get(field)
        ]
        if required_missing:
            issues.append(f"{source}: map required fields {required_missing}.")
        required_any = source_config.get("required_any", [])
        if required_any and not any(columns.get(field) for field in required_any):
            issues.append(f"{source}: map at least one of {required_any}.")
    issues.extend(validate_configuration_document(config))
    return issues


def validate_configuration_document(config: dict[str, Any]) -> list[str]:
    """Validate an in-memory mapping document without writing it to disk."""
    errors: list[str] = []
    for source, source_config in config.get("sources", {}).items():
        if not source_config.get("worksheets"):
            errors.append(f"{source}: configure at least one worksheet.")
        if not source_config.get("required"):
            errors.append(f"{source}: configure required canonical columns.")
        columns = source_config.get("columns", {})
        missing = [field for field in source_config.get("required", []) if not columns.get(field)]
        if missing:
            errors.append(f"{source}: required fields missing column mapping: {missing}")
        for field, candidates in columns.items():
            if not isinstance(candidates, list) or not candidates:
                errors.append(f"{source}: {field} must map to one or more exact source headers.")
    matching = config.get("matching", {})
    try:
        if float(matching.get("amount_tolerance", -1)) < 0:
            errors.append("matching.amount_tolerance must be zero or greater.")
    except (TypeError, ValueError):
        errors.append("matching.amount_tolerance must be numeric.")
    try:
        if int(matching.get("settlement_window_days", -1)) < 0:
            errors.append("matching.settlement_window_days must be a non-negative integer.")
    except (TypeError, ValueError):
        errors.append("matching.settlement_window_days must be a non-negative integer.")
    return errors


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    st.set_page_config(page_title="DSA Cash Reconciliation Control Tower", layout="wide")
    st.title("DSA Cash Reconciliation Control Tower")
    st.caption("September 2026 pilot · source profiling and mapping approval only")
    st.warning(
        "Pilot safeguard: reconciliation is disabled here. No production reconciliation will run "
        "until mappings have been reviewed and approved."
    )

    config_path = PROJECT_ROOT / "config" / "column_mappings.yaml"
    approved_config_path = PROJECT_ROOT / "data" / "approved_column_mappings.yaml"
    approval_path = PROJECT_ROOT / "data" / "mapping_approval.json"
    approved = (
        _load_yaml(approved_config_path)
        if _approval_is_current(approved_config_path, approval_path)
        else None
    )
    root_default = os.getenv("LOCAL_SHAREPOINT_ROOT", "").strip()
    if not root_default:
        root_default = str(PROJECT_ROOT / "data" / "raw")

    with st.sidebar:
        st.header("Source intake")
        mode = st.selectbox(
            "Ingestion mode",
            ["Local Synced SharePoint Folder", "Microsoft Graph (optional future mode)"],
            index=0,
        )
        if mode.startswith("Microsoft Graph"):
            st.info("Graph remains an optional connector; this September pilot uses the locally synchronized folder.")
        local_root = st.text_input(
            "Local synchronized SharePoint root folder",
            value=root_default,
            help="Paste the local SharePoint sync-folder path. This app only reads files.",
        ).strip()
        profile_clicked = st.button("Profile September 2026 source files", width="stretch")

    profile_page, validation_page = st.tabs(["Source Profile", "Configuration Validation"])

    if profile_clicked:
        try:
            profiles = profile_source_files(local_root)
            st.session_state["source_profiles"] = profiles
            st.session_state["profile_root"] = str(Path(local_root).expanduser().resolve())
            st.session_state["profile_error"] = None
        except (OSError, ValueError) as exc:
            st.session_state["source_profiles"] = []
            st.session_state["profile_root"] = local_root
            st.session_state["profile_error"] = str(exc)

    profiles = st.session_state.get("source_profiles", [])
    if st.session_state.get("profile_root") != str(Path(local_root).expanduser().resolve()):
        profiles = []

    with profile_page:
        st.subheader("Detected files")
        st.caption(
            "Only recursively discovered .xlsx files whose names start with the five configured "
            "September source prefixes are profiled. The app does not validate transaction dates."
        )
        if st.session_state.get("profile_error"):
            st.error(st.session_state["profile_error"])
        if not profiles:
            st.info("Choose the synchronized SharePoint root folder and run source profiling.")
        else:
            _profile_tables(profiles, approved)
            if not profiles:
                st.warning("No matching source workbooks were found.")
            st.download_button(
                "Download source-profile report (Excel)",
                data=build_profile_report(profiles, approved),
                file_name="source_profile_september_2026.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Metadata only: filenames, worksheet names, row counts, headers, and local paths.",
            )
            file_types = {profile["source_type"] for profile in profiles}
            missing_types = [prefix for prefix, _ in FILENAME_RULES if prefix not in file_types]
            if missing_types:
                st.warning("No matching workbook detected for: " + ", ".join(missing_types))

    with validation_page:
        st.subheader("Configuration Validation")
        if approved is None:
            st.info("No current approved local mapping exists. Review the profile and explicitly approve mappings below.")
        else:
            st.success(
                "A mapping approval exists for the current local mapping file. "
                "Re-editing and saving mappings will replace this local approval."
            )
            st.dataframe(pd.DataFrame([
                {"Source": source, "Worksheets": ", ".join(config.get("worksheets", [])),
                 "Mapped columns": ", ".join(config.get("columns", {}).keys())}
                for source, config in approved.get("sources", {}).items()
            ]), width="stretch", hide_index=True)
        if not profiles:
            st.warning("Profile files first. No actual source workbook headers are available to map yet.")
        else:
            template = _load_yaml(config_path)
            saved = approved or template
            _build_mapping_form(profiles, template, saved)
        st.caption(
            "Mappings and approval metadata, when explicitly saved, remain under ignored local data/. "
            "No production reconciliation is exposed in this pilot UI."
        )


if __name__ == "__main__":
    main()
