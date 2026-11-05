# Database Hub private-over-public API contract

Read this before either mode reference.

## Contents

- [Lifecycle and identity](#lifecycle-and-identity)
- [Required headers and transport](#required-headers-and-transport)
- [Query values](#query-values)
- [Pagination](#pagination)
- [Partial results and grounding](#partial-results-and-grounding)
- [Error handling](#error-handling)
- [Read-only route boundary](#read-only-route-boundary)

## Lifecycle and identity

Database Hub is reached through the normal Fabric Public API host:

```text
https://api.fabric.microsoft.com/v1/databasehub/__private
```

The `__private` segment is an API lifecycle classification, not an instruction
to use a private network or a workload-specific hostname. These routes are not a
generated public SDK contract and can change independently of documented Fabric
REST APIs. Use only the allowlisted read routes in this skill; never discover,
guess, or generalize adjacent routes.

Use a **delegated Entra user token** for
`https://api.fabric.microsoft.com`. Follow the authentication guidance in
`common/COMMON-CLI.md`.
Do not assume service-principal or managed-identity compatibility. If the
current identity lacks a delegated user assertion and the route returns 401 or
403, report that the identity is unsupported by the current Database Hub
contract rather than weakening authentication.

## Required headers and transport

Every call requires:

- `Authorization: Bearer <Fabric token>` — supplied by `az rest`;
- `x-ms-fabric-skill: databasehub-cli`; and
- `Content-Type: application/json` for POST requests.

GET example:

```powershell
$dbhBase = "https://api.fabric.microsoft.com/v1/databasehub/__private"
az rest --method get `
  --resource "https://api.fabric.microsoft.com" `
  --url "$dbhBase/databases/count" `
  --headers "x-ms-fabric-skill=databasehub-cli"
```

For POST, use a UTF-8 JSON file with a unique name per request, so parallel
calls never overwrite or delete each other's body. Inline JSON is unreliable
through PowerShell's native-command quoting and can reach the service with
stripped property quotes.

```powershell
$bodyPath = Join-Path $env:TEMP (
  "databasehub-request-{0}.json" -f [guid]::NewGuid().ToString("N"))
$body = @{ top = 100 } | ConvertTo-Json -Depth 20
[IO.File]::WriteAllText($bodyPath, $body, [Text.UTF8Encoding]::new($false))
try {
  az rest --method post `
    --resource "https://api.fabric.microsoft.com" `
    --url "$dbhBase/databases/list" `
    --headers "x-ms-fabric-skill=databasehub-cli" "Content-Type=application/json" `
    --body "@$bodyPath"
} finally {
  Remove-Item -LiteralPath $bodyPath -ErrorAction SilentlyContinue
}
```

Never print, persist, or pass the bearer token as a command-line argument.

## Query values

- Timestamps are ISO 8601 UTC values.
- URL-encode continuation tokens, resource names, and resource IDs when they
  appear in a URL.
- Health windows must be 31 days or less.
- Supported granularities are `PT1M`, `PT5M`, `PT15M`, `PT30M`, `PT1H`, and
  `P1D`, except Cosmos DB accepts only `PT1H` or `P1D`.
- Supported aggregation values are `average`, `maximum`, and `minimum`.
- Treat continuation tokens as opaque. Reuse them verbatim for the same route,
  request body, filter snapshot, and ordering.

On Windows, prefer `Invoke-RestMethod` for GET URLs containing multiple `&`
query parameters, using the in-memory Fabric token/header pattern from
`common/COMMON-CLI.md`. The `az.cmd` shim can split an expanded query string
into separate commands. Treat messages such as `'<parameter>' is not
recognized` as a failed request, fix the transport, and rerun it before using
the response.

## Pagination

The route families use three related response shapes:

| Family | Rows | Paging signal |
| --- | --- | --- |
| `/databases/list` | `databases[]` | continue while `hasMore` and `continuationToken` are present |
| specialized inventory and saved views | `resources[]` | continue while `continuationToken` is present |
| Fabric catalog | `value[]` | continue while `continuationToken` is present |
| posture warnings | `items[]` | continue while `hasMore` and `continuationToken` are present |
| Cosmos health | metric arrays for one account page | continue while `continuationToken` is present |

Do not combine pages produced from different filter bodies. For a count-only
question, a summary/count response is sufficient; do not page tens of thousands
of resources unnecessarily.

## Partial results and grounding

HTTP 200 does not guarantee full estate coverage.

- SQL and PostgreSQL health can return `errors[]`.
- PostgreSQL can return `coverage` with `totalResources`,
  `resourcesWithData`, `partitionsFailed`, `metricsFailed`,
  `permissionDeniedResources`, and `isComplete`.
- Cosmos DB returns `totalAccounts`, `processedAccounts`,
  `resourcesWithData`, `continuationToken`, and `errors`.
- Finding summaries can carry per-family `errors`.

Always ground the final answer in returned fields. Include the query
`startTime`, `endTime`, and `granularity`; identify missing engines or resources;
and label results **partial** when errors, permissions, coverage, or paging leave
the population incomplete.

For summary questions, project the typed fields needed for the answer instead
of printing full `series`, `targetSummaries`, or resource pages. Preserve raw
responses only when the user requests export or detailed drill-down. Compact
tool output prevents truncation while retaining the counts, coverage, and error
fields used in the final answer. Emit projected rows with `ConvertTo-Json`, not
`Format-Table`; tables truncate long values such as resource IDs and silently
drop columns such as `reason`.

## Error handling

| Result | Action |
| --- | --- |
| 400 | Fix the route value, query range, enum, page size, or body. Do not retry unchanged input. |
| 401 | Recheck the active Entra user, tenant, Fabric audience, and delegated-user authentication. |
| 403 | Report the denied permission or unavailable feature; do not bypass with another host or token audience. |
| 404 | Treat the route as unavailable in that environment. Do not guess a replacement route. |
| 429 | Respect `Retry-After`, then retry the same read with bounded backoff. |
| 5xx / timeout | Retry boundedly only when the operation is idempotent; retain and report any partial page already returned. |

## Read-only route boundary

Allowed families are the inventory, hierarchy, health, finding-summary, and
posture routes listed in the mode references.

Never call:

- `/deploy/database`;
- PostgreSQL or Cosmos create, deploy, name-availability, or operation-status
  routes;
- `/azureSql/performanceMonitoring` or any enable/disable flow;
- Database Agent, System Agent, or issue-mutation routes; or
- any future telemetry schema/query route not explicitly added to this skill.

POST does not automatically mean write: list, saved-view, and filtered-health
routes use POST for read-only request bodies. Judge safety by the allowlisted
route, not only by the HTTP method.
