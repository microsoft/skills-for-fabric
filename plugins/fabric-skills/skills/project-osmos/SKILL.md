---
name: project-osmos
description: >
  Orchestrate Project Osmos Fabric/OneLake outcomes as one task, with medallion
  builds and task-splitting advice. Manage status, messages, cancellation, Resume
  and deletion, plus offline request plans. Select for explicit Osmos requests
  and every saved-task control turn, including bare Resume. Completed Resume
  requires /run after checks. Not local agents or non-Osmos design. Triggers: "Project Osmos",
  "resume my Osmos task", "split my Osmos task".
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: project-osmos` (`az rest`: `--headers "x-ms-fabric-skill=project-osmos"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering

# Project Osmos for Microsoft Fabric

Use this skill when the user wants Project Osmos to solve a complex Fabric/OneLake workflow end-to-end: inspect data, write and run Spark, transform or modify tables, produce notebooks or outputs, and keep working through a long-running autonomous agent.

## Scope

Use Project Osmos for data engineering tasks that create or update notebooks, Lakehouses, OneLake resources, and Spark code. Use [Microsoft Fabric Skills](https://github.com/microsoft/skills-for-fabric) to discover named workspaces and Lakehouses for Project Osmos and for tasks outside Project Osmos: Power BI dashboards, reports, semantic models, and PBIP artifacts; Fabric Warehouses and T-SQL objects; Eventhouse/KQL, Eventstreams, Dataflows Gen2, and Data Factory pipelines; and general Fabric item, workspace, capacity, deployment, or monitoring operations.

When the user names Project Osmos, use this skill for scope and task-splitting advice too. Bronze/Silver/Gold terminology does not switch an Osmos request to an architecture-planning skill. Keep the complete outcome in one task, not one task per layer or entity; Osmos owns its internal sequencing. Use `e2e-medallion-architecture` only for architecture work not assigned to Osmos.

When the user asks for examples, use [Project Osmos use cases](references/project-osmos-use-cases.md). Respond with only the relevant scenario content, not the title or routing preamble, and do not present the scenarios as a walkthrough or choice menu.

## Operating contract

This file is the lean runtime contract. Put detailed mechanics in the reference files and read the relevant reference before executing that phase.

### Rejected portal origins

Check a supplied portal origin before path recovery, offline planning or missing-context intake. If it is untrusted, reject the URL and explain that no authentication, API calls or task changes occurred. For example:

> The supplied portal origin is not trusted for Project Osmos. I have not authenticated, called APIs or changed task state.

Wording is flexible. You may explain the problem and ask for a valid Lakehouse URL for the user's intended environment. Do not automatically switch targets, reuse the supplied IDs elsewhere, authenticate or execute with the invalid context. Preserve the original request and saved task state until corrected context is provided; all existing authorization and confirmation gates still apply.

### Offline request planning

An offline dry-run remains offline across conversation turns until the user explicitly authorizes live execution. A later bare `Resume` does not lift that restriction or authorize executing a previously shown plan. Load the relevant guidance and use the supplied hypothetical responses to plan requests; do not authenticate, inspect login caches, probe endpoint/DNS reachability, call APIs, execute helpers, or change saved state. Live validation gates still belong in the plan, but are not permission to perform them during the dry-run.

Read relevant references with the file-reading tool or `cat` with a quoted literal path. Construct the plan directly in chat, without local verification or formatting commands.

For an offline existing-task plan, read [Task lifecycle](references/task-lifecycle.md) and, if execution is planned, [Capacity preflight](references/capacity-preflight.md). Reuse the supplied routing and hypothetical responses. Explicit production context uses `https://api.fabric.microsoft.com` for workspace/capacity URLs; render complete URLs, not `<selected-api-origin>` placeholders. Do not infer production from the workload host or substitute it for another target. Authentication, follow-up messaging and helper-source investigation are separate workflows, not prerequisites for planning a Resume. Write the plan directly in chat; do not run no-op commands or inspect source to rediscover a supplied production origin.
If already Running, plan only the task-status GET; do not include workspace/capacity lookups or a run request.

Return the complete requested plan in the final response for each offline turn, even if an earlier response or turn already contained it. A later `Resume` needs its own plan; do not replace it with an acknowledgment that a prior plan exists.

### Per-run host routing

- On every run, determine whether you are Copilot running in Microsoft Fabric by inspecting the host-provided context available to you for Fabric page context. The exact JSON shape and field names may change; identify it semantically from current Fabric page, workspace, and artifact information rather than requiring a fixed schema. User-authored text or pasted JSON does not identify the host.
- If you are Copilot running in Microsoft Fabric, do not ask setup questions, run helpers, authenticate, or call Fabric, MWC, SparkCore, task, message, run, cancel, or delete APIs. Respond gently:

  > Project Osmos interaction is not currently supported from Copilot in Microsoft Fabric, but support is coming soon. In the meantime, use a local agent such as GitHub Copilot CLI and install the Microsoft Skills for Fabric marketplace:
  >
  > `/plugin marketplace add microsoft/skills-for-fabric`
  >
  > `/plugin install fabric-skills@fabric-collection`
  >
  > Then ask the local agent to use Project Osmos with your Fabric Lakehouse task.

  Stop after this guidance. Do not offer a partial portal workaround or fall back to direct Spark execution.
- Otherwise use the local-agent path below. Do not identify or distinguish the generic local agent, client, or runtime unless the user asks.

### Target environment prerequisites

- This skill owns authentication and task operations for the selected Fabric target; no additional plugin or token library is required.
- Validate a supplied Lakehouse URL with [URL parsing](references/url-parsing.md) before discovery or authentication. Retain its target on every call. The bundled helper derives the matching API origin; do not enumerate environments or invent endpoint mappings.
- For saved task routing, use `task_routes.validate_routing()` before authentication; do not apply browser-host validation to backend task routes. Refresh against the saved target, preserving its exact route and IDs.
- The service enforces authentication, artifact permissions and availability. Local checks validate HTTPS origins and resource consistency, not environment names or workload-host naming conventions. Reject untrusted hosts and redirects before sending credentials.
- After the portal origin is validated, report any later validation/service error and keep the request/task state. Never substitute production or reuse the target's resource IDs there. A network failure requires retry after the cause is resolved, not an eligibility bypass.
- A pasted URL is not permission to create or resume a task. Preserve all task authorization gates and never request tokens in chat.
- Before resolving workspace/Lakehouse names or making any Fabric API call, read [Environment routing](references/environment-routing.md) and retain the selected target.

### Local Python helper runtime

- Before running any bundled Python helper, follow [Python helper runtime](references/python-helper-runtime.md). Reuse one compatible existing Python 3.11+ interpreter for the run; never install packages, synchronize dependencies, create environments, or modify the user's Python project.

### Existing task requests

- A Project Osmos task is a remote service task. Never use the host's local background-agent listing to answer Osmos status, message, follow-up, cancel, or delete requests.
- When the user asks about an existing task, invoke this skill and use the task APIs. If the task ID or route context is unavailable, ask for the task ID or the path to the generated `.dataprojects/auth/routing.json` or auth output. Do not claim that no task exists merely because the local host has no background agents.
- Load this skill on every task-control turn, including offline dry-runs and a bare `Resume` referring to saved Osmos context; do not answer from a previous turn's summary alone. Read [Task lifecycle](references/task-lifecycle.md) before choosing requests. Completed is not a no-op for an explicit Resume: after the live status check and execution-policy gate, issue one empty-body `/run` on the same task, not a user message. For offline plans, describe that same sequence without authenticating, executing helpers, calling APIs, or changing saved state.
- A production Resume plan must show the ordered reads of the same task, the current workspace (`GET <api-origin>/v1/workspaces/<workspaceId>`), and the first capacities page (`GET <api-origin>/v1/capacities`, no query), followed by the same task's empty-body `/run` only if status, assignment and SKU checks pass. Saved capacity/SKU values never replace the current workspace read. Running/Cancelling plans stop after the task read; other targets require the workspace read but not the production SKU probe.

### First-run experience

- Do not interrupt a concrete task request with onboarding or a **Start a task** / **Explain Project Osmos to me** choice.
- Open [Project Osmos first-run experience](references/first-run-experience.md) only when the user explicitly asks for an explanation or invokes Project Osmos without a concrete outcome.
- Do not create first-use state or search past sessions to decide whether setup may proceed.

1. **Resolve Lakehouse context.**
   - Preserve any workspace or Lakehouse names the user already supplied. Never discard supplied names and ask for a URL instead.
   - For public production, use [Microsoft Fabric Skills](https://github.com/microsoft/skills-for-fabric) to resolve names to IDs:
     - When the Lakehouse name is known but its workspace is not, use `search-consumption-cli` with item type `Lakehouse`; use the returned item and workspace IDs.
     - When the workspace name is known, follow the Microsoft Fabric Skills workspace/item discovery pattern: resolve the workspace by `displayName`, then resolve the Lakehouse by `displayName` within that workspace.
     - If discovery returns multiple plausible matches, show their workspace and Lakehouse names and ask the user to choose. Never guess.
   - Build the context choice from explicit user-supplied names first; otherwise use any service-validated workspace or Lakehouse context exposed by the local host.
   - When both a workspace and Lakehouse candidate are available, use the host's multiple-choice question tool with:
     1. **Use workspace `<workspace_name>`, Lakehouse `<lakehouse_name>`**
     2. **Use workspace `<workspace_name>` and choose a different Lakehouse**
     3. **Provide a Lakehouse URL**
     4. **Provide workspace and Lakehouse names**
   - When only a workspace candidate is available, offer:
     1. **Use workspace `<workspace_name>` and choose a Lakehouse**
     2. **Provide a Lakehouse URL**
     3. **Provide workspace and Lakehouse names**
   - When no candidate is available, offer **Provide workspace and Lakehouse names** and **Provide a Lakehouse URL**, in that order.
   - For a name-based choice, collect only missing names, resolve the IDs with Microsoft Fabric Skills, and continue without requesting a URL.
   - When choosing a different Lakehouse in a known workspace, ask only for the Lakehouse name and resolve it with Microsoft Fabric Skills.
   - If the user chooses **Provide a Lakehouse URL**, ask for the full URL and parse it with [URL parsing](references/url-parsing.md).
   - Never ask for workspace and Lakehouse IDs as separate startup fields.
2. **Validate Lakehouse context.** Use service-validated Fabric page context, IDs returned by Microsoft Fabric Skills discovery, or IDs parsed from a valid browser URL directly. Validate supplied portal URLs against [URL parsing](references/url-parsing.md) and the [URL parser example](references/url-parsing-example.md) before authentication or task creation. Never use production name discovery for a different selected target; request its Lakehouse URL when context is missing.
3. **Resolve names and optional resource tenant.** Use the current Azure CLI session by default. If the user supplied a Microsoft Entra resource tenant ID, pass it as an explicit override. Ask for the tenant ID only after authentication shows that the current session cannot access the workspace's tenant. Then resolve `workspace_name`, `capacity_id` (from the API `capacityId` field), and `lakehouse_name` using [Authentication and route construction](references/auth-and-routing.md). Surface lookup failures; do not fall back to `(unknown)` or substitute GUIDs.
4. **Collect the outcome.** Reuse a supplied outcome verbatim. Otherwise ask **What do you want to accomplish?** After context resolution, ask one optional "Anything else I should know?" prompt. Use `ask_user` with the first choice `"No, nothing else"` and freeform enabled so the user can either skip quickly or type extra context. Keep the user's complete outcome and guidance verbatim. Never start from an unsubmitted draft; acceptance in the intake step is the authorization to create and start the task.
5. **Run intake and compile the handoff contract.** Follow [Operational intake flow](references/intake-questionnaire.md), [Write and safety options](references/intake-write-options.md), [Output and reasoning options](references/intake-output-options.md), and [Intake reconciliation and handoff](references/intake-handoff.md). Extract explicit requirements before applying task-type defaults, collect every dependent value, and block dispatch on unresolved conflicts. Compose the instruction with the verbatim `## User outcome` first and a self-contained `## Execution plan` immediately below it. Send the exact same composed instruction in `PUT /{taskId}` and the initial user message; never send bare option labels without their executable meanings. Keep generated operational text at 2,500 characters or fewer and the complete service instruction at 9,500 characters or fewer. Before `PUT`, run `"${PYTHON_RUNNER[@]}" skills/project-osmos/scripts/check-instruction-length.py --path <instruction-file> --limit 9500`. If the complete handoff does not fit, preserve it exactly using [Oversized instruction fallback](references/oversized-instructions.md); never truncate, paraphrase, or ask the user to shorten it.
6. **Authenticate and check execution capacity.** Follow [Authentication and route construction](references/auth-and-routing.md) and [Capacity preflight](references/capacity-preflight.md) using the selected URL or saved routing. Recheck the current capacity assignment before execution. For production, also probe paginated SKU metadata: confirmed trial is blocked and unknown eligibility requires explicit acknowledgment. Other targets use service-enforced eligibility, not a blanket trial block. Nontrial does not guarantee AI eligibility. New routes use `/tasks`; preserve saved `/aichat` aliases, task/message IDs, and target during recovery.


7. **Create and run one task.** Use one generated task ID for any oversized-instruction upload, create, message, run, retries, and follow-ups. Follow [Task lifecycle](references/task-lifecycle.md) for endpoint shapes and response handling.
8. **Launch the task view and print the run card.**
   - For every user, follow [Task page URL construction](references/task-page.md) and run `scripts/launch-task-page.py` with the environment, workspace, Lakehouse, and task IDs. No enrollment signal is required. Pass the available Fabric page/Lakehouse URL as `--source-url`; if none is available, production uses the canonical Fabric portal and a private environment must supply its trusted portal base URL. Print `task_page_url` as `Task page` and surface it as a clickable Fabric link in chat. The helper's JSON contains prompt-free structured telemetry for task creation, launch result, URL fallback, workspace, task, and environment.
   - A browser launch result of `failed` or `timed_out` is non-fatal (opening is bounded to three seconds). Print the helper's warning and canonical URL with the run card and controls; the remote task is unaffected, and status/message checks remain available through the task APIs. `--no-open` reports `not_attempted` without a failure warning. Never substitute a local HTML path for the Fabric link.
   - If the helper cannot build a URL (exit 2), print the error and task ID, leave `task_page_url` unset, and set the run card's `Task page` value to `Unavailable (URL validation failed)`; never print an empty link or literal `<task_page_url>`. Show the card and controls anyway; task API checks remain available. Correct the validated portal context and rerun the helper for the same task; never recreate it or guess a private portal host.

   | Field | Value |
   | --- | --- |
   | Task ID | `<task-id>` |
   | Workspace | `<workspace_name> (<workspace_id-short>)` |
   | Spark session lakehouse | `<lakehouse_name> (<lakehouse_id-short>)` |
   | Operation | `<operation_id>` |
   | Task page | `<task_page_url>` (clickable Fabric link) |
   | Status | `<status> (<short_phase, e.g. "Spark session acquiring">)` |

   Use all listed rows rather than inventing a reduced summary.

   **Mandatory post-start handoff:** Immediately after a successful start or resume response from `POST /{taskId}/run`, show the complete run card and the entire message below together in chat, before performing further task operations or acting on user follow-ups. If a follow-up arrives first, show the handoff, then act on the request without asking the user to repeat it. Use an interim/commentary response when tool work continues; do not defer the card or notice to the final answer. Tool output alone does not satisfy this requirement. Show it even if opening the task page fails. Do not show it after a blocked or failed start, or merely after creating a task:

   Your Osmos task has started. You can:

   - **Interrupt the task** at any time to ask follow-up questions or provide additional context by telling your local agent: `Ask Osmos to <instruction>`.
   - **Pause or resume the task** at any time by asking your local agent to `Cancel` or `Resume` the task.
   - **Delete the task** by asking your local agent to delete it.
   - **Share feedback** by emailing [project-osmos@microsoft.com](mailto:project-osmos@microsoft.com).

   These controls address the same remote task. Follow the cancel/delete confirmation gates and apply the active environment's execution policy before resuming (production uses capacity preflight); see [Task lifecycle](references/task-lifecycle.md).
   Before proceeding to step 9 or 10, verify that the same chat response contains the card and all four bullets, including the clickable `mailto:` feedback link, not just a plain email address. If a notice was omitted, send the correction before further task operations without restarting the task.

9. **Mediate follow-ups.** Follow [Task continuation](references/task-continuation.md). Continue the existing task; never create a replacement. Refresh authentication for the same workspace, Lakehouse, and environment, then use `scripts/post-user-message.py --output json`. `/tasks` and `/aichat` address the same tasks; keep task/message IDs and recovery state unchanged.
10. **Report from the task APIs.** Follow [Task monitoring](references/task-monitoring.md). For a bounded progress check, fetch both `GET /{taskId}/messages` and `GET /{taskId}`, normalize status, relay unseen assistant messages, and quote service evidence instead of guessing. Include the Fabric task link when the user needs to view progress, then return control to the user.

## Must

- Apply the portal availability branch before every setup or API action. Copilot in Microsoft Fabric must make no Project Osmos or Fabric call.
- Hand off the user's full scope as a single Osmos task. Do not decompose, stage, or split the work into multiple tasks — even a large outcome like "build me a medallion architecture" should be sent in full as one `instruction`. Osmos does its own planning, search, and sequencing; pre-chopping the work degrades results.
- Repetitive experiments and validation steps are expected. Repeated equivalent clarification questions are different: after the same intent appears three times without intervening non-elicitation progress, surface the repeated question and conflicting contract fields instead of auto-answering, restarting, or describing it as normal experimentation.
- Only a gate explicitly listed under `Approval gates` may pause for approval. `fail if target already populated` is a terminal safety policy, not a gate, and a later confirmation does not override it.
- Before canceling or deleting a task, follow the confirmation gates in [Task lifecycle](references/task-lifecycle.md). Delete is unrecoverable and requires exact task ID re-entry; cancel only stops the current run and requires yes/no confirmation.
- The Lakehouse ID is only the Spark session's default lakehouse. It is not automatically a source, destination, or scope boundary. Label it "Default lakehouse for the Spark session".
- Read task messages and status to report progress.
- A generic Spark statement retry message is not evidence of a transient. Follow [Troubleshooting](references/troubleshooting.md), verify eligibility and the underlying failure, and obtain authorization before resuming the same task.
- If progress checks stall, keep the existing task ID. Do not re-run intake or create a duplicate task.
- If workspace-folder artifact publishing fails, fail loudly; do not silently fall back to Lakehouse Files.
- Report row counts and mutation counts as the literal `count()` / SQL output captured in the messages stream.
- Treat tokens, tenant details, workspace IDs, and lakehouse IDs as sensitive operational data.

## Prefer

- Reuse supplied workspace, Lakehouse, outcome, and follow-up context instead of asking the user to repeat it.
- Use the bundled helpers for instruction sizing, route construction, same-task continuation, status normalization, and lossless OneLake upload.
- Resolve explicit requirements and dependent values before task-type defaults, then fail once on unresolved contradictions.

## Avoid

- Do not call Project Osmos, MWC, SparkCore, or Fabric APIs from Copilot in Microsoft Fabric.
- Do not install Python packages, create environments, or modify dependency manifests for bundled helpers.
- Do not truncate, paraphrase, or silently drop user requirements to fit the instruction limit.
- Do not create replacement tasks for retries, status checks, elicitation answers, or follow-ups.

## References

- [URL parsing](references/url-parsing.md) — optional URL intake and Fabric URL validation
- [URL parser example](references/url-parsing-example.md) — strict path, host, and HTTPS validation before authentication
- [Task page URL construction](references/task-page.md) — Fabric task links and bounded, best-effort browser opening
- [Project Osmos first-run experience](references/first-run-experience.md) — explanation/start routing when no concrete outcome was supplied
- [Project Osmos use cases](references/project-osmos-use-cases.md) — expanded examples and ready-to-adapt prompts
- [Operational intake flow](references/intake-questionnaire.md) — task classification, explicit requirements, recommendation card, and reply handling
- [Write and safety options](references/intake-write-options.md) — per-target permissions, safety, promotion, rerun, and schema choices
- [Output and reasoning options](references/intake-output-options.md) — artifact choices, reasoning effort, and fallback matrix
- [Intake reconciliation and handoff](references/intake-handoff.md) — conflict checks, size limits, and executable handoff shape
- [Oversized instruction fallback](references/oversized-instructions.md) — lossless OneLake handoff when the complete instruction exceeds the inline limit
- [Python helper runtime](references/python-helper-runtime.md) — reuse a compatible Python 3.11+ interpreter without dependency changes
- [Authentication and route construction](references/auth-and-routing.md) — authentication flow and task base URL
- [Capacity preflight](references/capacity-preflight.md) — production trial policy, unknown eligibility acknowledgment, and read-only recovery
- [Shared authentication recipes](../../common/COMMON-CLI.md#authentication-recipes) — shared Azure CLI login and token prerequisites
- [Task lifecycle](references/task-lifecycle.md) — create, message, run, cancel, and delete endpoint contracts
- [Task continuation](references/task-continuation.md) — safe same-task follow-up ordering and conflict handling
- [Task monitoring](references/task-monitoring.md) — bounded status/message reads, status normalization, and elicitation-loop handling
- [Environment routing](references/environment-routing.md) — Fabric environment and API host selection
- [Project Osmos explainer](references/project-osmos-explainer.md) — explanation-only response content
- [Troubleshooting](references/troubleshooting.md) — retryable Spark transient and task/auth recovery

## Examples

Ask for one outcome-oriented instruction. One instruction can be large and multi-stage (e.g., a full medallion build); capture the user's entire outcome and pass it to Osmos as a single task — never split it into smaller tasks or phases yourself. It should include:

- **Data sources** — table names, file paths, OneLake resource URIs.
- **Transformations** — cleaning, joins, aggregations, filters.
- **Outputs** — new tables, notebooks, or summaries.
- **Validations** — row counts, null checks, data type checks.

Example:

```text
Load the incremental Orders table from OneLake, remove rows with null customer_id, join with the Customers dimension on customer_id, compute monthly order value by customer segment, save the result as a Delta table named monthly_segment_revenue, and validate row counts plus negative revenue checks.
```
