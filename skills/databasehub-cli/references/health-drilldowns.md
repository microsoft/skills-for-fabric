# Database Hub health drill-downs and filtered snapshots

Use this reference for named high/low SQL or PostgreSQL resources, critical or
monitored SQL resources, per-resource SQL metric history, and filtered
saved-view comparisons. Apply the authentication, transport, paging, and
read-only rules from the private-over-public API contract linked directly from
`SKILL.md`.

## Contents

- [Microsoft SQL drill-down routes](#microsoft-sql-drill-down-routes)
- [PostgreSQL drill-down routes](#postgresql-drill-down-routes)
- [Filtered health](#filtered-health)

## Microsoft SQL drill-down routes

| Method | Relative route | Key request fields | Use |
| --- | --- | --- | --- |
| GET | `/health/v2/usage-details` | `MetricType`, `UsageLevel`, time range, `Granularity`, `DatabaseType?`, `AggregationType` | named high/low usage resources |
| GET | `/health/critical` | time range, `Granularity`, `DatabaseType?`, `AggregationType` | resources classified as critical |
| GET | `/health/monitored` | time range, repeated `DatabaseTypes?`, `Top?`, `ContinuationToken?`, `CheckPermission?` | SQL/Arc resources sending telemetry |
| GET | `/health/database/metrics/{encodedResourceId}` | `MetricType`, time range, `Granularity`, optional `ResourceName` | one SQL/Arc resource time series |

For SQL health, omit `DatabaseType` to cover Azure SQL and Arc SQL Server, or
use `AzureSql` / `ArcSqlServer` to narrow. Do not pass PostgreSQL to this route;
use the PostgreSQL route family. Do not label these health metrics as covering
Azure SQL Managed Instance, SQL Server on Azure VM, logical servers, or elastic
pools; those resource types can appear in inventory/security findings but are
outside this health route's default metric population.

Valid `MetricType` values for drill-down are `Cpu`, `Storage`, and `Memory`.
Valid `UsageLevel` values are `High` and `Low`.

Print usage-details responses whole with `ConvertTo-Json -Depth 10`; do not
project them. They are small, and `metricType`, `usageLevel`, `startTime`,
`endTime`, `totalCount`, and `databases` are the evidence for the answer.

> **Windows transport gate:** `/health/v2/usage-details` uses several `&`
> query parameters. On Windows, call this route with `Invoke-RestMethod` and an
> in-memory Fabric bearer token/header map. Do not pass an expanded query-rich
> URL through the `az.cmd` shim. If output contains messages such as
> `'UsageLevel' is not recognized`, the request is failed even when a
> default-looking JSON response follows; discard it and rerun with
> `Invoke-RestMethod`.

URL-encode the full resource ID for the per-resource route. For Arc machines
with multiple instances, preserve the returned `ResourceName` when supplied.

## PostgreSQL drill-down routes

| Method | Relative route | Key request fields | Use |
| --- | --- | --- | --- |
| GET | `/postgreSql/health/v2/usage-details` | `MetricType`, `UsageLevel`, time range, `Granularity`, `AggregationType` | named high/low PostgreSQL servers |

The PostgreSQL route has no `DatabaseType` parameter. Do not copy a SQL request
body or query string onto it.

## Filtered health

Use filtered POST routes when the user supplies a saved-view/filter scope.
Estate-wide Cosmos health is the explicit exception: use its filtered POST with
`overviewFilters: {}` and `pageSize: 300` even when the user supplied no filter.

- `/health/v2/filtered-summary`
- `/health/v2/filtered-usage-details`
- `/postgreSql/health/v2/summary`
- `/postgreSql/health/v2/usage-details`
- `/cosmosDb/health/summary`

Filtered bodies require the same immutable `overviewFilters` snapshot used by
inventory, `pageSize` 1-300, and a matching `continuationToken`.

When comparing a plain SQL summary, filtered usage details, and a filtered SQL
summary, pin the same `StartTime`, `EndTime`, `Granularity`, and
`AggregationType` on all three. If `overviewFilters.databaseTypes` is
`AzureSql`, also set `DatabaseType=AzureSql` on the plain summary. Send the same
`overviewFilters` snapshot to both filtered POSTs and apply the requested row
bound with `pageSize` on `/health/v2/filtered-usage-details` (for example,
`pageSize: 20`). GET `/health/v2/usage-details` has no `Top` parameter; if you
use that unfiltered route elsewhere, any presentation limit is a disclosed
client-side truncation. Never compare an unfiltered SQL/Arc denominator with an
Azure-SQL-only filtered population.

When the three requests use separate shell tool calls, compute the window once
and copy the exact UTC `StartTime` and `EndTime` strings into every later call.
Do not run `Get-Date` again in each shell call; even a few seconds of drift means
the responses are not the same snapshot. Paste the literal strings into each
command; do not save the window to a file and reload it with `ConvertFrom-Json`,
which turns ISO strings into `DateTime` values and changes their precision.

Prefer three separate shell tool calls and emit a typed result for each. If two
or more requests share one shell call, label every included output section with
exactly `SQL SUMMARY`, `USAGE DETAILS`, or `FILTERED SUMMARY`, echo the pinned
window, and preserve response `startTime`, `endTime`, and `granularity` so each
result remains correlated. When projecting a summary, keep `totalDatabases`,
`usageCounts`, and `performanceIssueSummary`.

A usage-details response with `totalCount: 0` and `databases: []` is a valid
empty population. Report zero named resources together with the summary high
count; do not invent percentages or widen the filter to find rows.

- SQL/PostgreSQL/Cosmos filtered **summary** bodies can include `category`
  (`security` or `performance`) and `relevance` (`issues` or `suggestions`).
- PostgreSQL filtered **usage-details** can also include `category` and
  `relevance`.
- SQL `/health/v2/filtered-usage-details` does **not** define those two fields;
  send only metric, usage level, time, aggregation, filters, paging, and token.

Use the file-based POST pattern from the private-over-public API contract.
