---
name: silver-cumulative-table-design
description: "Designs and implements Cumulative Table Design (CTD) in the Silver layer of a Fabric Lakehouse: entity-level history accumulated in Delta arrays-of-structs, the daily full-outer-join pipeline, schema decisions, MERGE vs overwrite strategies, and when CTD is and is not the right choice. Use this skill when a user asks to track entity state over time, build activity history, avoid snapshot explosion, replace a slowly-changing-dimension (SCD2) with a compacted pattern, or when they say 'cumulative table'. For raw Bronze ingestion use e2e-medallion-architecture; for the notebook that runs the pipeline use spark-cli."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: silver-cumulative-table-design` (`az rest`: `--headers "x-ms-fabric-skill=silver-cumulative-table-design"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. **Skill disambiguation**: use `silver-cumulative-table-design` for schema design, daily pipeline logic, and MERGE strategy for cumulative tables. Notebook cell authoring and Livy execution belong to `spark-cli`; Bronze ingestion and medallion setup belong to `e2e-medallion-architecture`; semantic model authoring on top of the resulting table belongs to `semantic-model-authoring`.

# Silver — Cumulative Table Design (CTD)

Cumulative Table Design is a Silver-layer modelling pattern where each row represents one **entity** (a user, device, account, product, etc.) and carries both its **current state** and its full **activity history** as an array of structs — one element per observation period (typically one day). A single daily pipeline replaces yesterday's cumulative table and today's new activity via a full-outer join, producing a table that never grows in row count beyond the cardinality of the entity population.

This skill owns the entire CTD lifecycle: fitness assessment, schema design, the daily merge pipeline, history pruning strategy, and downstream access patterns. It contains NO procedures. Read the matching reference file before acting.

---

## Fitness gate — read this before doing anything else

CTD is not always the right choice. Before designing a schema or writing code, evaluate the request against this table. **If any REJECT condition is met, stop and state the reason** — do not proceed to schema design.

| Signal in the request | Verdict | Reasoning |
|---|---|---|
| Entity population is stable and known (users, devices, accounts) | ACCEPT | CTD shines: bounded row count, rich history per entity |
| Request is "track how X changed over time" or "show activity history of Y" | ACCEPT | Core CTD use case |
| Replacing an SCD2 that is too wide or too slow for Direct Lake | ACCEPT | CTD eliminates is_current filter scans |
| Daily or near-daily observation cadence | ACCEPT | Array growth is predictable; pruning is straightforward |
| Entity cardinality > 50 M rows AND history window > 1 year | EVALUATE | Array columns become very large; consider partitioned snapshots or Parquet instead |
| Sub-minute or streaming observations | REJECT | CTD is batch-day oriented; use Eventhouse / KQL or a streaming lakehouse table instead |
| Entity population is unbounded and unknown at design time (e.g., arbitrary event keys) | REJECT | No bounded row count; row explosion defeats CTD's purpose — use partitioned event tables |
| Source has no stable entity key | REJECT | Cannot join yesterday <-> today without a key; ask the user to define one first |
| Downstream consumer is a SQL endpoint only (no Spark) and cannot unnest arrays | EVALUATE | CTD arrays require Spark or a flattened view; build the view, note the limitation |
| Gold layer needs flat, pre-aggregated rows for Direct Lake | EVALUATE | CTD is Silver; Gold should explode and reaggregate — route Gold design to e2e-medallion-architecture |

If the verdict is EVALUATE: ask **one** clarifying question (entity count, history retention, downstream tool) before deciding. Do not ask multiple questions at once.

---

## Mode selection

| Mode | Use when the request ... | Example triggers | Read this first |
|---|---|---|---|
| `design` | User wants a schema, wants to understand what CTD is, wants to evaluate whether CTD fits their use case, or asks for a migration from SCD2/snapshots | "design a cumulative table for users", "should I use CTD here?", "replace my SCD2 with something simpler" | [references/design.md](references/design.md) |
| `pipeline` | User wants the daily incremental pipeline code: the full-outer-join notebook logic, MERGE vs overwrite choice, deduplication, NULL coalescing, or history pruning | "write the daily pipeline", "how do I update the cumulative table each day", "write the PySpark for the CTD merge" | [references/pipeline.md](references/pipeline.md) |
| `access` | User wants to query the cumulative table: explode history to flat rows, compute date-spine metrics, build a Gold view, or connect to Power BI | "how do I query this table", "explode the history array", "build a gold view from the cumulative table" | [references/access.md](references/access.md) |
| `ops` | User wants to troubleshoot an existing CTD pipeline: history array growing too large, MERGE conflicts, partition skew, schema evolution issues | "my cumulative table is bloating", "MERGE is failing with schema mismatch", "history array has duplicates" | [references/ops.md](references/ops.md) |

### Mode boundary rules

