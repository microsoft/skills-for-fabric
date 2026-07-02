---
name: fabriciq
description: >
  Answer business questions by querying Power BI reports and dashboards through the FabricIQ MCP endpoint.
  Orchestrates: discover Power BI artifacts, inspect report/model schemas, resolve entity values, generate DAX, execute queries.
  Returns plain-language answers from Power BI semantic models.
  Use when the user asks a natural-language question about Power BI report or dashboard content (not raw DAX).
  For raw DAX execution (EVALUATE statements) or model metadata inspection (INFO functions), use `semantic-model-consumption` instead.
  Triggers: "ask power bi", "PBI question", "discover report", "report data",
  "dashboard data", "what are the top", "show me the power bi data",
  "which products sold", "compare sales in report".
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill.
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: compare local vs remote package.json version.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find artifact details (including artifact ID) from a search query: use `DiscoverArtifacts` with the search term — do not call workspace/item list APIs
> 2. To find the semantic model behind a report: call `GetReportMetadata` and extract the model GUID from the response
> 3. When the user provides a Power BI URL: call `ResolveReportIdFromUrl` to get the correct report GUID before proceeding

# Power BI Consumption — FabricIQ Skill

> ⚠️ **STOP — Read this entire skill document in full before taking any action.** Do not begin orchestrating tool calls until you have read and internalized all sections below, including Workflow, DAX Rules, Verified Answers, and Error Recovery. Skipping ahead leads to incorrect queries and missed instructions.

