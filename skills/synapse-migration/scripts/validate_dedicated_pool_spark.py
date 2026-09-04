"""Parse Dedicated Pool migration artifacts with the installed target Spark parser."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dedicated_pool_runtime import MigrationBlocked, validate_spark_sql_notebook


def validate_artifact(artifact: Path, parse_plan) -> None:
    try:
        content = artifact.read_text(encoding="utf-8")
        if artifact.suffix.casefold() == ".ipynb":
            validate_spark_sql_notebook(json.loads(content), parse_plan)
        elif artifact.suffix.casefold() == ".sql":
            parse_plan(content)
        else:
            raise MigrationBlocked(f"Unsupported parser-gate artifact: {artifact}")
    except MigrationBlocked:
        raise
    except Exception as exception:
        raise MigrationBlocked(f"Parser gate failed for {artifact}: {exception}") from exception


def validate_artifacts(spark, artifacts: list[Path]) -> None:
    primary_error: BaseException | None = None
    try:
        parse_plan = spark._jsparkSession.sessionState().sqlParser().parsePlan
        for artifact in artifacts:
            validate_artifact(artifact, parse_plan)
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated Spark SQL without executing it")
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args()

    try:
        from pyspark.sql import SparkSession
    except ImportError as exception:
        raise MigrationBlocked("PySpark matching the target Fabric runtime must be installed") from exception

    try:
        spark = SparkSession.builder.master("local[1]").appName("dedicated-pool-parser-gate").getOrCreate()
        validate_artifacts(spark, args.artifacts)
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