- `design` is read-only on Fabric (no API calls, schema output only). A request to *create* the notebook that runs the pipeline belongs to `spark-cli authoring` after the schema is agreed.
- `pipeline` produces PySpark notebook code only. Deploying that notebook to a Fabric workspace requires `spark-cli authoring`; running it requires `spark-cli authoring` or `consumption`.
- `access` produces Spark SQL / PySpark read patterns and optionally a Gold view DDL. Creating the Gold table belongs to `e2e-medallion-architecture`.
- If a request spans modes (e.g., "design and write the pipeline"), handle one mode at a time, state the switch, and read each reference before starting that part.
- If the mode is ambiguous, ask one short clarifying question — do not guess.

---

## Terminal write — the step you must not skip

Producing schema DDL, PySpark snippets, or a notebook cell is **not** completing the task. The terminal write for each mode is:

| Mode | Terminal write |
|---|---|
| `design` | None — `design` is advisory. State explicitly that the schema must be deployed via `spark-cli authoring` (CREATE TABLE DDL via Livy) or the user's notebook. |
| `pipeline` | Notebook cell code ready for the user to paste, OR a `spark-cli authoring` handoff to create and deploy the notebook. Printing the code without deploying it is not a terminal write. |
| `access` | A working Spark SQL / PySpark cell block, or a Gold view DDL statement ready for deployment via `spark-cli authoring`. |
| `ops` | A diagnosis and a concrete remediation command (ALTER TABLE, VACUUM, OPTIMIZE, schema migration DDL). State whether the fix was applied or is advisory. |

---

## Shared essentials (all modes)