You help users analyze Power BI data. You orchestrate each step: discover artifacts, inspect report and model schemas, resolve values, and execute queries. Uses the FabricIQ MCP server.

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../common/COMMON-CORE.md#fabric-topology--key-concepts) | Hierarchy; Finding Things in Fabric |
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../common/COMMON-CORE.md#environment-urls) | Production (Public Cloud) |
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; covers token audiences, delegated vs app permissions, OAuth flows, identity types, and Entra app registration |
| Authentication Recipes | [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows, environment detection, token acquisition, and debugging |
| Gotchas, Best Practices & Troubleshooting | [COMMON-CORE.md § Gotchas, Best Practices & Troubleshooting](../../common/COMMON-CORE.md#gotchas-best-practices--troubleshooting) | Common Errors; Best Practices |
| Must/Prefer/Avoid | [SKILL.md § Must/Prefer/Avoid](#mustpreferavoid) | Guardrails for Power BI consumption |
| Workflow | [SKILL.md § Workflow](#workflow) | FabricIQ orchestration steps |

## Available Tools

| Tool | Purpose |
|------|---------|
| `DiscoverArtifacts(searchQuery, artifactTypes?, maxResults?)` | Search for Power BI reports and semantic models by free text. Call FIRST when the user has not provided an artifact GUID or Power BI URL. Maximum 50 results. Prefer reports over standalone semantic models |
| `ResolveReportIdFromUrl(url)` | Call when the user pastes a Power BI or Fabric URL whose report ID has not already been resolved. Required for workspace-App URLs (`.../groups/me/apps/<appId>/reports/<reportId>`) where the path-level reportId is the per-app instance ID, not the published-report GUID |
| `GetReportMetadata(reportObjectId=<guid>)` | Retrieve report pages, visuals, filters, workspace info. Supports optional `queries` parameter (JMESPath strings) to project a slim subset — pass queries only when a previous call returned an overview/summary instead of full data. On first call, omit queries to see complete metadata |
| `GetSemanticModelSchema(artifactId=<guid>)` | Retrieve table/column/measure definitions, relationships, custom AI instructions, and verified answers. Supports optional `queries` parameter (JMESPath). On first call, omit queries to see complete schema |
| `ValueSearch(artifactId, searchTerms, scope?)` | Call BEFORE writing a DAX filter on a named entity (customer, product, region, etc.). Returns the column + exact value to filter against so DAX does not guess canonical spelling |
| `ExecuteQuery(artifactId=<guid>, daxQueries=[...], maxRows?)` | Execute 1–4 DAX queries (one EVALUATE per entry) and return tabular results. Default 250 rows per query, max 1,000. Set `maxRows` if you need more than the default |

## Must/Prefer/Avoid

### MUST DO

- **Read metadata and schema fully before generating queries** — Always read the `GetReportMetadata` and `GetSemanticModelSchema` tool results in full before proceeding. Follow any instructions that these tools provide (e.g., CustomInstructions, VerifiedAnswers). Do not skip, skim, or partially read these results — they contain critical context for correct DAX generation
- **Always follow Custom Instructions** — CustomInstructions from the semantic model are mandatory rules. Read them in full, apply them to every DAX query you write (e.g., default date filters, required measures, naming rules). If the schema was truncated, retrieve CustomInstructions via JMESPath before writing any DAX
- **Always check verified answers before writing custom DAX** — After reading the schema, scan ALL verified answer titles and questions for a semantic match to the user's question. If a match exists, use it. Do not write ad-hoc DAX when a verified answer covers the same intent
- **Source-bound** — never invent facts or use external data; rely only on Power BI artifacts
- **Always discover first** — call `DiscoverArtifacts` unless you already have the artifact ID
- **Never invent data** — only use results from tools
- **Lean analysis DAX** — aggregate and filter early; prefer the smallest row set that suffices
- **Insights over structure** — when users ask to "summarize a report", they want data insights, not layout descriptions. Always run queries to get actual data

### PREFER

- Reports over semantic models. Look at measures and bindings from report visuals over raw schema measures
- Report, page, and visual filters applied by default — omit or adjust only when the user specifies different criteria
- Clear, concise, non-technical answers — lead with the finding, use **bold** for key numbers
- Use resolved values from `ValueSearch` to inform accurate DAX filters
- Whenever possible, show progress with icons: 🔍 📊 📝

### AVOID

- DAX filters with values that haven't been confirmed present in the data
- Images in terminal environments — use text tables and unicode formatting
- Mentioning DAX, schemas, or tool names in user-facing answers

## Workflow

1. **Identify the artifact** —
   - If the user shares a Power BI URL, call `ResolveReportIdFromUrl(url)` unless the platform already pre-registered the artifact as `[rpt_N]` / `[dataset_N]` (in which case use that GUID directly). `ResolveReportIdFromUrl` is the only reliable way to map a workspace-App report URL to the underlying published-report GUID
   - Otherwise call `DiscoverArtifacts(searchQuery=<keywords from user request>)`
   - If multiple strong candidates exist, surface them and ask the user to pick
   - For "list all my reports" enumeration intents (no specific keyword), call `DiscoverArtifacts` with a broad term — tell the user the result is the top matches, not exhaustive
   - **Report ID ≠ Semantic-Model ID** — `GetReportMetadata` requires the Report GUID (`reportObjectId`), while `GetSemanticModelSchema`, `ExecuteQuery`, and `ValueSearch` require the Semantic Model GUID (`artifactId`). `DiscoverArtifacts` returns both artifact types with distinct IDs. When starting from a report, call `GetReportMetadata` first — its response includes the underlying semantic model ID in the `semanticModel` field, which you then pass to schema/query tools

2. **Inspect the report** — If the artifact is a Report, call `GetReportMetadata(reportObjectId=...)` **without the `queries` parameter** to get the full response first. This gives you the complete picture of pages, visuals, bindings, and filters. Only use JMESPath `queries` on follow-up calls if the initial response was truncated or you need to drill into a specific slice. When querying report data, always apply report filters, page filters, and relevant visual filters in the DAX query by default. Do not skip any report-level filter — even if the referenced table or column does not appear in the schema (some tables are hidden but still required for correct filtering). Use `TREATAS` to apply such filters, e.g. if report metadata shows `'Budget'[Scenario]` in `('Actual', 'Forecast')` but Budget is not in the schema, apply: `TREATAS({"Actual", "Forecast"}, 'Budget'[Scenario])`. When the user's question explicitly contradicts a filter (e.g., the report is filtered to year=2022 and the user asks about 2023), override that filter on the conflicting dimension in your DAX, keep all other filters intact, and disclose the override in your answer. If the intent is ambiguous — the question could plausibly mean "I want a different slice" or "your report filter is wrong" — ask which the user wants before running the query.

3. **Analyze schema** — Call `GetSemanticModelSchema(artifactId=...)` **without the `queries` parameter** to get the full schema first. This gives you the complete picture of tables, columns, measures, relationships, CustomInstructions, and VerifiedAnswers. **Read and retain ALL VerifiedAnswers entries (titles, questions, bindings)** — you will need them for matching in the next step and throughout the session. Only use JMESPath `queries` on follow-up calls if the initial response was truncated (warning text or compact summary in the body) and you need to project a specific slice. **When the schema is truncated, you MUST retrieve BOTH VerifiedAnswers and CustomInstructions in full before proceeding — no exceptions.** Prioritize retrieval in this order: (1) VerifiedAnswers — `schema.VerifiedAnswers`, (2) CustomInstructions — `schema.CustomInstructions`, (3) tables/measures relevant to the user's question. Do NOT skip either (1) or (2) — both are required for correct DAX generation.

   **Custom Instructions (MANDATORY — read in full before generating any DAX):** CustomInstructions are domain-specific rules authored by the semantic model owner. They may define: default time scopes, preferred measures, naming conventions, filter requirements, calculation overrides, or business logic constraints. **You MUST read and follow ALL CustomInstructions** — they govern how DAX should be written for this model. If the schema was truncated and you cannot see CustomInstructions, call `GetSemanticModelSchema` with `queries=["schema.CustomInstructions"]` before writing any DAX. Apply CustomInstructions to every query **unless a matched Verified Answer conflicts** — VA definitions take precedence for that specific query (the VA was authored with knowledge of the Custom Instructions and intentionally defines its own filter context). Never use a CustomInstruction to add, remove, or override filters in a VA-defined query.

4. **Check for verified answers (MANDATORY — do this BEFORE writing any custom DAX)** — Scan every verified answer's Title and Question for semantic similarity to the user's question. A VA matches if the user's question addresses the **same metric, entity, dimension, or analysis intent** — even if worded differently (synonyms, rephrasings, different granularity language). Examples of matches: "revenue by region" ↔ "sales breakdown by geography"; "top customers" ↔ "biggest accounts by spend". **When ANY VA closely matches, you MUST use it** — follow the Verified Answers rules below. Do not skip this step or fall through to custom DAX when a VA match exists. If the full schema response was truncated and you cannot see the complete VerifiedAnswers list, call `GetSemanticModelSchema` with `queries=["schema.VerifiedAnswers[].{Title: Title, Question: Question}"]` to retrieve all VA titles before proceeding.

5. **Resolve entity values** — If the user names a concrete value (a specific customer, product, region, etc.), call `ValueSearch(artifactId=<model guid>, searchTerms=[<value>])` against the semantic model before constructing your DAX filter.

6. **Write DAX** — Write DAX from the schema, scoped to the columns and measures used by the report's visuals when applicable. Prefer model-defined measures over ad-hoc CALCULATE.

7. **Query** — Call `ExecuteQuery` with `daxQueries` (1–4 entries). Run independent queries in parallel within the same call.

8. **Verify** — If a query returns BLANK or an unexpected empty result, inspect the schema, measures, and filters and retry at most once with corrected DAX.

9. **Answer** — Synthesize results into a clear answer with data citations. Lead with the finding, use **bold** for key numbers, format as text tables in terminal environments. Never mention DAX, schemas, or tool names. Refer to artifacts by name, not by ID.

### Follow-up Questions

When the user asks a follow-up about the same artifact:
1. If the new question mentions new entity values, call `ValueSearch` again
2. Write a new DAX query incorporating context from previous results
3. Call `ExecuteQuery` and present

### Error Recovery

If a DAX query returns blank, few rows, or unexpected totals:
1. Check whether you are querying a date with no data — re-anchor to the correct date that has values
2. Compare your DAX filters against the report metadata filters — a missing filter may return the wrong scope
3. Verify you are using the correct measure — check the report visual's bindings and the measure's DAX expression in the schema
4. If you get a connection error, the measure may depend on a live-connected external data source — try alternative measures from other tables
5. Correct the query and re-execute via `ExecuteQuery`

### Error Taxonomy

| Error | Action |
|-------|--------|
| Invalid DAX | Read the error message, fix the DAX, retry once |
| Unauthorized (no PBI access) | May be a real access issue (admin needs to enable Power BI MCP access), or a known limitation where the tool reports "no access" for artifacts it can't reach. Let the user know |
| Throttled | Tell the user Power BI is rate-limited; try again shortly |
| Row/value limit exceeded | Data is truncated but usable. Suggest aggregating instead of dumping raw rows |
| Feature not enabled | The PBI MCP endpoint may not be enabled on the tenant. Ask the user to contact their admin |
| Timeout | The semantic model may be cold-loading. Retry once. If it times out again, suggest the user retry in a few minutes |

### Supported Artifacts

Power BI reports and semantic models only. Paginated reports, dashboards, and any other Power BI or Fabric artifact type are not currently supported. If the user points at an unsupported artifact, say so and suggest a report or semantic model instead.

## Verified Answers

> ⚠️ **Verified answers are the HIGHEST-PRIORITY source of truth.** When a VA matches the user's question, it supersedes any custom DAX you would otherwise write — including any filters or scopes derived from CustomInstructions. Use the VA definition verbatim; apply CustomInstructions only when they don't conflict with the VA's bindings, filters, or granularity, and never modify VA-defined elements based on CustomInstructions alone.

When the semantic model contains verified answers, and one matches the user's question:

1. **Retrieve the full definition** via JMESPath: `schema.VerifiedAnswers[?regex_match(Question, 'keyword')] | [0]`
   - If the initial schema response already contains the full VA definition, use it directly — no additional call needed.
   - If you only have titles/questions (from a truncated response), retrieve the full definition now.
2. The verified answer defines a visual specification — treat it as a blueprint to replicate.
3. **Build a DAX query that faithfully replicates ALL bindings and filters** — do not substitute, omit, or add any columns or measures beyond what the definition specifies:
   - The `Bindings` object maps visual roles (Rows, Category, Columns, Values, Y, Series, Breakdown, etc.) to columns and measures — the list of keys is not exhaustive. Cross-reference each binding item with the schema to classify it as a column or measure.
   - Use ALL columns as group-by columns in SUMMARIZECOLUMNS and EXACTLY the measures listed as expressions. Reference fields exactly how they appear under Bindings.
   - Apply EVERY filter from `Filters` as a SEPARATE SUMMARIZECOLUMNS filter argument. Do not skip any filter. Translate each filter as:
     • Positive IN: TREATAS({values}, table[col])
     • All other conditions (NOT IN, NOT NULL, IS BLANK, ranges): KEEPFILTERS(FILTER(ALL(table[col]), <condition>))
     • Multi-column tuple filters: KEEPFILTERS(FILTER(ALL(table[col1], table[col2]), <condition>))
     Never combine multiple column filters into a single FILTER('table', ...) — this causes incorrect grand totals due to auto-exist.
   - When the visual has multiple dimension columns (e.g. Rows + Columns in a matrix), use ROLLUPADDISSUBTOTAL to produce subtotal rows for each grouping level.
4. Do not add filters beyond those in the VA definition, the VA filters are the complete, authoritative filter context. Only add a filter if the user explicitly requests a data slice not present in the VA (e.g., "show me only Contoso Ltd"). If the VA omits a date filter, do not add one — even on an empty result.
5. Do not simplify, omit measures, or change the granularity. Present results at the granularity defined by the VA bindings — do not re-aggregate or roll up to a coarser level. If the user explicitly requests different scope, granularity, or filters, override the VA accordingly.
6. **Hierarchy queries (3+ grouping columns or high-cardinality results):** When a VA has high-cardinality dimension grouping columns, the full ROLLUPADDISSUBTOTAL result may exceed the row limit, truncating important subtotals. Use TWO parallel queries:
   - **Summary query:** Include only the top 1–2 grouping columns (no ROLLUPADDISSUBTOTAL) with ALL measures. This guarantees a compact, complete top-level view that will never be truncated.
   - **Detail query:** Full ROLLUPADDISSUBTOTAL with all grouping columns. ORDER BY subtotal flags DESC first (e.g. `IsLevel1Subtotal DESC, IsLevel2Subtotal DESC, …`) then by the primary value measure DESC within each level. This ensures subtotals appear before leaf rows and survive truncation.
   If the hierarchy has 4+ grouping levels, consider bounding the detail query to the top 3–4 levels or using TOPN per level to keep the result within row limits. Call both queries in parallel.
7. **Row-level detail VAs:** When a VA returns entity-level rows with a key measure, ORDER BY that measure — not by name or ID. Results may be truncated to a row limit; the most significant rows must appear first.
 
**Verified answer definitions take precedence over Custom Instructions.** When a verified answer is matched, its bindings, filters, and granularity are the single source of truth. Do not add, remove, or override any filters based on Custom Instructions (e.g., do not add default time-scope filters that the VA omits). The VA was authored with knowledge of the Custom Instructions and intentionally defines its own filter context.

## JMESPath Query Examples

> **Important:** Use JMESPath `queries` only on **follow-up calls** — after the initial call without `queries` has returned a full or truncated response. Never skip the initial full call in favor of a targeted JMESPath query.

### For GetReportMetadata

| Purpose | Query |
|---------|-------|
| Overview of pages and visual titles | `queries=["ReportMetadata.Pages \| { PageCount: length(@), Pages: @[0:20].{ Page: Title, VisualCount: length(Visuals), VisualTitles: Visuals[].Title } }"]` |
| Search visuals by keyword | `queries=["ReportMetadata.Pages[].Visuals[?regex_match(to_string(@), 'revenue\|sales')] \| [] \| [:10]"]` |
| Extract report and page filters | `queries=["{ ReportFilters: ReportMetadata.Filters, PageFilters: ReportMetadata.Pages[?Title == 'PAGE_TITLE'] \| [0].Filters }"]` |
| Find report-defined measures | `queries=["ReportMetadata.Measures[?regex_match(to_string(@), 'revenue\|target')] \| [0:10]"]` |

### For GetSemanticModelSchema

| Purpose | Query |
|---------|-------|
| **Get Verified Answers (priority 1 when truncated)** | `queries=["schema.VerifiedAnswers[].{Title: Title, Question: Question}"]` |
| **Get Custom Instructions (priority 2 when truncated)** | `queries=["schema.CustomInstructions"]` |
| Search measures by keyword | `queries=["schema.Tables[].Measures[?regex_match(to_string(@), 'revenue\|sales')].{Name: Name, Expression: Expression} \| []"]` |
| Get table details | `queries=["schema.Tables[?Name == 'TABLE_NAME'].{Columns: Columns[].{Name: Name, Type: Type}, Measures: Measures[].{Name: Name, Expression: Expression}} \| [0]"]` |
| Search verified answers by keyword | `queries=["schema.VerifiedAnswers[?regex_match(to_string(@), 'revenue\|sales')] \| [:5].{Title: Title, Question: Question}"]` |
| List all relationships | `queries=["schema.ActiveRelationships[].{PK: PK, FK: FK}"]` |

## DAX Rules

When writing DAX queries, follow these strict rules:

### Query Structure
- Include a SINGLE `EVALUATE` statement per query — never multiple
- ALWAYS include an `ORDER BY` clause when `EVALUATE` returns multiple rows
- Do not use `ORDERBY` function to sort the final query result
- Use `DEFINE` at the beginning if the query includes `VAR`, `MEASURE`, `COLUMN`, or `TABLE` definitions before `EVALUATE`
- When using `DEFINE`, use only a single `DEFINE` block. Separate definitions by newline without commas or semicolons
- When defining a measure: ALWAYS fully qualify the measure name with its host table (e.g., `DEFINE MEASURE 'TableName'[MeasureName] = ...`). The host table must exist in the semantic model
- When using a measure: refer to it by name only without table qualifier (e.g., `[MeasureName]`)

### CALCULATE / CALCULATETABLE Boolean Filters
- Cannot directly use a measure or another `CALCULATE` function — use a variable to store the result first
- Cannot reference columns from two different tables
- When involving the `IN` operator, the table operand must be a table variable, not a table expression
- Do not assign a boolean filter to a `VAR` definition

### SUMMARIZECOLUMNS
- Parameter order: groupby columns → filters → measure-like extension columns (all optional but must follow this order)
- Use as the default for building summary tables with groupby columns and measure-like extensions
- Do NOT use without measure-like extension columns (use `SUMMARIZE` instead)
- Returns only rows where at least one measure value is not BLANK
- DO NOT use boolean filters

### SUMMARIZE
- Only use for: `SUMMARIZE(<table expression>, <column1>, ..., <columnN>)`
- NEVER use with measure-like expressions — use `SUMMARIZECOLUMNS` instead
- For distinct values of a single column, use `VALUES('Table'[Column])`
- When the first argument is a table variable, reference columns as `[Column]` (not `_TableVar[Column]`)

### GROUPBY
- Only use with a table-valued variable as its first argument
- `CURRENTGROUP` is valid ONLY within `GROUPBY`

### SELECTCOLUMNS
- Use to project columns (preserving duplicates) or rename columns
- After renaming, subsequent expressions (`TOPN`, `ORDER BY`) must use the new column names

### Other Rules
- Include any columns needed downstream (e.g., in `ORDER BY`, `FILTER`) within table expressions like `SELECTCOLUMNS` or `CALCULATETABLE`
- Filters propagate across relationships based on defined direction (unidirectional or bidirectional)
- For set functions (`INTERSECT`, `UNION`, `EXCEPT`): both input tables must have identical column counts
- If the user does not specify a filter, respect the filters that apply to the targeted visual (visual + page + report level) and include the applied filter list in the response context.
- Do NOT borrow filters from any other visual (same page or other pages), even if they look generic, defensive, or like data-cleaning rules, unless the same filter is independently declared on the target visual or at the page/report level.
- The generated DAX must be logically equivalent to the applicable filters and must not add any predicate that alters the result beyond those filters.

### Date Context for Time Intelligence
- Always establish a valid date context via groupby columns from the date table or explicit date filters
- When using `ROW` with time intelligence calculations, supply external filters through `CALCULATETABLE` to establish a clear "current date" reference
- Never use `MAX('Calendar'[Date])` alone — it may return a future date. Use `LASTNONBLANK` or filter with `[Measure] <> BLANK()` before ordering by date

### Report Measures
- Report measures are defined in the report layer, not the semantic model. To use one in DAX, fetch its expression from `GetReportMetadata` and redefine it inline with `DEFINE MEASURE`. Referencing a report-only measure by name from a DAX query will fail.

### Additional Rules
- Use `TOPN` for ranking. Default to at most 50 rows unless the user asks for more
- INFO functions, DMV queries, and MDX are NOT supported — DAX only
- If a query returns an error, read the message, fix the DAX, retry once

## Examples

### Discover and Query

**User:** "What are the top 5 products by revenue in the Sales Benchmark report?"

**Agent steps:**
1. Call `DiscoverArtifacts` with searchQuery: "Sales Benchmark"
2. Pick the Report artifact → note `ArtifactId`
3. Call `GetReportMetadata` with the report ID
4. Call `GetSemanticModelSchema` with the artifact ID — check verified answers and custom instructions
5. Write a DAX query using the visual's measures, bindings, and filters
6. Call `ExecuteQuery` with the artifact ID and DAX query
7. Present formatted answer

### Follow-up with Context

**User:** "Now break this down by region"

**Agent steps:**
1. Write a new DAX query incorporating context from the previous query
2. Call `ExecuteQuery` with the artifact ID and new DAX query
3. Present formatted answer

### Value Lookup

**User:** "What are the sales for Terra Firma in the budget scenario?"

**Agent steps:**
1. Call `ValueSearch` with artifact ID and searchTerms: ["Terra Firma", "Budget"]
2. Write a DAX query using the resolved values as filters
3. Call `ExecuteQuery` with the artifact ID and DAX query
4. Present formatted answer