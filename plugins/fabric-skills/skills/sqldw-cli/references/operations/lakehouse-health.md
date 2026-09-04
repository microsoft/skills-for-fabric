<!-- Leaf reference linked directly from sqldw-cli/SKILL.md. -->

# Lakehouse Table File Health

Use this workflow for Lakehouse tables needing attention, small files, deleted rows, and checkpoint/file-layout anomalies.

## Contents

- [Applicability](#applicability)
- [Response contract](#response-contract)
- [Inventory](#inventory)
- [Health procedure](#health-procedure)
- [Interpretation](#interpretation)

## Applicability

This point-in-time workflow applies only to a Lakehouse through its SQL analytics endpoint. Resolve item type before SQL.

For a Warehouse or Mirrored Database, return this under **Diagnosis** and stop:

`Not applicable: table-health metrics are available only for Lakehouse tables through a SQL analytics endpoint.`

Do not substitute Warehouse clustering or SQL optimizer-statistics diagnostics.

## Response contract

Return exactly:

```text
## Diagnosis
## Evidence
## Ruled out
## Recommendations
## Follow-ups
```

## Inventory

```sql
SELECT
    s.name AS schema_name,
    t.name AS table_name,
    QUOTENAME(s.name) + '.' + QUOTENAME(t.name) AS fully_qualified_table_name
FROM sys.tables AS t
INNER JOIN sys.schemas AS s ON t.schema_id = s.schema_id
WHERE t.is_ms_shipped = 0
ORDER BY s.name, t.name;
```

Run the health procedure once for every returned table. An empty inventory is a healthy empty-scope result.

## Health procedure

```sql
EXEC sys.sp_get_table_health_metrics @table_name = 'dbo.FactSales';
```

The caller needs at least `VIEW DEFINITION`. Attach the input table name to each returned row because the procedure does not identify it.

| Code | Meaning | Handling |
|---|---|---|
| `0` | None | Healthy for the procedure's file-layout checks |
| `1` | Invalid file statistics | Investigate Delta metadata; do not trust remaining metrics |
| `2` | Many deleted rows | Quantify deleted-row share; recommend maintenance outside SQL |
| `3` | Many small files | Quantify file count/histogram; recommend maintenance outside SQL |
| `4` | No recent checkpoint | Report versions and route checkpoint maintenance outside SQL |

## Interpretation

- Preserve live `PotentialAnomalyDescription`; do not replace it with a local message.
- The procedure returns only the highest-severity anomaly. Do not infer additional codes.
- Calculate rows per file, bytes per file, and deleted-row percentage with zero guards.
- A failed procedure call is `Not evaluated`, never healthy.
- The SQL analytics endpoint is read-only. Route `OPTIMIZE` or checkpoint maintenance to Spark, Lakehouse maintenance, or pipelines.
- Report the UTC evaluation time, evaluated/unevaluated tables, anomaly counts, and file-level metrics with `sys.sp_get_table_health_metrics` citations.
