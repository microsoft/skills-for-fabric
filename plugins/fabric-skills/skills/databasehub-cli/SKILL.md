---
name: databasehub-cli
description: "Analyzes Database Hub inventory, health, and security posture through Entra-authenticated Fabric APIs. Use for estate counts; SQL/PostgreSQL CPU, storage, and memory; Cosmos DB availability/RU; authentication/auditing/CMK warnings; and Fabric SQL inventory. Fabric SQL tuning routes to sqldb-cli; Warehouse/Lakehouse/Mirrored Database SQL to sqldw-cli. Triggers: data estate performance, database estate health, database security posture."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: databasehub-cli` (`az rest`: `--headers "x-ms-fabric-skill=databasehub-cli"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. Database Hub estate routes are tenant-scoped and usually need neither a workspace nor an item ID. Apply notes 1-2 only when resolving a Fabric SQL catalog item or handing off to an item-specific skill.

# Database Hub CLI

Read-only analysis of the database estate exposed through Database Hub. This
skill executes live API calls; it does not answer estate questions from generic
best practices or from files in the current directory.

## Prerequisite knowledge

- [Private-over-public API contract](references/private-over-public-api.md) —
  required authentication, transport, pagination, partial-result, error, and
  route-safety rules.
- [Health drill-downs and filtered snapshots](references/health-drilldowns.md)
  — required for named SQL/PostgreSQL resources, per-resource SQL metrics, and
  filtered health comparisons.
