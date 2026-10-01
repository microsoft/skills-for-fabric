"""Parse Dedicated Pool migration artifacts with the installed target Spark parser."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from dedicated_pool_runtime import MigrationBlocked, validate_spark_sql_notebook


def _record_namespaces(record: Mapping) -> set[str]:
    namespaces: set[str] = set()
    source_stable_id = record.get("sourceStableId")
    if isinstance(source_stable_id, str) and source_stable_id.strip():
        namespaces.add(source_stable_id.replace(".", "_"))
    source_schema = record.get("sourceSchema")
    source_name = record.get("sourceName")
    if (
        isinstance(source_name, str)
        and source_name.strip()
        and isinstance(source_schema, str)
        and source_schema.strip()
    ):
        namespaces.add(f"{source_schema}_{source_name}")
    return namespaces


def _is_procedure_record(record: Mapping, source_name: str) -> bool:
    source_type = record.get("sourceType", record.get("objectType"))
    if source_type is None:
        return True
    if not isinstance(source_type, str):
        raise MigrationBlocked(
            f"Manifest source type must be a string for {source_name}"
        )
    return "procedure" in source_type.casefold()


def _validation_rule_matches(kind: str, rule: object, required: bool) -> bool:
    if not isinstance(rule, str):
        return False
    prefix = "Required" if required else "Optional"
    expected = {
        "date": f"{prefix} DATE",
        "timestamp": f"{prefix} TIMESTAMP",
        "boolean": f"{prefix} BOOLEAN",
        "string": f"{prefix} non-blank STRING" if required else "Optional STRING",
        "nullable-string": "Nullable STRING",
    }.get(kind)
    if expected is not None:
        return rule == expected
    if kind == "integer":
        return re.fullmatch(
            rf"{prefix} (?:TINYINT|SMALLINT|INT|BIGINT)", rule
        ) is not None
    if kind.startswith("decimal:"):
        precision, scale = kind.split(":")[1:]
        return rule == f"{prefix} DECIMAL({precision},{scale})"
    return False


def validate_manifest_parameter_mappings(
    manifest_path: Path,
    nullable_parameters: tuple[str, ...] = (),
    expected_procedure_namespaces: tuple[str, ...] | None = None,
    declared_parameters: tuple[str, ...] | None = None,
    parameter_validations: Mapping[str, str] | None = None,
) -> tuple[set[tuple[str, str]], dict[str, object]]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exception:
        raise MigrationBlocked(
            f"Manifest validation failed for {manifest_path}: {exception}"
        ) from exception
    if not isinstance(manifest, Mapping):
        raise MigrationBlocked(f"Manifest root must be an object: {manifest_path}")
    objects = manifest.get("objects")
    if not isinstance(objects, list):
        raise MigrationBlocked(f"Manifest objects must be an array: {manifest_path}")
    expected_namespace_set = set(expected_procedure_namespaces or ())
    namespace_record_counts = Counter()
    scoped_mappings: list[tuple[str, set[str], dict]] = []
    scoped_records: list[tuple[str, list[dict]]] = []
    for record in objects:
        if not isinstance(record, dict):
            raise MigrationBlocked(f"Manifest object must be an object: {manifest_path}")
        source_name = record.get("sourceName") or record.get("sourceStableId") or "<unknown>"
        if not _is_procedure_record(record, str(source_name)):
            continue
        mappings = record.get("parameterMappings")
        if not isinstance(mappings, list):
            raise MigrationBlocked(
                f"Manifest parameterMappings must be an array for {source_name}"
            )
        record_namespaces = _record_namespaces(record)
        matched_record_namespaces = record_namespaces.intersection(expected_namespace_set)
        record_is_scoped = (
            expected_procedure_namespaces is None or bool(matched_record_namespaces)
        )
        namespace_record_counts.update(matched_record_namespaces)
        for mapping in mappings:
            if not isinstance(mapping, dict):
                raise MigrationBlocked(
                    f"Manifest parameter mapping must be an object for {source_name}"
                )
            if "parameterName" in mapping:
                raise MigrationBlocked(
                    f"Manifest parameter mapping for {source_name} uses parameterName; "
                    "use sourceParameter"
                )
            source_parameter = mapping.get("sourceParameter")
            if not isinstance(source_parameter, str) or not source_parameter.strip():
                raise MigrationBlocked(
                    f"Manifest parameter mapping for {source_name} requires sourceParameter"
                )
            if record_is_scoped:
                scoped_mappings.append((str(source_name), record_namespaces, mapping))
        if record_is_scoped:
            scoped_records.append((str(source_name), mappings))

    missing_namespaces = sorted(
        namespace
        for namespace in expected_namespace_set
        if namespace_record_counts[namespace] == 0
    )
    if missing_namespaces:
        raise MigrationBlocked(
            "Manifest contains no procedure mapping for expected namespace(s): "
            + ", ".join(missing_namespaces)
        )
    ambiguous_namespaces = sorted(
        namespace
        for namespace in expected_namespace_set
        if namespace_record_counts[namespace] != 1
    )
    if ambiguous_namespaces:
        raise MigrationBlocked(
            "Manifest contains multiple procedure mappings for expected namespace(s): "
            + ", ".join(ambiguous_namespaces)
        )

    for source_name, mappings in scoped_records:
        mapped_parameters = [mapping["sourceParameter"] for mapping in mappings]
        duplicates = sorted(
            parameter
            for parameter, count in Counter(mapped_parameters).items()
            if count > 1
        )
        if duplicates:
            raise MigrationBlocked(
                f"Manifest parameterMappings for {source_name} contain duplicate "
                f"sourceParameter values: {', '.join(duplicates)}"
            )
    if declared_parameters is not None:
        declared_parameter_set = set(declared_parameters)
        mapped_parameter_set = {
            mapping["sourceParameter"] for _, _, mapping in scoped_mappings
        }
        missing = sorted(declared_parameter_set - mapped_parameter_set)
        extra = sorted(mapped_parameter_set - declared_parameter_set)
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing: {', '.join(missing)}")
            if extra:
                details.append(f"extra: {', '.join(extra)}")
            raise MigrationBlocked(
                "Manifest parameterMappings do not exactly match declared notebook "
                f"parameters ({'; '.join(details)})"
            )
    if parameter_validations is not None:
        nullable_parameter_set = set(nullable_parameters)
        expected_parameter_keys: set[tuple[str, str]] = set()
        expected_parameter_defaults: dict[str, object] = {}
        mapped_parameter_set = {
            mapping["sourceParameter"] for _, _, mapping in scoped_mappings
        }
        validation_parameter_set = set(parameter_validations)
        missing_validations = sorted(
            mapped_parameter_set - validation_parameter_set
        )
        extra_validations = sorted(
            validation_parameter_set - mapped_parameter_set
        )
        if missing_validations or extra_validations:
            details = []
            if missing_validations:
                details.append(f"missing: {', '.join(missing_validations)}")
            if extra_validations:
                details.append(f"extra: {', '.join(extra_validations)}")
            raise MigrationBlocked(
                "Parameter validation contracts do not exactly match scoped manifest "
                f"parameters ({'; '.join(details)})"
            )
        for source_name, record_namespaces, mapping in scoped_mappings:
            parameter_name = mapping["sourceParameter"]
            validation = parameter_validations.get(parameter_name)
            if validation is None:
                raise MigrationBlocked(
                    f"Manifest parameter mapping for {source_name}.{parameter_name} "
                    "has no parameter validation contract"
                )
            required = mapping.get("required")
            source_default_present = mapping.get("sourceDefaultPresent")
            if not isinstance(required, bool) or not isinstance(
                source_default_present, bool
            ):
                raise MigrationBlocked(
                    f"Manifest parameter mapping for {source_name}.{parameter_name} "
                    "requires boolean required and sourceDefaultPresent fields"
                )
            if (
                "sourceDefault" not in mapping
                or "defaultValue" not in mapping
                or type(mapping["sourceDefault"]) is not type(mapping["defaultValue"])
                or mapping["sourceDefault"] != mapping["defaultValue"]
            ):
                raise MigrationBlocked(
                    f"Manifest parameter mapping for {source_name}.{parameter_name} "
                    "must preserve the same sourceDefault and defaultValue type and value"
                )
            if required and (
                source_default_present
                or mapping["sourceDefault"] is not None
                or mapping.get("missingValueBehavior") != "RejectBeforeMutation"
            ):
                raise MigrationBlocked(
                    f"Manifest required parameter contract is inconsistent for "
                    f"{source_name}.{parameter_name}"
                )
            if not required and not source_default_present:
                raise MigrationBlocked(
                    f"Manifest optional parameter contract has no source default for "
                    f"{source_name}.{parameter_name}"
                )
            if not required:
                expected_missing_value_behavior = (
                    "UseSourceNullDefault"
                    if mapping["sourceDefault"] is None
                    else "UseSourceDefault"
                )
                if (
                    mapping.get("missingValueBehavior")
                    != expected_missing_value_behavior
                ):
                    raise MigrationBlocked(
                        f"Manifest missingValueBehavior does not match the source default "
                        f"for {source_name}.{parameter_name}"
                    )
            if mapping.get("approvedCaller") != "FabricPipelineOrParentNotebook":
                raise MigrationBlocked(
                    f"Manifest approvedCaller is not valid for "
                    f"{source_name}.{parameter_name}"
                )
            if mapping.get("disposition") != "AutomaticSubstitutionApproved":
                raise MigrationBlocked(
                    f"Manifest disposition does not approve automatic substitution for "
                    f"{source_name}.{parameter_name}"
                )
            if not _validation_rule_matches(
                validation, mapping.get("validationRule"), required
            ):
                raise MigrationBlocked(
                    f"Manifest validationRule does not match {validation} for "
                    f"{source_name}.{parameter_name}"
                )
            if (
                "targetParameter" not in mapping
                or mapping["targetParameter"] != parameter_name
            ):
                raise MigrationBlocked(
                    f"Manifest targetParameter must be present and match "
                    f"sourceParameter for "
                    f"{source_name}.{parameter_name}"
                )
            approved_namespaces = record_namespaces.intersection(
                expected_namespace_set
            )
            configuration_key = mapping.get("configurationKey")
            configuration_match = (
                re.fullmatch(
                    r"spark\.synapseMigration\.([A-Za-z_][A-Za-z0-9_]*)\."
                    r"([A-Za-z_][A-Za-z0-9_]*)",
                    configuration_key,
                )
                if isinstance(configuration_key, str)
                else None
            )
            if (
                configuration_match is None
                or configuration_match.group(2) != parameter_name
                or (
                    approved_namespaces
                    and configuration_match.group(1) not in approved_namespaces
                )
            ):
                raise MigrationBlocked(
                    f"Manifest configurationKey does not match the approved namespace "
                    f"for {source_name}.{parameter_name}"
                )
            parameter_key = (configuration_match.group(1), parameter_name)
            if parameter_key in expected_parameter_keys:
                raise MigrationBlocked(
                    f"Manifest contains duplicate configurationKey for "
                    f"{source_name}.{parameter_name}"
                )
            expected_parameter_keys.add(parameter_key)
            source_default = mapping["sourceDefault"]
            if (
                parameter_name in expected_parameter_defaults
                and (
                    type(expected_parameter_defaults[parameter_name])
                    is not type(source_default)
                    or expected_parameter_defaults[parameter_name] != source_default
                )
            ):
                raise MigrationBlocked(
                    f"Manifest contains conflicting defaults for parameter "
                    f"{parameter_name}"
                )
            expected_parameter_defaults[parameter_name] = source_default
            if validation in {"string", "nullable-string"}:
                expected_allow_list = (
                    "^[A-Za-z0-9 _.-]+$" if required else "^[A-Za-z0-9 _.-]*$"
                )
                if mapping.get("stringAllowList") != expected_allow_list:
                    raise MigrationBlocked(
                        f"Manifest stringAllowList does not match the approved pattern "
                        f"for {source_name}.{parameter_name}"
                    )
                if mapping.get("validationBoundary") != "CallerBeforeNotebook":
                    raise MigrationBlocked(
                        f"Manifest validationBoundary is not valid for "
                        f"{source_name}.{parameter_name}"
                    )
                if (
                    mapping.get("outOfAllowListDisposition")
                    != "ManualReviewRequired"
                ):
                    raise MigrationBlocked(
                        f"Manifest outOfAllowListDisposition is not valid for "
                        f"{source_name}.{parameter_name}"
                    )
            if validation == "nullable-string" and parameter_name not in nullable_parameter_set:
                raise MigrationBlocked(
                    f"Manifest nullable validation is not enabled for "
                    f"{source_name}.{parameter_name}"
                )
    else:
        expected_parameter_keys = set()
        expected_parameter_defaults = {}
    for parameter_name in nullable_parameters:
        matches = [
            (source_name, mapping)
            for source_name, _, mapping in scoped_mappings
            if mapping.get("sourceParameter") == parameter_name
        ]
        if not matches:
            raise MigrationBlocked(
                f"Nullable parameter {parameter_name} has no matching manifest mapping"
            )
        for source_name, mapping in matches:
            if (
                mapping.get("required") is not False
                or mapping.get("sourceDefaultPresent") is not True
                or mapping.get("sourceDefault") is not None
                or mapping.get("missingValueBehavior") != "UseSourceNullDefault"
                or mapping.get("nullTransportToken")
                != "::SYNAPSE_MIGRATION_NULL::"
                or mapping.get("nullTokenCollisionCheck")
                != "ProvenOutsideSourceDomain"
            ):
                raise MigrationBlocked(
                    f"Nullable parameter {parameter_name} conflicts with the manifest "
                    f"contract for {source_name}"
                )
    print(f"MANIFEST VALID {manifest_path}")
    return expected_parameter_keys, expected_parameter_defaults


def validate_artifact(
    artifact: Path,
    parse_plan,
    expected_procedure_namespace: str | tuple[str, ...] | None = None,
    nullable_parameters: tuple[str, ...] = (),
    parameter_validations: Mapping[str, str] | None = None,
    expected_parameter_keys: set[tuple[str, str]] | None = None,
    expected_parameter_defaults: Mapping[str, object] | None = None,
) -> None:
    try:
        content = artifact.read_text(encoding="utf-8")
        if artifact.suffix.casefold() == ".ipynb":
            validate_spark_sql_notebook(
                json.loads(content),
                parse_plan,
                expected_procedure_namespace,
                nullable_parameters,
                parameter_validations,
                require_parameter_validations=True,
                expected_parameter_keys=expected_parameter_keys,
                expected_parameter_defaults=expected_parameter_defaults,
            )
        elif artifact.suffix.casefold() == ".sql":
            parse_plan(content)
        else:
            raise MigrationBlocked(f"Unsupported parser-gate artifact: {artifact}")
    except MigrationBlocked:
        raise
    except Exception as exception:
        raise MigrationBlocked(f"Parser gate failed for {artifact}: {exception}") from exception


def validate_artifacts(
    spark,
    artifacts: list[Path],
    expected_procedure_namespace: str | tuple[str, ...] | None = None,
    nullable_parameters: tuple[str, ...] = (),
    parameter_validations: Mapping[str, str] | None = None,
    expected_parameter_keys: set[tuple[str, str]] | None = None,
    expected_parameter_defaults: Mapping[str, object] | None = None,
) -> None:
    primary_error: BaseException | None = None
    try:
        parse_plan = spark._jsparkSession.sessionState().sqlParser().parsePlan
        for artifact in artifacts:
            validate_artifact(
                artifact,
                parse_plan,
                expected_procedure_namespace,
                nullable_parameters,
                parameter_validations or {},
                expected_parameter_keys,
                expected_parameter_defaults,
            )
            print(f"PARSED {artifact}")
    except BaseException as exception:
        primary_error = exception
        raise
    finally:
        try:
            spark.stop()
        except Exception:
            if primary_error is None:
                raise


def validate_notebook_structures(
    artifacts: list[Path],
    expected_procedure_namespace: str | tuple[str, ...] | None = None,
    nullable_parameters: tuple[str, ...] = (),
    parameter_validations: Mapping[str, str] | None = None,
    expected_parameter_keys: set[tuple[str, str]] | None = None,
    expected_parameter_defaults: Mapping[str, object] | None = None,
) -> None:
    for artifact in artifacts:
        if artifact.suffix.casefold() != ".ipynb":
            raise MigrationBlocked(f"Structure-only validation requires a notebook artifact: {artifact}")
        validate_artifact(
            artifact,
            lambda _sql: None,
            expected_procedure_namespace,
            nullable_parameters,
            parameter_validations or {},
            expected_parameter_keys,
            expected_parameter_defaults,
        )
        print(f"STRUCTURE VALID {artifact}")


def parse_parameter_validation(value: str) -> tuple[str, str]:
    parameter_name, separator, validation = value.partition("=")
    if (
        not separator
        or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", parameter_name) is None
        or re.fullmatch(
            r"(?:integer|date|timestamp|boolean|string|nullable-string|"
            r"decimal:[1-9][0-9]?:(?:0|[1-9][0-9]?))",
            validation,
        )
        is None
    ):
        raise argparse.ArgumentTypeError(
            "expected Name=Kind where Kind is integer, date, timestamp, boolean, "
            "string, nullable-string, or decimal:PRECISION:SCALE"
        )
    if validation.startswith("decimal:"):
        precision, scale = (int(part) for part in validation.split(":")[1:])
        if precision > 38:
            raise argparse.ArgumentTypeError(
                "decimal precision must be between 1 and 38"
            )
        if scale > precision:
            raise argparse.ArgumentTypeError("scale must be between 0 and precision")
    return parameter_name, validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated Spark SQL without executing it")
    parser.add_argument(
        "--structure-only",
        action="store_true",
        help="Validate notebook JSON and Python bridge structure without starting Spark",
    )
    parser.add_argument(
        "--expected-procedure-namespace",
        action="append",
        help="Approve a procedure namespace for parameter bridge keys; repeat for consolidated notebooks",
    )
    parser.add_argument(
        "--nullable-parameter",
        action="append",
        default=[],
        help="Allow this explicitly nullable parameter to normalize Python None for SQL transport",
    )
    parser.add_argument(
        "--parameter-validation",
        action="append",
        default=[],
        type=parse_parameter_validation,
        metavar="NAME=KIND",
        help="Bind a parameter to integer, decimal:PRECISION:SCALE, date, timestamp, boolean, string, or nullable-string; repeat for every parameter",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Validate migration-manifest.json parameter mapping field names",
    )
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args()
    expected_procedure_namespaces = (
        tuple(args.expected_procedure_namespace)
        if args.expected_procedure_namespace
        else None
    )
    parameter_validations = dict(args.parameter_validation)
    if len(parameter_validations) != len(args.parameter_validation):
        parser.error("--parameter-validation names must be unique")
    if args.parameter_validation and args.manifest is None:
        parser.error("--manifest is required with --parameter-validation")
    if args.parameter_validation and expected_procedure_namespaces is None:
        parser.error(
            "--expected-procedure-namespace is required with --parameter-validation"
        )
    if args.nullable_parameter and not args.parameter_validation:
        parser.error(
            "--parameter-validation is required with --nullable-parameter"
        )
    expected_parameter_keys: set[tuple[str, str]] | None = None
    expected_parameter_defaults: Mapping[str, object] | None = None
    if args.manifest is not None:
        expected_parameter_keys, expected_parameter_defaults = (
            validate_manifest_parameter_mappings(
                args.manifest,
                tuple(args.nullable_parameter),
                expected_procedure_namespaces,
                tuple(parameter_validations) if args.parameter_validation else None,
                parameter_validations if args.parameter_validation else None,
            )
        )

    if args.structure_only:
        validate_notebook_structures(
            args.artifacts,
            expected_procedure_namespaces,
            tuple(args.nullable_parameter),
            parameter_validations,
            expected_parameter_keys,
            expected_parameter_defaults,
        )
        return 0

    try:
        from pyspark.sql import SparkSession
    except ImportError as exception:
        raise MigrationBlocked("PySpark matching the target Fabric runtime must be installed") from exception

    try:
        spark = SparkSession.builder.master("local[1]").appName("dedicated-pool-parser-gate").getOrCreate()
        validate_artifacts(
            spark,
            args.artifacts,
            expected_procedure_namespaces,
            tuple(args.nullable_parameter),
            parameter_validations,
            expected_parameter_keys,
            expected_parameter_defaults,
        )
    except MigrationBlocked:
        raise
    except Exception as exception:
        raise MigrationBlocked(f"Spark parser gate failed: {exception}") from exception
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MigrationBlocked as exception:
        print(f"BLOCKED: {exception}", file=sys.stderr)
        raise SystemExit(1) from None