| Task | Reference | Notes |
|---|---|---|
| Notebook deployment and execution | [spark-cli](../spark-cli/SKILL.md) | Required for all PySpark pipeline deployment |
| Medallion layer setup and Bronze ingestion | [e2e-medallion-architecture](../e2e-medallion-architecture/SKILL.md) | Read before setting up the Silver lakehouse |
| Finding workspaces and items | [COMMON-CLI.md](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | Resolve workspace and lakehouse IDs by listing |
| Delta Lake write patterns | [COMMON-CORE.md](../../common/COMMON-CORE.md) | MERGE semantics, schema evolution, partition overwrite |
| Spark Optimization | [data-engineering-patterns.md](../spark-cli/references/authoring/resources/data-engineering-patterns.md) | Silver-layer Spark config: V-Order, AQE, ZORDER |

---

## Pattern reference — CTD fundamentals

This section is the conceptual anchor. Read the mode reference for the implementation detail; use this section to answer "what is CTD and why".

### Core idea

```
cumulative_table[today] =
    FULL OUTER JOIN(cumulative_table[yesterday], new_activity[today])
    -> COALESCE entity key from both sides
    -> COALESCE scalar state columns (prefer today value if not null)
    -> ARRAY_UNION(yesterday.history, [today_struct]) for the history column
    -> FILTER out entities inactive beyond retention_days
```

One row per entity. One history column. No partition explosion. No is_current flag.

### Anatomy of a CTD schema

```
entity_id          STRING       NOT NULL   -- stable business key
<current_field_1>  <TYPE>                  -- coalesced current state (e.g., subscription_plan)
<current_field_2>  <TYPE>                  -- coalesced current state (e.g., country)
history            ARRAY<STRUCT<           -- one element per observation day
  date             DATE,                   -- the observation date
  <metric_1>       <TYPE>,                 -- observed value on that day (nullable)
  <metric_2>       <TYPE>
>>
first_seen_date    DATE                    -- when the entity first appeared
last_active_date   DATE                    -- most recent observation; used for pruning
updated_at         TIMESTAMP               -- pipeline write timestamp (monotone)
```

### When to split vs merge history columns

| Scenario | Recommendation |
|---|---|
| All observed metrics belong to the same observation event | Single history array of structs |
| Two independent observation streams with different cadences | Two separate arrays (e.g., session_history, purchase_history) |
| One stream has very high cardinality per period (>50 events/entity/day) | Do not use CTD for that stream; keep as event table, join at query time |
| Array exceeds ~10 MB per row (check with len(to_json(history))) | Prune older entries or partition history into year buckets |

### History retention and pruning

Retention is always applied **after** the union step, before the write:

```python
from pyspark.sql.functions import col, filter as array_filter, datediff, current_date

df = df.withColumn(
    "history",
    array_filter("history", lambda x: datediff(current_date(), x["date"]) <= retention_days)
)
```

Default retention guidance:

| Use case | Recommended retention |
|---|---|
| User engagement / activity | 365 days (1 rolling year) |
| Financial / compliance | Driven by regulatory requirement; typically 7 years — store in Delta time travel instead of array for audit |
| Device telemetry | 90 days |
| Product interaction | 180 days |

---

## Rules

### MUST

- Run the **fitness gate** before entering any mode. If a REJECT condition is met, state it and stop.
- Choose exactly one mode before doing anything else.
- Read the matching `references/<mode>.md` end to end as your FIRST tool call before writing any code or DDL.
- State the entity key explicitly before designing the schema — if the user has not provided one, ask before proceeding.
- Apply history pruning in every pipeline — an unbounded array is a time-bomb.
- Use `FULL OUTER JOIN` between yesterday's cumulative and today's new activity — never `LEFT JOIN` alone (it drops new entities) and never `INNER JOIN` (it drops dormant entities).
- Use `COALESCE(today.entity_id, yesterday.entity_id)` as the joined key — both sides can be null.
- Write the output to Delta Lake in Silver with `mode("overwrite")` and `replaceWhere` partition or full table overwrite — avoid appending (it creates duplicates). See `references/pipeline.md` for the exact strategy decision.
- Validate history uniqueness after the union step — assert `SIZE(ARRAY_DISTINCT(TRANSFORM(history, x -> x.date))) == SIZE(history)` per entity before writing. `ARRAY_DISTINCT` on structs compares full struct equality (not just date field); always project the date field via `TRANSFORM` first.
- Annotate every STRUCT field with a comment describing the unit and nullability.

### PREFER

- `replaceWhere` partition overwrite over full table overwrite when the cumulative table is partitioned by `first_seen_date` month buckets — it avoids rewriting unchanged partitions.
- Separating "today's activity" preparation (Bronze -> cleaned daily view) from the cumulative join step — two distinct notebook cells for debuggability.
- Storing `last_active_date` as a top-level column rather than deriving it from `MAX(history.date)` — avoids an array scan on every query.
- A Gold view that explodes history to flat rows and adds a date-spine, rather than expecting consumers to handle arrays directly.
- Running `OPTIMIZE` + `ZORDER BY entity_id` on the cumulative table after each write.
- V-Order settings (`spark.sql.parquet.vorder.default=true`) for Silver writes when Direct Lake access is planned downstream.

### AVOID

- Appending to the cumulative table (`mode("append")`) — it creates duplicate entity rows that corrupt the history.
- Designing schemas without a stable, non-null entity key.
- Using `ARRAY_UNION` without deduplication when the source can produce duplicate day entries — `ARRAY_UNION` in Spark deduplicates by value equality; if two structs differ on any field for the same date, both are kept. Assert date uniqueness.
- Treating CTD as a replacement for an event store — CTD is for entity state history, not raw event logs.
- Hardcoding the processing date — always pass `processing_date` as a pipeline parameter; default to `current_date() - 1`.
- Applying CTD to streaming sources — it is a batch-day pattern.
- Proposing SCD Type 2 as an equivalent alternative — SCD2 balloons row count and requires is_current filter scans; CTD is the alternative, not a synonym.
- Building the Gold layer from inside this skill — route Gold aggregations to `e2e-medallion-architecture`.

---

## Decision tree — schema design quick guide

Use this tree when the user request is ambiguous:

```
Does the entity have a stable business key?
+-- NO  -> Ask the user to define one. Do not proceed.
+-- YES -> Is the observation cadence daily or slower?
           +-- NO (sub-daily / streaming) -> REJECT: route to Eventhouse / streaming lakehouse
           +-- YES -> Is entity cardinality < 50 M?
                      +-- NO  -> Evaluate: ask for history window length
                      |         +-- window < 90 days  -> ACCEPT with aggressive pruning
                      |         +-- window > 90 days  -> Consider partitioned snapshots; present trade-offs
                      +-- YES -> Is the user replacing SCD2 or snapshots?
                                 +-- YES -> ACCEPT: CTD is the upgrade path; read references/design.md
                                 +-- NO  -> Is the use case "entity history over time"?
                                            +-- YES -> ACCEPT
                                            +-- NO  -> Clarify the use case; CTD may not be needed
```

---

## Examples

| User request | Fitness verdict | Mode | Reference |
|---|---|---|---|
| "Design a cumulative user activity table so I can see what each user did each day for the last year." | ACCEPT | `design` | [references/design.md](references/design.md) |
| "Write the PySpark notebook cell that updates my user_cumulative Silver table every morning." | ACCEPT | `pipeline` | [references/pipeline.md](references/pipeline.md) |
| "Replace my SCD2 customer_dim table with something that doesn't explode in Power BI Direct Lake." | ACCEPT | `design` then `pipeline` | [references/design.md](references/design.md) then [references/pipeline.md](references/pipeline.md) |
| "How do I query the history array to get a date-spine of user sessions?" | ACCEPT | `access` | [references/access.md](references/access.md) |
| "My cumulative table MERGE is failing with 'schema mismatch' after a Bronze schema change." | ACCEPT | `ops` | [references/ops.md](references/ops.md) |
| "Build a cumulative table for my Kafka click-stream (100k events/second)." | REJECT | — | State: streaming cadence — use Eventhouse / Real-Time Intelligence instead |
| "Track every HTTP request per user in a cumulative table." | REJECT | — | State: unbounded events per entity per period — use partitioned event table |
| "Design a Gold summary of cumulative user engagement by cohort." | EVALUATE | Route to e2e-medallion-architecture for Gold; this skill owns Silver CTD only | — |
