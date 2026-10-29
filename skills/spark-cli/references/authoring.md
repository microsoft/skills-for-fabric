<!-- Mode reference for the `spark-cli` skill. Loaded on demand from `skills/spark-cli/SKILL.md` when the request matches the `authoring` mode. -->

# Spark Authoring — CLI Skill

This skill covers two complementary areas: (1) **managing Fabric Spark artifacts via REST APIs** (workspaces, lakehouses, notebooks, jobs, pipelines) and (2) **writing code inside Fabric Notebook cells** (PySpark, Scala, SparkR, SQL with correct lakehouse access, notebookutils, and Spark configuration). For notebook code authoring fundamentals and shared modules, MUST see [SPARK-NOTEBOOK-AUTHORING-CORE.md](../../../common/SPARK-NOTEBOOK-AUTHORING-CORE.md).

## Notebook Codegen Invariants

Apply these before following any deeper link; the shared `common/` modules might not be present in a packaged skill runtime.

- **Offline notebook code generation:** answer from this file and its bundled resources; do not web-search for API alternatives. Read the relevant local resource once, then return the requested code. If an API is not documented locally, state that limitation instead of repeatedly searching.
- **Pipeline detection:** use `context = notebookutils.runtime.context`, then read `context["isForPipeline"]` and `context["currentWorkspaceId"]`. Do not parse the context as JSON or infer pipeline execution from `currentJobType`.
- **Built-in resources:** use `notebookutils.nbResPath` with `/builtin/`; Spark paths require the `file:` prefix, for example `f"file:{notebookutils.nbResPath}/builtin/config.json"`. Do not invent `notebookutils.resources.getPath`.
- **Variable Libraries:** use `library = notebookutils.variableLibrary.getLibrary("AppConfig")`, then read variables through dot notation such as `library.lakehouse_name` and `library.enable_feature`.
- **Default lakehouse in `%%configure`:** for session-scoped attachment, use the documented `defaultLakehouse` object in the first `%%configure` cell, for example `"defaultLakehouse": {"name": "LakehouseName"}`. Notebook `metadata.dependencies.lakehouse` is the persistent definition binding; do not claim `%%configure` lacks a lakehouse option.
- **Session memory and native execution:** put `%%configure` in the first cell, keep `driverMemory` and `executorMemory` at the JSON top level, and set `"spark.native.enabled": "true"` under `conf`. Native execution must be enabled before the Spark session starts.
- **Cross-workspace Spark SQL:** use the four-part backtick-qualified name `` `workspace`.`lakehouse`.`schema`.`table` ``.
- **Non-default ABFSS paths:** obtain the endpoint with `notebookutils.conf.get("trident.onelake.endpoint")` and keep the identifier order exact: `abfss://{workspaceId}@{endpoint}/{lakehouseId}/Tables/...`. The workspace ID is the authority before `@`; the lakehouse ID is the first path segment after the endpoint. Do not reverse them or hardcode `onelake.dfs.fabric.microsoft.com`.
- **Fabric connections:** copy the exact API spelling `credential = notebookutils.connections.getCredential("{connectionId}")` for PostgreSQL, Azure SQL, S3, and other Fabric-managed connections. Do not rename `notebookutils`, substitute `credentials.getConnectionString`, or hardcode credentials.
- **Large cross-lakehouse copies:** use `notebookutils.fs.fastcp(...)`, not `fs.cp(...)`.
- **ABFSS identifiers:** never mix a workspace ID with a lakehouse name. When notebook code receives a workspace ID plus lakehouse name, it MUST acquire a Fabric token with `notebookutils.credentials.getToken("pbi")`, list `/v1/workspaces/{workspaceId}/lakehouses`, select the exact `displayName`, fail if it is missing or ambiguous, and use the returned lakehouse ID in the ABFSS path. Do not send the user to the portal, leave an ID placeholder, ask for an ID the API can resolve, or switch to all-name syntax.

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| RULES — Read these first, follow them always | [SKILL.md § RULES](#rules--read-these-first-follow-them-always) | **MUST read** — 4 rules for this skill |
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* [needed for finding workspace id by its name or item id by its name, item type, and workspace id] |
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../../common/COMMON-CORE.md#fabric-topology--key-concepts) ||
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../../common/COMMON-CORE.md#environment-urls) ||
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../../common/COMMON-CORE.md#core-control-plane-rest-apis) ||
| Pagination | [COMMON-CORE.md § Pagination](../../../common/COMMON-CORE.md#pagination) ||
| Long-Running Operations (LRO) | [COMMON-CORE.md § Long-Running Operations (LRO)](../../../common/COMMON-CORE.md#long-running-operations-lro) ||
| Rate Limiting & Throttling | [COMMON-CORE.md § Rate Limiting & Throttling](../../../common/COMMON-CORE.md#rate-limiting--throttling) ||
| OneLake Data Access | [COMMON-CORE.md § OneLake Data Access](../../../common/COMMON-CORE.md#onelake-data-access) | Requires `storage.azure.com` token, not Fabric token |
| Definition Envelope | [ITEM-DEFINITIONS-CORE.md § Definition Envelope](../../../common/ITEM-DEFINITIONS-CORE.md#definition-envelope) | Definition payload structure |
| Per-Item-Type Definitions | [ITEM-DEFINITIONS-CORE.md § Per-Item-Type Definitions](../../../common/ITEM-DEFINITIONS-CORE.md#per-item-type-definitions) | Support matrix, decoded content, part paths — [REST specs](../../../common/COMMON-CORE.md#item-creation), [CLI recipes](../../../common/COMMON-CLI.md#item-crud-operations) |
| Job Execution | [COMMON-CORE.md § Job Execution](../../../common/COMMON-CORE.md#job-execution) ||
| Capacity Management | [COMMON-CORE.md § Capacity Management](../../../common/COMMON-CORE.md#capacity-management) ||
| Gotchas & Troubleshooting | [COMMON-CORE.md § Gotchas & Troubleshooting](../../../common/COMMON-CORE.md#gotchas--troubleshooting) ||
| Best Practices | [COMMON-CORE.md § Best Practices](../../../common/COMMON-CORE.md#best-practices) ||
| Tool Selection Rationale | [COMMON-CLI.md § Tool Selection Rationale](../../../common/COMMON-CLI.md#tool-selection-rationale) ||
| Authentication Recipes | [COMMON-CLI.md § Authentication Recipes](../../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows and token acquisition |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource https://api.fabric.microsoft.com`** or `az rest` fails |
| Pagination Pattern | [COMMON-CLI.md § Pagination Pattern](../../../common/COMMON-CLI.md#pagination-pattern) ||
| Long-Running Operations (LRO) Pattern | [COMMON-CLI.md § Long-Running Operations (LRO) Pattern](../../../common/COMMON-CLI.md#long-running-operations-lro-pattern) ||
| OneLake Data Access via `curl` | [COMMON-CLI.md § OneLake Data Access via curl](../../../common/COMMON-CLI.md#onelake-data-access-via-curl) | Use `curl` not `az rest` (different token audience) |
| SQL / TDS Data-Plane Access | [COMMON-CLI.md § SQL / TDS Data-Plane Access](../../../common/COMMON-CLI.md#sql--tds-data-plane-access) ||
| Job Execution (CLI) | [COMMON-CLI.md § Job Execution](../../../common/COMMON-CLI.md#job-execution) ||
| Job Scheduling | [COMMON-CLI.md § Job Scheduling](../../../common/COMMON-CLI.md#job-scheduling) | URL is `/jobs/{jobType}/schedules`; `endDateTime` required |
| OneLake Shortcuts | [COMMON-CLI.md § OneLake Shortcuts](../../../common/COMMON-CLI.md#onelake-shortcuts) ||
| Capacity Management (CLI) | [COMMON-CLI.md § Capacity Management](../../../common/COMMON-CLI.md#capacity-management) ||
| Composite Recipes | [COMMON-CLI.md § Composite Recipes](../../../common/COMMON-CLI.md#composite-recipes) ||
| Gotchas & Troubleshooting (CLI-Specific) | [COMMON-CLI.md § Gotchas & Troubleshooting (CLI-Specific)](../../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | `az rest` audience, shell escaping, token expiry |
| Quick Reference: `az rest` Template | [COMMON-CLI.md § Quick Reference: az rest Template](../../../common/COMMON-CLI.md#quick-reference-az-rest-template) ||
| Quick Reference: Token Audience / CLI Tool Matrix | [COMMON-CLI.md § Quick Reference: Token Audience ↔ CLI Tool Matrix](../../../common/COMMON-CLI.md#quick-reference-token-audience--cli-tool-matrix) | Which `--resource` + tool for each service |
| Relationship to SPARK-CONSUMPTION-CORE.md | [SPARK-AUTHORING-CORE.md § Relationship to SPARK-CONSUMPTION-CORE.md](../../../common/SPARK-AUTHORING-CORE.md#relationship-to-spark-consumption-coremd) ||
| Data Engineering Authoring Capability Matrix | [SPARK-AUTHORING-CORE.md § Data Engineering Authoring Capability Matrix](../../../common/SPARK-AUTHORING-CORE.md#data-engineering-authoring-capability-matrix) ||
| Lakehouse Management | [SPARK-AUTHORING-CORE.md § Lakehouse Management](../../../common/SPARK-AUTHORING-CORE.md#lakehouse-management) ||
| Notebook Management | [SPARK-AUTHORING-CORE.md § Notebook Management](../../../common/SPARK-AUTHORING-CORE.md#notebook-management) ||
| Notebook Execution & Job Management | [SPARK-AUTHORING-CORE.md § Notebook Execution & Job Management](../../../common/SPARK-AUTHORING-CORE.md#notebook-execution--job-management) ||
| CI/CD & Automation Patterns | [SPARK-AUTHORING-CORE.md § CI/CD & Automation Patterns](../../../common/SPARK-AUTHORING-CORE.md#cicd--automation-patterns) ||
| Infrastructure-as-Code | [SPARK-AUTHORING-CORE.md § Infrastructure-as-Code](../../../common/SPARK-AUTHORING-CORE.md#infrastructure-as-code) ||
| Performance Optimization & Resource Management | [SPARK-AUTHORING-CORE.md § Performance Optimization & Resource Management](../../../common/SPARK-AUTHORING-CORE.md#performance-optimization--resource-management) ||
| Runtime 2.0 Performance Features | [data-engineering-patterns.md § Runtime 2.0 Performance Features](authoring/resources/data-engineering-patterns.md#runtime-20-performance-features-spark-41-delta-42) | NEE, Efficient Scaledown, Liquid Clustering, Spark 4.1 |
| Authoring Gotchas and Troubleshooting | [SPARK-AUTHORING-CORE.md § Authoring Gotchas and Troubleshooting](../../../common/SPARK-AUTHORING-CORE.md#authoring-gotchas-and-troubleshooting) ||
| Quick Reference: Authoring Decision Guide | [SPARK-AUTHORING-CORE.md § Quick Reference: Authoring Decision Guide](../../../common/SPARK-AUTHORING-CORE.md#quick-reference-authoring-decision-guide) ||
| Recommended Patterns (Data Engineering) |[data-engineering-patterns.md § Recommended patterns](authoring/resources/data-engineering-patterns.md#recommended-patterns) ||
| Data Ingestion Principles | [data-engineering-patterns.md § Data Ingestion Principles](authoring/resources/data-engineering-patterns.md#data-ingestion-principles) ||
| Transformation Patterns | [data-engineering-patterns.md § Transformation Patterns](authoring/resources/data-engineering-patterns.md#transformation-patterns) ||
| Delta Lake Best Practices | [data-engineering-patterns.md § Delta Lake Best Practices](authoring/resources/data-engineering-patterns.md#delta-lake-best-practices) ||
| Quality Assurance Strategies | [data-engineering-patterns.md § Quality Assurance Strategies](authoring/resources/data-engineering-patterns.md#quality-assurance-strategies) ||
| Recommended Patterns (Development Workflow) | [development-workflow.md § Recommended patterns](authoring/resources/development-workflow.md#recommended-patterns) ||
| Notebook Lifecycle | [development-workflow.md § Notebook Lifecycle](authoring/resources/development-workflow.md#notebook-lifecycle) ||
| Parameterization Patterns | [development-workflow.md § Parameterization Patterns](authoring/resources/development-workflow.md#parameterization-patterns) ||
| Variable Library (notebook + pipeline usage) | [development-workflow.md § Method 4: Variable Library](authoring/resources/development-workflow.md#parameterization-patterns) | `getLibrary()` + dot notation in notebooks; `libraryVariables` + `@pipeline().libraryVariables` in pipelines |
| Variable Library Definition | [ITEM-DEFINITIONS-CORE.md § VariableLibrary](../../../common/ITEM-DEFINITIONS-CORE.md#variablelibrary) | Definition parts, decoded content, types, pipeline mappings, gotchas |
| Local Testing Strategy | [development-workflow.md § Local Testing Strategy](authoring/resources/development-workflow.md#local-testing-strategy) ||
| Debugging Patterns | [development-workflow.md § Debugging Patterns](authoring/resources/development-workflow.md#debugging-patterns) ||
| Recommended Patterns (Infrastructure) | [infrastructure-orchestration.md § Recommended patterns](authoring/resources/infrastructure-orchestration.md#recommended-patterns) ||
| Materialized Lake View patterns | [materialized-lake-view-patterns.md § Recommended patterns](authoring/resources/materialized-lake-view-patterns.md#recommended-patterns) | Spark Lakehouse authoring guidance for MLV design (when to use MLVs, layering patterns) |
| MLV incremental refresh patterns | [mlv-incremental-refresh-patterns.md](authoring/resources/mlv-incremental-refresh-patterns.md) | Read for IR-targeted creation, REFRESH_HINT output-key selection/review, refresh-readiness analysis, and safe rewrites |
| MLV schedule & job management | [the `mlv` mode](mlv.md) | Route here when user asks to schedule, trigger, monitor, or cancel MLV refreshes (not authoring) |
| Workspace Provisioning Principles | [infrastructure-orchestration.md § Workspace Provisioning Principles](authoring/resources/infrastructure-orchestration.md#workspace-provisioning-principles) ||
| Lakehouse Configuration Guidance | [infrastructure-orchestration.md § Lakehouse Configuration Guidance](authoring/resources/infrastructure-orchestration.md#lakehouse-configuration-guidance) ||
| Pipeline Design Patterns | [infrastructure-orchestration.md § Pipeline Design Patterns](authoring/resources/infrastructure-orchestration.md#pipeline-design-patterns) ||
| CI/CD Integration Strategy | [infrastructure-orchestration.md § CI/CD Integration Strategy](authoring/resources/infrastructure-orchestration.md#cicd-integration-strategy) ||
| Notebook API — Which Endpoint to Use | [notebook-api-operations.md § Quick Decision](authoring/resources/notebook-api-operations.md#quick-decision-which-endpoint-to-use) | **Start here for remote notebook edits** — getDefinition vs updateDefinition |
| Notebook Modification Workflow | [notebook-api-operations.md § Workflow](authoring/resources/notebook-api-operations.md#workflow-get--decode--modify--encode--upload--verify) | Five-step flow: retrieve, decode, modify, encode, upload |
| Notebook Orchestration (parallel + DAG) | [notebook-api-operations.md § Notebook Orchestration](authoring/resources/notebook-api-operations.md#notebook-orchestration--parallel-run--dag-dependencies) | `notebookutils.notebook.runMultiple(DAG)` for parallel runs and run-order dependencies (fan-in/fan-out); use instead of hand-rolled threads |
| Notebook API Error Reference | [notebook-api-operations.md § Error Reference](authoring/resources/notebook-api-operations.md#error-reference) | 411, 400 (updateMetadata), 401, 403 explained |
| Notebook API Gotchas | [notebook-api-operations.md § Gotchas](authoring/resources/notebook-api-operations.md#gotchas) | `/result` suffix, empty body, `\n` per-line rule, `format=ipynb` |
| Default Lakehouse Binding | [notebook-api-operations.md § Default Lakehouse Binding](authoring/resources/notebook-api-operations.md#default-lakehouse-binding) | `.ipynb` metadata vs `.py` `# METADATA` block; discover IDs dynamically |
| Public URL Data Ingestion | [notebook-api-operations.md § Public URL Data Ingestion](authoring/resources/notebook-api-operations.md#public-url-data-ingestion-spark) | Use real source URL, stage into `Files/`, then read with Spark |
| getDefinition (read notebook content) | [notebook-api-operations.md § Step 1 — Retrieve Notebook Content](authoring/resources/notebook-api-operations.md#step-1--retrieve-notebook-content-getdefinition) | LRO flow, `?format=ipynb`, empty body (`--body '{}'`) requirement |
| Decode Base64 Notebook Payload | [notebook-api-operations.md § Step 2 — Decode the Notebook Content](authoring/resources/notebook-api-operations.md#step-2--decode-the-notebook-content) | Extract payload, base64 decode, ipynb JSON structure |
| Modify Notebook Cells | [notebook-api-operations.md § Step 3 — Modify the Notebook Content](authoring/resources/notebook-api-operations.md#step-3--modify-the-notebook-content) | Find cell, insert/replace lines, `\n` per-line rule |
| updateDefinition (write notebook content) | [notebook-api-operations.md § Step 4 — Re-encode and Upload](authoring/resources/notebook-api-operations.md#step-4--re-encode-and-upload-updatedefinition) | Re-encode, upload, LRO poll, updateMetadata flag pitfall |
| Verify Notebook Update (Optional) | [notebook-api-operations.md § Step 5 — Verify the Update](authoring/resources/notebook-api-operations.md#step-5--verify-the-update) | Skip unless you suspect a silent failure — `Succeeded` from updateDefinition is sufficient (see Rule 2) |
| Notebook API Error Reference | [notebook-api-operations.md § Error Reference](authoring/resources/notebook-api-operations.md#error-reference) | 411, 400 (updateMetadata), 401, 403 explained |
| Notebook API End-to-End Script | [notebook-api-operations.md § Complete End-to-End Script](authoring/resources/notebook-api-operations.md#complete-end-to-end-script) | Full bash: get → decode → modify → encode → update → verify |
| Quick Start Examples | [SKILL.md § Quick Start Examples](#quick-start-examples) | Minimal examples for common operations |
| **— Notebook Code Authoring (shared modules) —** | | |
| Notebook Authoring Core | [SPARK-NOTEBOOK-AUTHORING-CORE.md](../../../common/SPARK-NOTEBOOK-AUTHORING-CORE.md) | **READ FIRST for notebook code tasks** — fundamentals, code gen approach, module index |

---

## Must/Prefer/Avoid

### MUST DO
- **Check for recent jobs BEFORE creating new notebook runs** — Query job instances from last 5 minutes; if recent job exists, monitor it instead of creating duplicate
- **Capture job instance ID immediately after POST** — Store job ID before any other operations to enable proper monitoring
- **Verify workspace capacity assignment** before operations — Workspace must have capacity assigned and active
- **When user provides a public data URL, follow the Public URL Data Ingestion policy** — keep detailed behavior in the linked resource section to avoid drift/duplication
- **Format notebook cells correctly** — Each line in cell source array MUST end with `\n` to prevent code merging
- **Use correct Lakehouse Livy session body format** — Send a FLAT JSON with `name`, `driverMemory`, `driverCores`, `executorMemory`, `executorCores`. Do NOT wrap in `{"payload": ...}` or send only `{"kind": "pyspark"}` — that causes HTTP 500. Use valid memory values (28g, 56g, 112g, 224g). See Create Lakehouse Livy Session example below and SPARK-CONSUMPTION-CORE.md.
- **Bound live MLV Livy execution end to end** — Use one elapsed-time deadline of at most 12 minutes across session readiness and all create/readback statements. Use short one-shot requests with fixed sleeps; stop on terminal states or the deadline and report the last state. Never leave a background job or foreground watcher running.

### PREFER
- **Poll notebook job status with proper intervals** — 10-30 seconds between polls; timeout after reasonable duration (e.g., 30 minutes)
- **Check job history when POST response is unreadable** — If POST returns "No Content" or unreadable response, query recent jobs (last 1 minute) before retrying
- **Use Starter Pool for development** — Development/testing workloads should use `useStarterPool: true`
- **Use Workspace Pool for production** — Production workloads need consistent performance with `useWorkspacePool: true`
- **Enable lakehouse schemas** during creation — Set `creationPayload.enableSchemas: true` for better table organization
- **Implement idempotency checks** — Prevent duplicate operations by checking existing state first

### AVOID
- **Never retry POST with same parameters** — If you have a job ID, only use GET to check status; don't create duplicate job instances
- **Don't skip capacity verification** — Operations will fail if workspace capacity is paused or unassigned
- **Avoid immediate POST retries on failures** — Check for existing/active jobs first to prevent duplicates
- **Don't create new runs if monitoring existing job** — One job at a time; wait for completion before submitting new runs
- **Don't hardcode workspace/lakehouse IDs** — Discover dynamically via item listing or catalog search APIs
- **Own `%%sql` notebook cells here, do not defer to `sqldw-cli`** — a request to "write a %%sql cell" (or any notebook magic cell) is notebook-cell authoring even when the cell queries a lakehouse table. Only route to `sqldw-cli` when the user wants a plain T-SQL query executed against a SQL endpoint, not a notebook cell.
- **Own "run/execute the notebook named X" here** — running a Fabric notebook by name is notebook execution via `POST .../items/{notebookId}/jobs/instances?jobType=RunNotebook`; never invent a `/jobs/RunNotebook/instances` path. This belongs to authoring mode; do not defer to `consumption`, which is only for ad-hoc Livy session code execution.
- **Do NOT use Lakehouse Livy sessions to run a Fabric notebook** — Lakehouse Livy sessions (the public Livy API) are for ad-hoc interactive Spark code execution. To run a notebook as a job, use the Jobs API (`RunNotebook`) which creates a Notebook Spark session internally. See SPARK-AUTHORING-CORE.md § Notebook Execution & Job Management
- **Do NOT schedule MLV refreshes from notebooks** — If the user asks to "schedule MLV refresh", route to [the `mlv` mode](mlv.md) which uses the REST API. Notebook-based `REFRESH MATERIALIZED LAKE VIEW ... FULL` is for one-time manual refresh only, not recurring schedules.
- **Preserve the IR authoring contract** — for IR-targeted MLV creation or edits,
  read both MLV resources linked below. Use the user's output-key knowledge,
  an established contract, or optional validation to identify hint columns.
  Offer Validate or Skip; always ask the user to review/approve selected keys,
  even after successful validation. If verification is unavailable, report it
  and ask the user to provide unique output column(s). Do not deploy a guessed
  key or treat skipped checks as successful validation.
- **Do not use CREATE as an incremental refresh trigger** — CREATE and CREATE OR
  REPLACE perform Full materialization, with or without REFRESH_HINT. Subsequent
  eligible refreshes can be incremental. A hint does not prevent schema-change
  Full fallback. Do not silently switch to PySpark decorators when IR is required.

---


## RULES — Read these first, follow them always

> **Rule 1 — Validate prerequisites before operations.**
> Verify workspace has capacity assigned (see COMMON-CORE.md Create Workspace and Capacity Management) and resource IDs exist before attempting operations.
>
> **Rule 2 — Trust updateDefinition success.**
> A `Succeeded` poll result from `updateDefinition` is sufficient confirmation that content and lakehouse bindings persisted. Do NOT call `getDefinition` after every upload — it is an async LRO that adds significant latency. Only use `getDefinition` for its intended purpose: reading current notebook content before making modifications.
>
> **Rule 3 — Prevent duplicate jobs and monitor execution properly.**
> Before submitting new notebook run, ALWAYS check for recent job instances first (last 5 minutes). If recent job exists, monitor it instead of creating duplicate. After submission, capture job instance ID immediately and poll status - never retry POST. See SPARK-AUTHORING-CORE.md Job Monitoring for patterns.
>
> **Rule 4 — For notebook code authoring, MUST follow SPARK-NOTEBOOK-AUTHORING-CORE.md.**
> When writing code inside notebook cells, MUST read [SPARK-NOTEBOOK-AUTHORING-CORE.md](../../../common/SPARK-NOTEBOOK-AUTHORING-CORE.md) first — it defines the code generation approach, rules, and a Module Index linking to detailed guides (lakehouse paths, connections, context, orchestration, etc.). Use the Spark-specific resources in this skill ([data-engineering-patterns.md](authoring/resources/data-engineering-patterns.md), [development-workflow.md](authoring/resources/development-workflow.md)) for Spark-only implementation details. When the task is about Materialized Lake Views, read [materialized-lake-view-patterns.md](authoring/resources/materialized-lake-view-patterns.md) for authoring/design guidance and [mlv-incremental-refresh-patterns.md](authoring/resources/mlv-incremental-refresh-patterns.md) for refresh-readiness analysis.

---

## Notebook Codegen Quick Rules

Quick reference for common notebook-authoring tasks. The shared `common/notebook-authoring/` core (see Rule 4 / [SPARK-NOTEBOOK-AUTHORING-CORE.md](../../../common/SPARK-NOTEBOOK-AUTHORING-CORE.md)) is authoritative; if these ever differ, follow the common core.

| User asks for | Required output pattern |
|---|---|
| `%%sql` / cross-workspace lakehouse query cell | Return a Fabric notebook `%%sql` cell with the four-part backtick-qualified name `` `workspace`.`lakehouse`.`schema`.`table` ``. The workspace belongs in the SQL identifier, not only in an attachment note. This is notebook authoring, not interactive Spark consumption. |
| Non-default lakehouse ABFSS path | Build `abfss://{workspaceId}@{endpoint}/{lakehouseId}/Tables/{schema}/{table}` with `notebookutils.conf.get("trident.onelake.endpoint")`; do not hardcode `onelake.dfs.fabric.microsoft.com`. |
| Large cross-lakehouse file copy | Use `notebookutils.fs.fastcp(...)` with ABFSS source and destination paths. `fs.cp(...)` is not the fastest available method for this request. |
| Workspace ID plus lakehouse name | Generate notebook code that calls `/v1/workspaces/{workspaceId}/lakehouses` with `notebookutils.credentials.getToken("pbi")`, matches the exact `displayName`, rejects zero or multiple matches, and builds the ABFSS URI from the returned ID. Never return a portal lookup, unresolved placeholder, or mixed ID/name path. |
| Pipeline context detection | Use `notebookutils.runtime.context`; include `isForPipeline = context["isForPipeline"]` and read `context["currentWorkspaceId"]`. |
| Built-in notebook resource files with Spark | Use `notebookutils.nbResPath`, `builtin/`, and the `file:` prefix: `spark.read.json(f"file:{notebookutils.nbResPath}/builtin/config.json")`. Spark and `notebookutils.fs` require `file:` for resource-folder local paths. |
| Fabric connections | Use `notebookutils.connections.getCredential("{connectionId}")` directly and show a compact code sample. Do not web-search; keep the answer under the tool/turn budget. |

### Minimal snippets

```python
# Pipeline context
context = notebookutils.runtime.context
isForPipeline = context["isForPipeline"]
workspace_id = context["currentWorkspaceId"]
print(f"isForPipeline={isForPipeline}, workspace_id={workspace_id}")
```

```python
# Spark read from notebook built-in resources
config_df = spark.read.option("multiline", "true").json(
    f"file:{notebookutils.nbResPath}/builtin/config.json"
)
display(config_df)
```

```python
# PostgreSQL through a Fabric connection (fill in connectionId and host/db)
import psycopg2

credential = notebookutils.connections.getCredential("{connectionId}")
conn = psycopg2.connect(
    host="<postgres-host>",
    database="<database>",
    user=credential["username"],
    password=credential["password"],
)
```

---

## Quick Start Examples

For detailed patterns, authentication, and comprehensive API usage, see:
- **COMMON-CORE.md** — Fabric REST API patterns, authentication, item discovery
- **COMMON-CLI.md** — `az rest` usage, environment detection, token acquisition
- **SPARK-AUTHORING-CORE.md** — Notebook deployment, lakehouse creation, job execution

Below are minimal quick-start examples. **Always reference the COMMON-* files for production use.**

### Create Workspace & Lakehouse
```bash
# See COMMON-CORE.md Environment URLs and SPARK-AUTHORING-CORE.md for full patterns
cat > /tmp/body.json << 'EOF'
{"displayName": "DataEng-Dev"}
EOF
workspace_id=$(az rest --method post --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --body @/tmp/body.json --query "id" --output tsv)

cat > /tmp/body.json << 'EOF'
{"displayName": "DevLakehouse", "type": "Lakehouse", "creationPayload": {"enableSchemas": true}}
EOF
lakehouse_id=$(az rest --method post --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$workspace_id/items" \
  --body @/tmp/body.json --query "id" --output tsv)
```

### Organize Lakehouse Tables with Schemas
```python
# See SPARK-AUTHORING-CORE.md Lakehouse Schema Organization for table organization patterns
#
# IMPORTANT: `CREATE SCHEMA` is only supported on schema-enabled lakehouses. On a
# lakehouse created WITHOUT `enableSchemas`, it fails with
# "Feature not supported on Apache Spark in Microsoft Fabric". Always detect schema
# support first, then branch: create schemas only when enabled, otherwise skip.
# Schema names are configurable. If your workspace standard is `raw`/`curated`
# instead of `bronze`/`silver`/`gold`, substitute those names consistently.
import uuid

def lakehouse_is_schema_enabled():
    # Probe schema support by attempting CREATE SCHEMA and catching the
    # platform-blocked error. Use a unique probe schema name to avoid
    # accidentally dropping a real pre-existing schema.
    probe = f"_schema_probe_{uuid.uuid4().hex}"
    try:
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {probe}")
        spark.sql(f"DROP SCHEMA IF EXISTS {probe}")
        return True
    except Exception as e:
        if "Feature not supported on Apache Spark in Microsoft Fabric" in str(e):
            return False
        raise

if lakehouse_is_schema_enabled():
    # Schema-enabled: create medallion schemas and write tables as `schema.table`.
    spark.sql("CREATE SCHEMA IF NOT EXISTS bronze")
    spark.sql("CREATE SCHEMA IF NOT EXISTS silver")
    spark.sql("CREATE SCHEMA IF NOT EXISTS gold")
else:
    # Not schema-enabled: skip CREATE SCHEMA (unsupported). Organize tables by name
    # prefix instead (e.g. `bronze_orders` / `raw_orders`, `silver_orders` /
    # `curated_orders`), or recreate the lakehouse with
    # `creationPayload.enableSchemas: true` if schemas are required.
    print("Lakehouse is not schema-enabled; skipping schema creation and using name prefixes.")
```

### Create and Refresh a Materialized Lake View (MLV)
```sql
-- See authoring/resources/materialized-lake-view-patterns.md for design guidance
-- and authoring/resources/mlv-incremental-refresh-patterns.md for refresh-readiness review.

-- Bronze/Silver/Gold schemas in a Lakehouse with schemas enabled
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- A simple append-only Silver MLV with data quality constraints.
-- For updates/deletes, read the IR resource for REFRESH_HINT syntax and
-- optional validation plus mandatory user review of the unique output key.
--
-- Prerequisite for incremental refresh: enable Change Data Feed (CDF) on every
-- source table the MLV reads from. Without CDF, optimal refresh can only choose
-- between no refresh (sources unchanged) and full refresh — never incremental.
-- See authoring/resources/mlv-incremental-refresh-patterns.md.
ALTER TABLE bronze.orders_raw SET TBLPROPERTIES (delta.enableChangeDataFeed = true);

CREATE OR REPLACE MATERIALIZED LAKE VIEW silver.orders_clean
(
    CONSTRAINT valid_order_id CHECK (order_id IS NOT NULL) ON MISMATCH DROP
)
AS
SELECT
  order_id,
  customer_id,
  CAST(order_ts AS TIMESTAMP) AS order_ts,
  amount
FROM bronze.orders_raw;

-- CREATE and CREATE OR REPLACE perform Full materialization, with or without
-- a refresh hint. Only subsequent refreshes of the existing MLV can be IR.
-- Routine refresh is handled by the lakehouse Materialized lake views → Manage
-- schedule/lineage view; don't orchestrate from notebooks. The SQL form below is
-- documented only for forcing a one-time FULL recompute (troubleshooting / after
-- a correction). There is no documented SQL form for triggering incremental refresh.
REFRESH MATERIALIZED LAKE VIEW silver.orders_clean FULL;
```

### Create Lakehouse Livy Session
```bash
# See SPARK-CONSUMPTION-CORE.md for Lakehouse Livy session configuration and management
# IMPORTANT: Body MUST be flat JSON with memory/cores — do NOT wrap in {"payload": ...}
cat > /tmp/body.json << 'EOF'
{"name": "dev-session", "driverMemory": "56g", "driverCores": 8, "executorMemory": "56g", "executorCores": 8, "conf": {"spark.dynamicAllocation.enabled": "true", "spark.fabric.pool.name": "Starter Pool"}}
EOF
az rest --method post --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$workspace_id/lakehouses/$lakehouse_id/livyapi/versions/2023-12-01/sessions" \
  --body @/tmp/body.json
```

> **Lakehouse Livy Session Body — Common Mistakes**
> - ❌ `{"payload": {"kind": "pyspark"}}` → HTTP 500 (wrong wrapper, missing required fields)
> - ❌ `{"kind": "pyspark"}` → HTTP 500 (missing `driverMemory`, `executorMemory`, etc.)
> - ✅ Flat JSON with `name`, `driverMemory`, `driverCores`, `executorMemory`, `executorCores` (and optionally `conf` with Starter Pool)

### Spark Performance Configs
**For detailed workload-specific configurations, see data-engineering-patterns.md Delta Lake Best Practices.**

Quick reference:
```python
# Write-heavy (Bronze): Disable V-Order, enable autoCompact
# Balanced (Silver): Enable V-Order, adaptive execution  
# Read-heavy (Gold): Vectorized reads, optimal parallelism
# See data-engineering-patterns.md for complete config tables
```

---

**Focus**: Essential CLI patterns for Spark/data engineering development and notebook code authoring, with intelligent routing to specialized resources. For comprehensive patterns, always reference COMMON-* files and resource documents.