- [Fabric authentication and CLI patterns](../../common/COMMON-CLI.md)
- [Fabric REST API concepts](../../common/COMMON-CORE.md)
- [Databases in Fabric documentation](https://learn.microsoft.com/en-us/fabric/database/)

## Select one mode

| Mode | Use when the request asks for | Read next |
| --- | --- | --- |
| `consumption` | estate counts, subscriptions, resource hierarchy, mixed or engine-specific inventory, saved-view membership, or Fabric SQL catalog entries | [references/consumption.md](references/consumption.md) |
| `operations` | cross-engine performance, CPU/storage/memory, Cosmos DB availability/RU use, critical or monitored resources, issues/suggestions, or authentication/auditing/CMK posture | [references/operations.md](references/operations.md) |

For a request spanning both modes, establish inventory scope first, then run
operations against that scope. Read each reference before issuing its calls.

## Scope and routing boundaries

| Request | Route to |
| --- | --- |
| Cross-engine estate inventory, health, findings, or security posture | `databasehub-cli` |
| Query Store, DMVs, blocking, plans, indexes, T-SQL, or tuning for one Fabric SQL Database | `sqldb-cli` |
| Warehouse, Lakehouse SQL endpoint, or Mirrored Database SQL queries and `queryinsights` | `sqldw-cli` |
| OneLake domains, labels, workspace/capacity governance, descriptions, endorsement, or tags | `onelake-catalog-cli` |
| Fabric workspace item search by name, description, workspace, or type | `search-consumption-cli` |
| Eventhouse or KQL Database queries | `eventhouse-cli` |
| Azure Monitor mirrored-catalog onboarding and business-impact correlation | `azmon-mirroredcatalogs-operations-cli` |

Fabric SQL support here is **catalog inventory only**. Do not claim Database Hub
health or posture coverage for Fabric SQL items. Do not substitute a
single-database diagnostic skill for a cross-engine estate request.

## Execution contract

1. Confirm the active Entra identity and requested scope. Portal-provided
   subscriptions, resource filters, or time range are query hints, never
   authorization.
2. Before the first Database Hub call, read
   [references/private-over-public-api.md](references/private-over-public-api.md)
   and the selected mode reference. For named-resource or filtered health
   drill-downs, read [references/health-drilldowns.md](references/health-drilldowns.md)
   in addition to `operations.md`, not instead of it.
3. Run the documented live calls through `https://api.fabric.microsoft.com`.
4. Follow every continuation token needed for the requested scope.
5. Report timeframe, aggregation, engine coverage, pagination completeness,
   `coverage`, and sanitized `errors`.
6. For prompts containing "all", "across", or "estate", complete every required
   summary/posture call in the selected workflow before answering. Attempt
   independent required calls even when another route fails; collect each
   route's error instead of short-circuiting the workflow. Only a page that
   depends on a failed prior page/token may be skipped. Do not defer required
   calls as an optional follow-up.
7. If a route or permission is unavailable, state the exact missing coverage;
   never invent data, switch to a workload host, or query ADX directly.

## Must / Prefer / Avoid

### MUST

- Remain read-only. Decline create, deploy, enable, disable, update, delete, or
  remediation requests and route them to the owning product flow or skill.
- Use a delegated Entra user token for the Fabric API and include
  `x-ms-fabric-skill: databasehub-cli` on every request.
- Emit SQL and PostgreSQL health summaries only through the compact
  `Select-Object` projection in `operations.md`; never print raw summaries
  with their `series` arrays. A populated estate's raw summaries exceed the
  tool-output limit, and answering from partial file reads misattributes
  metrics.
- For general cross-engine health/performance that includes Cosmos
  availability or RU, query Microsoft SQL, PostgreSQL, and Cosmos DB
  separately; preserve their different metric contracts in the answer. For a
  CPU-only request, query SQL and PostgreSQL and state that Cosmos CPU is not
  exposed by this contract.
- For general cross-engine health/performance requests that include Cosmos
  availability/RU, and for all-findings requests, page Cosmos health with the
  filtered POST form until `continuationToken` is absent. A first-page Cosmos
  result is incomplete. Do not call Cosmos health for inventory-only or
  CPU-only requests.
- In every Cosmos health answer, label `processedAccounts` and `totalAccounts`
  separately even when they are equal; do not compress them into one unlabeled
  account count. When they differ, literally label coverage `partial` or
  `inconsistent`. When `totalAccounts` is `0`, report `totalAccounts: 0`, say
  there are no Cosmos DB accounts in scope and therefore no availability or
  normalized RU data, and do not call Cosmos healthy.
- For CPU-only requests, report CPU evidence only. Do not add storage or memory
  counts merely because the summary response also contains them.
- Treat HTTP 200 with non-empty `errors`, incomplete `coverage`, or remaining
  continuation tokens as partial, not complete success.
- Label posture denominators exactly: authentication counts cover Azure SQL
  databases plus Arc SQL Server, while auditing and CMK counts cover Azure SQL
  databases only. Repeat the literal scope on each posture line: "Azure SQL +
  Arc SQL Server" for authentication and "Azure SQL only" for both auditing and
  CMK.
- For "all issues and suggestions" output, report both `totalFindingCount` and
  `totalAffectedResourceCount` for every returned database family. Do not
  substitute affected-resource counts for finding totals.
- State that Cosmos DB exposes availability and normalized RU consumption here,
  not CPU, memory, storage, latency, or throttled-request diagnostics.
- State normalized RU saturation and explicitly say it does **not** prove
  throttled requests because this contract exposes no throttling metric. Do not
  rephrase saturation as a confirmed, likely, or potential throttling risk.

### PREFER

- Start with summary/count routes, then drill into only the affected population.
- Use server-provided finding summaries and high/low usage classifications
  instead of inventing thresholds.
- Project compact typed summaries from API responses. Do not dump full metric
  series or finding `targetSummaries` unless the user asks for them; oversized
  tool output is harder to ground reliably.
- Group results by database family and priority, with affected counts and named
  examples only when the user asks for detail.
- Reuse an immutable filter snapshot across pages and related filtered calls.

### AVOID

- Direct calls to ADX, Kusto, `arcdataservices.com`, workload regional hosts, or
  any MWC-token flow.
- Agent-authored KQL, schema discovery, or arbitrary telemetry queries.
- Claiming IO support; the current health contract exposes CPU, storage, and
  memory for Microsoft SQL/PostgreSQL.
- Inferring throttled requests or throttling from normalized RU consumption
  alone. This contract reports RU saturation, not throttling events.
- Treating an empty response as healthy when authorization, coverage, paging,
  or partial errors are unresolved.

## Examples

```text
User: Are there any performance issues I should know about in my data estate?
Mode: operations
Action: Query all three health families, report performance findings and partial coverage, then drill into high-usage SQL/PostgreSQL resources when needed.
```

```text
User: What should I fix first to improve security across my databases?
Mode: operations
Action: Compare security issues with authentication, auditing, and CMK posture; prioritize affected resources without changing them.
```

```text
User: Show my database estate by engine and subscription.
Mode: consumption
Action: Read counts, page the requested inventory, and group returned resources by type and subscription.
```

```text
User: How is my CPU consumption looking across my databases recently?
Mode: operations
Action: Query Microsoft SQL and PostgreSQL CPU coverage and explicitly note that this Database Hub Cosmos contract has no CPU metric.
```

```text
User: Give me a breakdown of all issues and suggestions across my data estate.
Mode: operations
Action: Combine health finding summaries with security issue/suggestion summaries and list affected resources through read-only drill-down routes.
```
