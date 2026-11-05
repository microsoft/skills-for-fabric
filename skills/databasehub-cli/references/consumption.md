# Database Hub consumption mode

Use this mode for estate discovery and inventory. Read
`private-over-public-api.md` first.

## Contents

- [Workflow](#workflow)
- [Inventory routes](#inventory-routes)
- [Azure SQL hierarchy routes](#azure-sql-hierarchy-routes)
- [Security finding summaries](#security-finding-summaries)
- [Reporting contract](#reporting-contract)

## Workflow

1. Start with `/databases/count` to establish the total and type mix.
2. If the user asks only for totals, report `totalCount` and `countByType` and
   stop.
3. For mixed Estate V2 rows, use `/savedView/resources/list` with an immutable
   `overviewFilters` snapshot. Use `/databases/list` only for its legacy Azure
   SQL database / Arc SQL Server population.
4. Use hierarchy routes only to resolve a named Azure SQL database or to answer
   a subscription/resource-group/server hierarchy question.
5. Keep Fabric SQL catalog entries separate from Azure estate resources.
6. Report pagination completeness and any issue/enhancement fields returned
   with inventory rows.

## Inventory routes

| Method | Relative route | Request | Important response fields |
| --- | --- | --- | --- |
| GET | `/subscriptions` | none | array of `subscriptionId`, `displayName`, `tenantId` |
| GET | `/databases/count` | none | `totalCount`, `countByType` |
| GET | `/databases/warning/count` | none | SQL/Arc-only `warningCount` |
| POST | `/databases/list` | legacy `databaseType?` (`AzureSql` or `ArcSqlServer`), `top` 1-1000, `continuationToken?` | SQL/Arc `databases[]`, `totalCount`, `hasMore`, `continuationToken` |
| POST | `/azuresql/list` | required `resourceType`, `includeHealthData?`, `pageSize?`, `continuationToken?` | `resourceType`, `resources[]`, `totalCount`, `continuationToken` |
| POST | `/postgreSql/list` | `pageSize?`, `continuationToken?` | `resources[]`, `totalCount`, `continuationToken` |
| POST | `/cosmosDb/list` | `pageSize?`, `continuationToken?` | `resources[]`, `totalCount`, `continuationToken` |
| POST | `/savedView/resources/list` | required `overviewFilters`, plus `pageSize?`, `continuationToken?` | mixed `resources[]`, `totalCount`, `continuationToken` |
| POST | `/fabric/list` | `search?`, `pageSize?`, `continuationToken?` | Fabric SQL catalog `value[]`, `continuationToken` |

For `pageSize`-based inventory routes, the default is 1000 and the valid range
is 1-1000. `/databases/list` is the exception: it uses `top` 1-1000 instead of
`pageSize`. Begin smaller when the user wants a summary rather than a full
export.

`/databases/count` and `/databases/list` do not have the same population.
Counts include broader Estate V2 types; the legacy list contains only Azure SQL
databases and Arc SQL Server instances. Never compare their totals as if they
were the same denominator.

### Legacy SQL/Arc inventory body

```json
{
  "top": 100
}
```

Omit `databaseType` for both legacy families, or use only `AzureSql` or
`ArcSqlServer`. Other enum values are unsupported on this route; use the
engine-specific or saved-view routes instead.

### Engine-specific inventory bodies

```json
{
  "pageSize": 100
}
```

PostgreSQL and Cosmos DB use that shape directly. Azure SQL also requires one
canonical ARM resource type:

| Resource | `resourceType` |
| --- | --- |
| Azure SQL databases | `microsoft.sql/servers/databases` |
| logical servers | `microsoft.sql/servers` |
| elastic pools | `microsoft.sql/servers/elasticpools` |
| Arc-enabled SQL Server instances | `microsoft.azurearcdata/sqlserverinstances` |
| SQL Server on Azure VMs | `microsoft.sqlvirtualmachine/sqlvirtualmachines` |
| managed instances | `microsoft.sql/managedinstances` |

Set `includeHealthData: true` only on `/azuresql/list`, and only when its
issue/enhancement flags are required. PostgreSQL and Cosmos inventory return
their supported finding flags without that property. Do not treat inventory
flags as a substitute for the operations health routes.

### Saved-view body

An empty immutable filter snapshot selects the supported mixed Estate V2
resource types:

```json
{
  "pageSize": 100,
  "overviewFilters": {}
}
```

Supported membership filters include `databaseTypes`, `statuses`,
`subscriptionIds`, `resourceGroups`, `locations`, structured `tags`, and
`skuTiers`.

```json
{
  "pageSize": 100,
  "overviewFilters": {
    "databaseTypes": ["AzureSql", "PostgreSql", "Cosmos"],
    "subscriptionIds": ["<subscription-guid>"],
    "tags": [
      {
        "key": "environment",
        "value": "production"
      }
    ]
  }
}
```

Each tag filter requires `key`; omit `value` to match any value for that key.

When the user requests an exact number of pages, issue that many separate POST
requests and stop even if another token remains. Emit a compact result with
`pageCount`, `returnedRowCount`, `totalCount`, and the final
`continuationToken`. For example, two 10-row pages must report
`pageCount: 2` and `returnedRowCount: 20`; do not infer those values only in
the final prose. When the user asks to return the rows, the final answer must
also enumerate every requested row, grouped by the returned `databaseType`.
Include each row's returned `name` and add its server, workspace, resource
group, subscription, or resource ID when names are duplicated. The compact
page aggregate proves completeness but does not replace the requested row
listing.

Request each page once and print it in the same call with its rows labeled, so
you never re-request a page to recover a field:

```powershell
$page | Select-Object totalCount, continuationToken, @{ n = 'resources'; e = {
    , @($_.resources | Select-Object databaseType, name, id, resourceGroupName,
      @{ n = 'subscription'; e = { $_.subscription.name } }) } } |
  ConvertTo-Json -Depth 6
```

`searchFindingKeys` is **not** a standalone finding-membership filter. It is
used only with a non-empty `searchTerm`, and active finding flags are OR'd into
that keyword search. Do not use it to claim that returned rows all have a
specific issue.

For named finding resources:

- performance high/low groups: use SQL or PostgreSQL `usage-details`;
- authentication, auditing, or CMK gaps: use the matching warning route; and
- other security findings: inspect `issues` / `enhancements` on engine-specific
  inventory. On `/azuresql/list`, request them with `includeHealthData: true`;
  PostgreSQL and Cosmos return supported flags without that property. Filter the
  returned rows client-side and state when no dedicated server-side membership
  route exists.

### Fabric SQL catalog body

```json
{
  "search": "",
  "pageSize": 100
}
```

Rows contain `id`, `type`, `catalogEntryType`, `displayName`, `description`, and
workspace hierarchy. This route is **inventory only**; hand off a selected
Fabric SQL database to `sqldb-cli` for T-SQL or item-level diagnostics.

## Azure SQL hierarchy routes

| Method | Relative route | Purpose |
| --- | --- | --- |
| GET | `/subscriptions/{subscriptionId}/resourceGroups` | list resource groups |
| GET | `/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/servers` | list logical servers |
| GET | `/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/servers/{serverName}/databases` | list database names |
| GET | `/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/servers/{serverName}/databases/{databaseName}` | read one Azure SQL database from ARM |

Resolve names by listing and filtering. Never guess a subscription, resource
group, server, resource ID, workspace ID, or item ID.

## Security finding summaries

The overview summary routes currently support only the `security` category:

```text
GET /overviewFindings/security/{issues|suggestions}/summaries
GET /overviewFindings/security/{issues|suggestions}/{MicrosoftSql|PostgreSql|CosmosDb}/summary
```

Use `suggestions` in requests; the response can canonicalize that relevance to
`enhancements`. Important fields are `databaseFamily`, `totalFindingCount`,
`totalAffectedResourceCount`, `postureAffectedResourceCount`,
`affectedResourceCounts`, `targetSummaries`, and `errors`.

## Reporting contract

- Distinguish resource count from finding count: one resource can have multiple
  findings.
- Group by returned `type` or `databaseFamily`; do not infer an engine from a
  resource name.
- Include `totalCount` and whether every continuation token was consumed.
- State which population produced each total. In particular, do not present the
  legacy SQL/Arc list total as the broader `/databases/count` denominator.
- If inventory is empty, state the scope and filters used before concluding
  that no resources exist.
- If a resource name is duplicated, include server, subscription, resource
  group, workspace, or full resource ID as needed to disambiguate it.
