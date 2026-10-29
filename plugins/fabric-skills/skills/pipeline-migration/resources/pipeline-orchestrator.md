# Pipeline Migration Orchestrator — Synapse → Fabric Data Factory

End-to-end workflow for migrating one or more Synapse pipelines to Fabric Data Factory.

---

## Required Inputs

Ask the user for **four things only**. Discover everything else automatically.

**User-provided inputs (4):**

| Input | Source |
|---|---|
| Synapse workspace name | **Ask the user** |
| Fabric workspace name | **Ask the user** |
| Pipeline names to migrate | **Ask the user** — specific names or `*` for all |
| Name suffix (optional) | **Ask the user** — e.g. `_migrated`; leave blank to keep original names |

**Auto-discovered (do not ask):**

| Input | Source |
|---|---|
| Subscription ID | `az account show --query id -o tsv` |
| Resource group | `az synapse workspace show --name <ws> --query resourceGroup -o tsv` |
| Fabric workspace ID | `GET /v1/workspaces` → filter by display name |
| Notebook GUIDs | `GET /v1/workspaces/{wsId}/notebooks` → filter by display name |

**Conditional input — only if `@pipeline().globalParameters.*` is used:**

| Input | Source |
|---|---|
| `VARIABLE_LIBRARY_ID` | Output of Phase 1 (`global-parameters-to-variable-library.md`). Run Phase 1 first, then paste the Variable Library item GUID into the runner before Phase 5 deploy. Leave as `None` when the source pipelines do not reference `@pipeline().globalParameters.*`. |

> **Synapse Studio URL shortcut**: If the user provides a URL like `https://web.azuresynapse.net/en/home?workspace=%2Fsubscriptions%2F{subId}%2FresourceGroups%2F{rg}%2Fproviders%2FMicrosoft.Synapse%2Fworkspaces%2F{wsName}`, extract all three Synapse values automatically.

> **Check login first**: Run `az account show` before acquiring tokens. If it fails, ask the user to run `az login`.

---

## Inline Runner — Notebook-Activity Migration (Phases 0, 4, 5 only)

> **Scope**: This runner covers the prerequisite notebook-GUID lookup (Phase 0), activity transformation for `SynapseNotebook` activities (Phase 4), and Fabric pipeline creation (Phase 5). It does **not** perform:
> - **Phase 1** — Global parameters → Variable Library (requires ARM token; run `global-parameters-to-variable-library.md` first)
> - **Phase 2** — Linked services → Fabric Connections (run `linked-service-to-connection.md` first)
> - **Phase 3** — Dataset inlining (run `dataset-inlining.md` first)
>
> Complete those phases manually before running this script if your pipelines depend on them. For the full orchestrated flow — all five phases in sequence — follow the **Orchestration Flow** section below.

Copilot executes this script inline from the terminal — no saved file needed. Fill in `SYNAPSE_WS`, `FABRIC_WS_NAME`, and `PIPELINES`, then run.

```python
import requests, json, base64, subprocess, re, shutil, time, os
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

# ── Platform detection ─────────────────────────────────────────────────────────
_AZ = "az.cmd" if shutil.which("az.cmd") else "az"

def _az_run(*args):
    return subprocess.run([_AZ, *args], capture_output=True, text=True,
                          check=True).stdout.strip()

# ── Config (Copilot fills from user answers) ───────────────────────────────────
SYNAPSE_WS     = "<synapse-workspace-name>"   # ask user
FABRIC_WS_NAME = "<fabric-workspace-name>"    # ask user
PIPELINES      = ["*"]                         # or ["Pipeline 1", "Pipeline 2"]
NAME_SUFFIX    = ""                            # optional, e.g. "_migrated"

# Variable Library produced by Phase 1 (global-parameters-to-variable-library.md).
# Set this to the item ID printed at the end of Phase 1 to wire up
# @pipeline().libraryVariables.* expressions. Leave as None if the source
# pipelines do not reference @pipeline().globalParameters.*.
VARIABLE_LIBRARY_ID = None                     # e.g. "11111111-2222-3333-4444-555555555555"

# ── Auto-discover subscription and resource group ──────────────────────────────
SUBSCRIPTION   = _az_run("account", "show", "--query", "id", "-o", "tsv")
RESOURCE_GROUP = _az_run("synapse", "workspace", "show",
                          "--name", SYNAPSE_WS, "--query", "resourceGroup", "-o", "tsv")
if not RESOURCE_GROUP:
    RESOURCE_GROUP = _az_run("resource", "list", "--resource-type",
                              "Microsoft.Synapse/workspaces",
                              "--query", f"[?name=='{SYNAPSE_WS}'].resourceGroup | [0]",
                              "-o", "tsv")

# ── Scope note ────────────────────────────────────────────────────────────────
# This inline runner covers Phase 0 (notebook-GUID lookup), Phase 4
# (SynapseNotebook activity transformation), and Phase 5 (Fabric pipeline
# creation). Phases 1–3 (global parameters → Variable Libraries, linked
# services → connections, dataset inlining) must be completed before running.
# For the full five-phase sequence see the Orchestration Flow section below.

# ── Token acquisition ──────────────────────────────────────────────────────────
def get_token(audience):
    return _az_run("account", "get-access-token", "--resource", audience,
                   "--query", "accessToken", "-o", "tsv")

print("Acquiring tokens...", flush=True)
synapse_token = get_token("https://dev.azuresynapse.net")
fabric_token  = get_token("https://api.fabric.microsoft.com")
# ARM token not acquired here — global parameter migration (Phase 1) is a
# prerequisite step; see get_global_parameters() in the full orchestrator.

SYNAPSE_BASE = f"https://{SYNAPSE_WS}.dev.azuresynapse.net"
FABRIC_BASE  = "https://api.fabric.microsoft.com/v1"

# Per-request HTTP timeout as (connect_seconds, read_seconds). Long-running
# migrations should never hang indefinitely on a transient network stall —
# a stuck connect or stuck read both surface as requests.Timeout, which the
# caller can retry or escalate. Override via env vars without editing code.
HTTP_TIMEOUT = (
    float(os.environ.get("FABRIC_HTTP_CONNECT_TIMEOUT", 10)),
    float(os.environ.get("FABRIC_HTTP_READ_TIMEOUT", 60)),
)

def synapse_get(path):
    r = requests.get(f"{SYNAPSE_BASE}{path}",
                     headers={"Authorization": f"Bearer {synapse_token}"},
                     timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()

def synapse_paginate(path):
    """Collect all items from a paginated Synapse list endpoint (`nextLink`).

    Required for workspaces with enough pipelines/datasets/linked services to
    paginate — a bare `synapse_get('/pipelines')` returns only the first page
    and silently migrates an incomplete set (especially when `PIPELINES == ['*']`)."""
    items, url = [], f"{SYNAPSE_BASE}{path}"
    while url:
        r = requests.get(url,
                         headers={"Authorization": f"Bearer {synapse_token}"},
                         timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        items.extend(data.get("value", []))
        url = data.get("nextLink")
    return items

def fabric_get(path):
    r = requests.get(f"{FABRIC_BASE}{path}",
                     headers={"Authorization": f"Bearer {fabric_token}"},
                     timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()

def _next_page_url(url: str, continuation_token: str) -> str:
    """Replace/add `continuationToken` on `url`, preserving any other query params and
    URL-encoding the token value."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k != "continuationToken"]
    query.append(("continuationToken", continuation_token))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def fabric_paginate(path):
    """Collect all items from a paginated Fabric list endpoint (continuationToken)."""
    items, url = [], f"{FABRIC_BASE}{path}"
    while url:
        r = requests.get(url, headers={"Authorization": f"Bearer {fabric_token}"},
                         timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        items.extend(data.get("value", []))
        cont = data.get("continuationToken")
        url = _next_page_url(url, cont) if cont else None
    return items

def fabric_post(path, body):
    r = requests.post(f"{FABRIC_BASE}{path}",
                      headers={"Authorization": f"Bearer {fabric_token}",
                               "Content-Type": "application/json"},
                      json=body, timeout=HTTP_TIMEOUT)
    if r.status_code in (200, 201):
        # Fabric item creation typically returns 201 Created for synchronous success;
        # some endpoints may return 200 OK. Treat both as immediate success.
        # On empty / non-JSON bodies the created resource identity (id) is lost.
        # The downstream caller does `resp.get("id", "unknown")` and would silently
        # produce broken Fabric URLs — instead, recover the id from the Location
        # header (`.../items/{id}`) and refetch, or fail loudly so a partial
        # success doesn't masquerade as a complete one.
        if r.content:
            try:
                return r.json()
            except ValueError:
                pass
        location = r.headers.get("Location") or r.headers.get("Content-Location")
        if location:
            # Resolve relative URLs against the Fabric base.
            if location.startswith("/"):
                location = f"https://api.fabric.microsoft.com{location}"
            fetched = requests.get(location,
                                   headers={"Authorization": f"Bearer {fabric_token}"},
                                   timeout=HTTP_TIMEOUT)
            fetched.raise_for_status()
            return fetched.json()
        raise RuntimeError(
            f"Fabric returned {r.status_code} for {path!r} with an empty/non-JSON body "
            f"and no Location header — cannot identify the created item. "
            f"Headers: {dict(r.headers)}"
        )
    if r.status_code == 202:
        # Long-running operation — poll via Location / Operation-Location / x-ms-operation-id
        location = (
            r.headers.get("Location")
            or r.headers.get("Operation-Location")
            or (f"https://api.fabric.microsoft.com/v1/operations/{r.headers['x-ms-operation-id']}"
                if "x-ms-operation-id" in r.headers else None)
        )
        if not location:
            raise RuntimeError("202 response missing Location, Operation-Location, or x-ms-operation-id header")
        # Some Fabric endpoints return relative URLs (e.g. `/v1/operations/...`).
        # Resolve against the Fabric base so `requests.get` receives a valid URL,
        # matching the 200/201 path above.
        if location.startswith("/"):
            location = f"https://api.fabric.microsoft.com{location}"
        max_polls = int(os.environ.get("FABRIC_LRO_MAX_POLLS", 150))   # default ~5 min at 2 s base
        base_sleep = float(os.environ.get("FABRIC_LRO_POLL_INTERVAL", 2))
        # Sleep BEFORE the first poll, honoring `Retry-After` from the initial
        # 202 response when present. Polling immediately wastes a round-trip
        # (typically returns transient "not ready") and ignores throttling
        # guidance from busy tenants, which can trigger 429s.
        initial_retry = r.headers.get("Retry-After")
        time.sleep(float(initial_retry) if initial_retry else base_sleep)
        for _ in range(max_polls):
            poll = requests.get(location,
                                headers={"Authorization": f"Bearer {fabric_token}"},
                                timeout=HTTP_TIMEOUT)
            poll.raise_for_status()
            state = poll.json()
            status = state.get("status")
            if status == "Succeeded":
                # Follow resourceLocation to fetch the created item
                resource_url = (
                    state.get("resourceLocation")
                    or state.get("result", {}).get("resourceLocation")
                )
                if resource_url:
                    if resource_url.startswith("/"):
                        resource_url = f"https://api.fabric.microsoft.com{resource_url}"
                    item = requests.get(resource_url,
                                        headers={"Authorization": f"Bearer {fabric_token}"},
                                        timeout=HTTP_TIMEOUT)
                    item.raise_for_status()
                    return item.json()
                # Fallback: some LRO responses embed the created item in result
                result = state.get("result") or {}
                if result.get("id"):
                    return result
                raise RuntimeError(
                    f"Fabric LRO Succeeded for {path!r} but no resourceLocation "
                    f"or result.id found — cannot identify created item. "
                    f"Raw state: {state}"
                )
            elif status == "Failed":
                raise RuntimeError(f"Fabric LRO failed: {state.get('error', state)}")
            elif status == "Cancelled":
                # Treat user/admin-initiated cancellation as a terminal failure —
                # otherwise the loop keeps polling a terminal operation until the
                # max_polls timeout fires.
                raise RuntimeError(
                    f"Fabric LRO cancelled for {path!r}: {state.get('error', state)}"
                )
            retry_after = poll.headers.get("Retry-After")
            sleep_s = float(retry_after) if retry_after else base_sleep
            time.sleep(sleep_s)
        raise TimeoutError(f"Fabric LRO timed out after {max_polls} polls: {path}")
    r.raise_for_status()
    return r.json() if r.content else {}

# ── Resolve Fabric workspace ID ────────────────────────────────────────────────
print(f"Resolving Fabric workspace '{FABRIC_WS_NAME}'...", flush=True)
ws_list = fabric_paginate("/workspaces")
fabric_ws = next((w for w in ws_list if w["displayName"] == FABRIC_WS_NAME), None)
if not fabric_ws:
    sample = [w["displayName"] for w in ws_list[:5]]
    hint = f"first {len(sample)} of {len(ws_list)}: {sample}" if len(ws_list) > 5 else str(sample)
    raise ValueError(
        f"Fabric workspace '{FABRIC_WS_NAME}' not found. "
        f"Check the name and your access permissions ({hint})"
    )
FABRIC_WS_ID = fabric_ws["id"]
print(f"  Fabric workspace ID: {FABRIC_WS_ID}", flush=True)

# ── Build notebook name → Fabric GUID map ─────────────────────────────────────
notebooks_in_fabric = fabric_paginate(f"/workspaces/{FABRIC_WS_ID}/notebooks")
notebook_guid_map = {nb["displayName"]: nb["id"] for nb in notebooks_in_fabric}
_nb_count = len(notebook_guid_map)
_nb_sample = list(notebook_guid_map.keys())[:5]
_nb_suffix = f" (showing first 5 of {_nb_count})" if _nb_count > 5 else ""
print(f"  Notebooks in Fabric: {_nb_count}{_nb_suffix}: {_nb_sample}", flush=True)

# ── Fetch pipelines from Synapse ───────────────────────────────────────────────
# Use paginated GET so workspaces with > 1 page of pipelines are migrated in full
# when PIPELINES == ['*'] (the bare /pipelines endpoint paginates via nextLink).
all_pipelines = synapse_paginate("/pipelines?api-version=2020-12-01")
if PIPELINES == ["*"]:
    pipelines_to_migrate = all_pipelines
else:
    # Validate explicit names up-front so typos, renamed pipelines, or pipelines
    # outside the caller's read permissions surface as a clear error instead of
    # silently shrinking the migration set (or producing a 'successful' run that
    # migrated zero pipelines).
    available_names = {p["name"] for p in all_pipelines}
    missing = [n for n in PIPELINES if n not in available_names]
    if missing:
        sample = sorted(available_names)[:10]
        sample_hint = (f"first 10 of {len(available_names)}: {sample}"
                       if len(available_names) > 10 else str(sample))
        raise ValueError(
            f"Requested pipeline(s) not found in Synapse workspace "
            f"'{SYNAPSE_WS}': {missing}. Check spelling, that the pipelines "
            f"still exist, and that the caller has read access. "
            f"Available pipelines ({sample_hint})."
        )
    pipelines_to_migrate = [p for p in all_pipelines if p["name"] in PIPELINES]
print(f"Migrating {len(pipelines_to_migrate)} pipeline(s): "
      f"{[p['name'] for p in pipelines_to_migrate]}", flush=True)

# ── Activity transformation ────────────────────────────────────────────────────
def fix_timeout(t):
    """Clamp Synapse timeouts to Fabric max of 12 hours (0.12:00:00).

    Returns None when t is absent/empty so the caller can omit the key
    entirely and let the platform default apply — only clamp when an
    explicit timeout exceeds 12 hours.

    Supports both d.hh:mm:ss and hh:mm:ss formats. Unrecognised formats
    are returned unchanged so valid custom values are not silently altered.
    """
    if not t:
        return None
    m = re.match(r'^(\d+)\.(\d+):(\d+):(\d+)$', t)
    if m:
        days, hours, minutes, seconds = (int(m.group(1)), int(m.group(2)),
                                         int(m.group(3)), int(m.group(4)))
    else:
        m = re.match(r'^(\d+):(\d+):(\d+)$', t)
        if m:
            days, hours, minutes, seconds = 0, int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            # Unrecognised format — pass through unchanged rather than silently clamping
            print(f"  ⚠️  Unrecognised timeout format '{t}' — kept as-is", flush=True)
            return t
    total_seconds = (((days * 24) + hours) * 60 + minutes) * 60 + seconds
    if total_seconds > 12 * 60 * 60:
        return "0.12:00:00"
    return t

def transform_activity(activity, nb_map, ws_id):
    """Recursively transform a Synapse activity to its Fabric equivalent."""
    atype = activity.get("type")
    if atype == "SynapseNotebook":
        tp = activity.get("typeProperties", {})
        nb_name = tp.get("notebook", {}).get("referenceName", "")
        nb_guid = nb_map.get(nb_name)
        if not nb_guid:
            # Show a bounded sample instead of the full list — real workspaces
            # can have hundreds of notebooks and dumping all names floods the
            # log. Mirrors the workspace-not-found hint shape above.
            available = sorted(nb_map.keys())
            sample = available[:5]
            hint = (f"first {len(sample)} of {len(available)}: {sample}"
                    if len(available) > 5 else str(sample))
            raise ValueError(
                f"Notebook '{nb_name}' not found in Fabric workspace '{FABRIC_WS_NAME}' "
                f"({hint}). "
                "Migrate the notebook first using the synapse-migration skill."
            )
        new_tp = {"notebookId": nb_guid, "workspaceId": ws_id}
        if tp.get("parameters"):
            new_tp["parameters"] = tp["parameters"]
        policy = dict(activity.get("policy", {}))
        clamped = fix_timeout(policy.get("timeout"))
        if clamped is not None:
            policy["timeout"] = clamped
        else:
            policy.pop("timeout", None)  # omit key; let platform default apply
        # Only emit "policy" when it has at least one meaningful field —
        # an empty {} can fail schema validation on some Fabric endpoints.
        result = {**activity, "type": "TridentNotebook", "typeProperties": new_tp}
        if policy:
            result["policy"] = policy
        else:
            result.pop("policy", None)
        return result
    # Recurse into container activities
    tp = dict(activity.get("typeProperties", {}))
    for key in ("activities", "ifTrueActivities", "ifFalseActivities", "defaultActivities"):
        if key in tp:
            tp[key] = [transform_activity(a, nb_map, ws_id) for a in tp[key]]
    if "cases" in tp:
        for case in tp["cases"]:
            case["activities"] = [transform_activity(a, nb_map, ws_id)
                                   for a in case.get("activities", [])]
    return {**activity, "typeProperties": tp}

# ── Migrate each pipeline ──────────────────────────────────────────────────────
results = []
for pipeline in pipelines_to_migrate:
    name = pipeline["name"]
    print(f"\nMigrating: {name}", flush=True)
    full  = synapse_get(f"/pipelines/{name}?api-version=2020-12-01")
    props = full.get("properties", {})
    transformed = [transform_activity(a, notebook_guid_map, FABRIC_WS_ID)
                   for a in props.get("activities", [])]

    # ── Phase 2/3 guard ────────────────────────────────────────────────────
    # The inline runner only performs Phase 0/4/5 — it does NOT apply Phase 2
    # (linked service → Fabric Connection name mapping) or Phase 3 (dataset
    # inlining). If the source pipeline contains Copy activities with
    # inputs/outputs DatasetReferences, Lookup/GetMetadata/Delete activities
    # with a `dataset` reference, or any other linkedServiceName/Reference
    # value still pointing at a Synapse linked service, deploying as-is would
    # produce an invalid Fabric pipeline. Fail loudly instead of silently
    # uploading broken JSON.
    # Only flag LinkedServiceReference under Synapse-specific parent keys.
    # Fabric pipeline JSON also uses `LinkedServiceReference` (e.g., under
    # `linkedService` on sinks/sources, or `externalReferences` on Copy
    # activities) to point at Fabric Connections, so a blanket type check
    # false-positives on valid post-Phase-2 Fabric output. Synapse-only
    # shapes always nest the reference under one of these parent keys:
    SYNAPSE_LS_PARENTS = {"linkedServiceName", "functionLinkedService"}

    def _find_synapse_only_constructs(node, path="$", parent_key=None):
        problems = []
        if isinstance(node, dict):
            if "referenceName" in node and node.get("type") == "DatasetReference":
                problems.append(f"{path} → DatasetReference to '{node['referenceName']}'")
            if (
                "referenceName" in node
                and node.get("type") == "LinkedServiceReference"
                and parent_key in SYNAPSE_LS_PARENTS
            ):
                problems.append(f"{path} → LinkedServiceReference to '{node['referenceName']}'")
            for k, v in node.items():
                problems.extend(_find_synapse_only_constructs(v, f"{path}.{k}", parent_key=k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                problems.extend(_find_synapse_only_constructs(v, f"{path}[{i}]", parent_key=parent_key))
        return problems

    synapse_only = _find_synapse_only_constructs({"activities": transformed})
    if synapse_only:
        sample = synapse_only[:5]
        more = f" (and {len(synapse_only) - len(sample)} more)" if len(synapse_only) > len(sample) else ""
        raise RuntimeError(
            f"Pipeline '{name}' still contains Synapse-only constructs after Phase 4 "
            f"transformation — the inline runner does NOT perform Phase 2 (linked "
            f"service → Fabric Connection) or Phase 3 (dataset inlining). "
            f"Uploading as-is would produce an invalid Fabric pipeline. Run "
            f"`linked-service-to-connection.md` and `dataset-inlining.md` first, "
            f"or use the full orchestrator flow. Offending references: {sample}{more}"
        )

    fabric_pipeline = {
        "properties": {
            "activities":  transformed,
            "parameters":  props.get("parameters", {}),
            "variables":   props.get("variables", {}),
            "annotations": props.get("annotations", []),
        }
    }
    if props.get("folder"):
        fabric_pipeline["properties"]["folder"] = props["folder"]
    # Phase 4 expression rewrite: @pipeline().globalParameters → @pipeline().libraryVariables
    # Walk the pipeline structure and rewrite only ADF expression strings
    # (values that begin with "@"). A blind global string-replace on the
    # serialized JSON could clobber unrelated text — e.g. literal descriptions,
    # annotations, or embedded code snippets that happen to contain the
    # substring "@pipeline().globalParameters." in prose form.
    #
    # Canonical implementation — keep in sync with the equivalent helpers in:
    #   - skills/pipeline-migration/resources/notebook-activity-migration.md
    #     (rewrite_global_parameters inside transform_pipeline_notebook_activities)
    #   - skills/pipeline-migration/resources/global-parameters-to-variable-library.md
    #     (rewrite_global_parameters in the Expression Rewrite section)
    # If you change the rewrite rules here (e.g. additional expression prefixes
    # or guarded substrings), update those copies too so the three docs don't
    # drift apart.
    def _rewrite_expressions(node):
        if isinstance(node, dict):
            # ADF/Fabric pipeline JSON places every expression inside a dict
            # shaped {"value": "@...", "type": "Expression"}. Restrict the
            # rewrite to that exact shape so prose in description/annotation
            # fields, embedded code samples, or other non-expression text
            # that happens to contain "pipeline().globalParameters." is not
            # mutated (which would otherwise false-positive the VARIABLE_LIBRARY_ID
            # hard-fail check downstream).
            if (
                node.get("type") == "Expression"
                and isinstance(node.get("value"), str)
                and node["value"].startswith("@")
            ):
                return {
                    **node,
                    # Match the bare `pipeline().globalParameters.` substring so
                    # both `@pipeline().globalParameters.x` AND nested forms
                    # like `@concat('env=', pipeline().globalParameters.env)`
                    # get rewritten. The outer startswith("@") guard above
                    # still scopes this strictly to expression-shaped dicts.
                    "value": node["value"].replace(
                        "pipeline().globalParameters.",
                        "pipeline().libraryVariables.",
                    ),
                }
            return {k: _rewrite_expressions(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_rewrite_expressions(v) for v in node]
        return node

    fabric_pipeline = _rewrite_expressions(fabric_pipeline)
    # Detect libraryVariables references by walking the dict for the exact
    # Expression shape the rewrite produces — a raw substring scan of the
    # serialized JSON would false-positive on description / annotation prose
    # that happens to mention "pipeline().libraryVariables.".
    def _has_library_variables_expression(node):
        if isinstance(node, dict):
            if (node.get("type") == "Expression"
                and isinstance(node.get("value"), str)
                and "pipeline().libraryVariables." in node["value"]):
                return True
            return any(_has_library_variables_expression(v) for v in node.values())
        if isinstance(node, list):
            return any(_has_library_variables_expression(v) for v in node)
        return False

    has_library_variables_ref = _has_library_variables_expression(fabric_pipeline)
    # Hard fail if the rewrite produced libraryVariables references but no
    # Variable Library was provisioned — the pipeline would deploy but its
    # expressions would silently fail to resolve at runtime.
    if has_library_variables_ref and not VARIABLE_LIBRARY_ID:
        raise RuntimeError(
            f"Pipeline '{name}' references @pipeline().libraryVariables.* but "
            f"VARIABLE_LIBRARY_ID is not set. Run Phase 1 (Variable Library creation) "
            f"first and pass the resulting library GUID, or remove global-parameter "
            f"references from the source pipeline."
        )
    # Attach the libraryVariables block so the rewritten expressions resolve at runtime.
    # Required whenever Phase 1 produced a Variable Library and the pipeline references it.
    if VARIABLE_LIBRARY_ID and has_library_variables_ref:
        fabric_pipeline["properties"]["libraryVariables"] = {
            "libraryId":   VARIABLE_LIBRARY_ID,
            "workspaceId": FABRIC_WS_ID,
        }
    fabric_pipeline_json = json.dumps(fabric_pipeline)
    payload_b64 = base64.b64encode(fabric_pipeline_json.encode()).decode()
    resp = fabric_post(f"/workspaces/{FABRIC_WS_ID}/items", {
        "displayName": name + NAME_SUFFIX,
        "type": "DataPipeline",
        "definition": {
            "format": "DataPipeline",
            "parts": [{"path": "pipeline-content.json",
                       "payload": payload_b64,
                       "payloadType": "InlineBase64"}]
        }
    })
    pid = resp.get("id", "unknown")
    url = f"https://app.fabric.microsoft.com/groups/{FABRIC_WS_ID}/datapipelines/{pid}"
    print(f"  [OK] Created: {name}  (id: {pid})")
    print(f"  [link] {url}")
    results.append({"name": name, "id": pid, "url": url})

print(f"\n{'='*60}")
print(f"Done — {len(results)} pipeline(s) created in Fabric workspace '{FABRIC_WS_NAME}'")
for r in results:
    print(f"  {r['name']}: {r['url']}")
```

> **Windows**: `az` is called as `az.cmd`. The runner detects this automatically via `shutil.which("az.cmd")`.

### Derived Values (Auto-Discovered)

| Value | Derived From |
|---|---|
| Synapse data-plane endpoint | `https://{workspaceName}.dev.azuresynapse.net` |
| Fabric workspace ID | `GET /v1/workspaces` → JMESPath filter by `displayName` |
| Fabric notebook GUIDs | `GET /v1/workspaces/{wsId}/notebooks` → filter by `displayName` |
| Fabric connection names | `GET /v1/connections` → filter by `displayName` |

---

## Orchestration Flow

```
Pipeline Migration Orchestrator:
│
├── Step 0: Authenticate (acquire 3 tokens)
├── Step 1: Inventory Synapse workspace
│   ├── List all pipelines
│   ├── List all datasets
│   ├── List all linked services
│   └── Get workspace global parameters
│
├── Phase 0: Prerequisite — Migrate Notebooks (synapse-migration skill)
│   ├── Identify notebooks referenced by SynapseNotebook activities
│   ├── ⚠️ GATE: These notebooks must exist in Fabric before Phase 4
│   └── Output: notebookNameToGUID mapping
│
├── Phase 1: Global Parameters → Variable Library
│   ├── Execute global-parameters-to-variable-library.md
│   ├── ⏸ GATE: Confirm Variable Library created and accessible
│   └── Output: variableLibraryId
│
├── Phase 2: Linked Services → Fabric Connections
│   ├── Execute linked-service-to-connection.md for each used linked service
│   ├── ⏸ GATE: Confirm all required connections created
│   └── Output: linkedServiceToConnectionName mapping
│
├── Phase 3: Build Dataset Inline Map
│   ├── Execute dataset-inlining.md to build dataset→inline map
│   └── Output: datasetInlineMap (dataset name → inline typeProperties)
│
├── Phase 4: Transform Pipeline Activities
│   ├── Execute activity-mapping.md for each activity type
│   ├── Apply notebook-activity-migration.md for SynapseNotebook activities
│   ├── Substitute dataset references with inlined definitions (Phase 3 map)
│   ├── Substitute linked service references with connection names (Phase 2 map)
│   ├── Replace @pipeline().globalParameters → @pipeline().libraryVariables
│   ├── Flag parked activities (SSIS, Databricks, SHIR-only) — log, do not block
│   └── Output: transformedActivities JSON array
│
├── Phase 5: Assemble & Deploy Fabric Pipeline
│   ├── Build pipeline-content.json (see § Pipeline JSON Assembly)
│   ├── Base64-encode the JSON
│   ├── POST to Fabric Items API
│   └── Output: fabricPipelineId
│
└── Final: Validation
    └── Execute validation-testing.md
```

---

## Step 0: Authentication

Acquire three tokens:

```bash
# 1. Synapse Data Plane token (pipelines, datasets, linked services)
SYNAPSE_TOKEN=$(az account get-access-token \
  --resource https://dev.azuresynapse.net \
  --query accessToken -o tsv)

# 2. Synapse ARM token (workspace properties, global parameters)
ARM_TOKEN=$(az account get-access-token \
  --resource https://management.azure.com \
  --query accessToken -o tsv)

# 3. Fabric token
FABRIC_TOKEN=$(az account get-access-token \
  --resource https://api.fabric.microsoft.com \
  --query accessToken -o tsv)

SYNAPSE_WS="mysynapseworkspace"
SYNAPSE_ENDPOINT="https://${SYNAPSE_WS}.dev.azuresynapse.net"
```

---

## Step 1: Inventory the Synapse Workspace

### List All Pipelines

```bash
# Enumerate all pipeline names
az rest --method GET \
  --headers "Authorization=Bearer ${SYNAPSE_TOKEN}" \
  --url "${SYNAPSE_ENDPOINT}/pipelines?api-version=2020-12-01" \
  --query "value[].name" -o tsv
```

### Get a Pipeline Definition

```bash
PIPELINE_NAME="MyIngestPipeline"
az rest --method GET \
  --headers "Authorization=Bearer ${SYNAPSE_TOKEN}" \
  --url "${SYNAPSE_ENDPOINT}/pipelines/${PIPELINE_NAME}?api-version=2020-12-01"
```

Response includes `properties.activities`, `properties.parameters`, `properties.variables`, `properties.folder`.

### List All Datasets

```bash
az rest --method GET \
  --headers "Authorization=Bearer ${SYNAPSE_TOKEN}" \
  --url "${SYNAPSE_ENDPOINT}/datasets?api-version=2020-12-01" \
  --query "value[].{name:name, type:properties.type, linkedService:properties.linkedServiceName.referenceName}" \
  -o table
```

### List All Linked Services

```bash
az rest --method GET \
  --headers "Authorization=Bearer ${SYNAPSE_TOKEN}" \
  --url "${SYNAPSE_ENDPOINT}/linkedservices?api-version=2020-12-01" \
  --query "value[].{name:name, type:properties.type}" \
  -o table
```

### Get Global Parameters

```bash
SUB_ID="<subscription-id>"
RG="<resource-group>"

az rest --method GET \
  --headers "Authorization=Bearer ${ARM_TOKEN}" \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/resourceGroups/${RG}/providers/Microsoft.Synapse/workspaces/${SYNAPSE_WS}?api-version=2021-06-01" \
  --query "properties.globalParameters"
```

---

## Step 1b: Discover Notebook References in Pipelines

Before Phase 4 can proceed, identify which Synapse notebooks are referenced by `SynapseNotebook` activities so they can be pre-migrated.

```python
import json, re

def find_notebook_references(pipeline_def):
    """Extract all unique Synapse notebook names from SynapseNotebook activities."""
    notebooks = set()
    for activity in pipeline_def.get("properties", {}).get("activities", []):
        if activity.get("type") == "SynapseNotebook":
            ref = (activity
                   .get("typeProperties", {})
                   .get("notebook", {})
                   .get("referenceName"))
            if ref:
                notebooks.add(ref)
        tp = activity.get("typeProperties", {})
        # Recurse into ForEach / IfCondition / Until inner activities (direct activity lists)
        for inner_key in ("activities", "ifTrueActivities", "ifFalseActivities",
                          "defaultActivities"):
            for inner in tp.get(inner_key, []):
                if isinstance(inner, dict):
                    notebooks.update(find_notebook_references({"properties": {"activities": [inner]}}))
        # Switch: cases is [{value, activities}, ...] — must unwrap each case's activity list
        for case in tp.get("cases", []):
            if isinstance(case, dict):
                for inner in case.get("activities", []):
                    if isinstance(inner, dict):
                        notebooks.update(find_notebook_references({"properties": {"activities": [inner]}}))
    return notebooks

# Usage
pipeline_json = json.loads(open("pipeline.json").read())
notebook_refs = find_notebook_references(pipeline_json)
print("Notebooks to migrate first:", notebook_refs)
```

### Build Notebook Name → Fabric GUID Map

After running the synapse-migration skill to migrate the notebooks:

```bash
FABRIC_WS_ID="<fabric-workspace-id>"
az rest --method GET \
  --headers "Authorization=Bearer ${FABRIC_TOKEN}" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${FABRIC_WS_ID}/notebooks" \
  --query "value[].{name:displayName, id:id}" -o table
```

Store this mapping in a JSON file for use in Phase 4:
```json
{
  "NotebookA": "aaaaaaaa-1111-2222-3333-444444444444",
  "NotebookB": "bbbbbbbb-5555-6666-7777-888888888888"
}
```

---

## Phase 5: Assemble Fabric Pipeline JSON

After completing Phases 0–4, assemble the final `pipeline-content.json`.

### Pipeline JSON Structure

```json
{
  "properties": {
    "description": "<pipeline description>",
    "activities": [ /* transformed activities array from Phase 4 */ ],
    "parameters": {
      "<paramName>": {
        "type": "string",
        "defaultValue": "<value>"
      }
    },
    "variables": {
      "<varName>": {
        "type": "String",
        "defaultValue": "<value>"
      }
    },
    "libraryVariables": {
      "libraryId": "<variable-library-item-id>",
      "workspaceId": "<fabric-workspace-id>"
    },
    "annotations": [],
    "folder": {
      "name": "<folder-path>"
    }
  }
}
```

> `libraryVariables` is only needed when the pipeline uses `@pipeline().libraryVariables.<name>` expressions (migrated from global parameters). Set `libraryId` to the Variable Library item GUID created in Phase 1.

> `folder` replicates the Synapse pipeline folder structure. This is optional but helps organize migrated pipelines.

### Deploy to Fabric

```python
import base64, json, requests

FABRIC_TOKEN = "<fabric-token>"
FABRIC_WS_ID = "<workspace-id>"
PIPELINE_NAME = "MyIngestPipeline"

pipeline_content = { /* assembled pipeline JSON */ }
payload_b64 = base64.b64encode(
    json.dumps(pipeline_content).encode("utf-8")
).decode("utf-8")

headers = {
    "Authorization": f"Bearer {FABRIC_TOKEN}",
    "Content-Type": "application/json"
}

body = {
    "displayName": PIPELINE_NAME,
    "type": "DataPipeline",
    "definition": {
        "format": "DataPipeline",
        "parts": [
            {
                "path": "pipeline-content.json",
                "payload": payload_b64,
                "payloadType": "InlineBase64"
            }
        ]
    }
}

response = requests.post(
    f"https://api.fabric.microsoft.com/v1/workspaces/{FABRIC_WS_ID}/items",
    headers=headers,
    json=body,
    timeout=60,
)

if response.status_code == 202:
    # Long-running operation — poll the Location header
    location = response.headers.get("Location")
    print(f"Pipeline creation in progress. Poll: {location}")
elif response.status_code in (200, 201):
    # Some Fabric item endpoints succeed with an empty/non-JSON body and convey
    # identity via the Location header — handle both shapes so the created id
    # isn't silently lost.
    item_id = None
    if response.content:
        try:
            item_id = response.json().get("id")
        except ValueError:
            item_id = None
    if not item_id and response.headers.get("Location"):
        from urllib.parse import urlsplit
        segs = [s for s in urlsplit(response.headers["Location"]).path.split("/") if s]
        item_id = segs[-1] if segs else None
    print(f"Pipeline created: {item_id or '<id unavailable>'}")
else:
    print(f"Error {response.status_code}: {response.text}")
```

### Update an Existing Pipeline Definition

If the pipeline item already exists and you need to update its definition:

```bash
PIPELINE_ITEM_ID="<fabric-pipeline-item-id>"
# payload_b64 = base64-encoded pipeline-content.json

az rest --method POST \
  --headers "Authorization=Bearer ${FABRIC_TOKEN}" "Content-Type=application/json" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${FABRIC_WS_ID}/items/${PIPELINE_ITEM_ID}/updateDefinition" \
  --body "{
    \"definition\": {
      \"parts\": [{
        \"path\": \"pipeline-content.json\",
        \"payload\": \"${payload_b64}\",
        \"payloadType\": \"InlineBase64\"
      }]
    }
  }"
```

---

## Pipeline Inventory Script (Full Workspace Scan)

Use this to produce a migration manifest before starting:

```python
import requests, json
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

SYNAPSE_TOKEN = "<synapse-data-plane-token>"
SYNAPSE_ENDPOINT = "https://myworkspace.dev.azuresynapse.net"
headers = {"Authorization": f"Bearer {SYNAPSE_TOKEN}"}

def paginate(url):
    items = []
    while url:
        r = requests.get(url, headers=headers, timeout=60)
        r.raise_for_status()
        data = r.json()
        items.extend(data.get("value", []))
        url = data.get("nextLink")
    return items

pipelines = paginate(f"{SYNAPSE_ENDPOINT}/pipelines?api-version=2020-12-01")
datasets = paginate(f"{SYNAPSE_ENDPOINT}/datasets?api-version=2020-12-01")
linked_services = paginate(f"{SYNAPSE_ENDPOINT}/linkedservices?api-version=2020-12-01")

manifest = {
    "pipelines": [p["name"] for p in pipelines],
    "datasets": [d["name"] for d in datasets],
    "linked_services": [ls["name"] for ls in linked_services],
    "pipeline_activity_types": {}
}

for p in pipelines:
    name = p["name"]
    # The list endpoint returns stubs — properties.activities is often omitted.
    # Fetch each pipeline definition to get the real activity list.
    r = requests.get(
        f"{SYNAPSE_ENDPOINT}/pipelines/{name}?api-version=2020-12-01",
        headers={"Authorization": f"Bearer {SYNAPSE_TOKEN}"},
        timeout=60,
    )
    r.raise_for_status()
    detail = r.json()
    types = set()

    def _collect_types(activities):
        for a in activities or []:
            atype = a.get("type")
            if atype:
                types.add(atype)
            inner = a.get("typeProperties", {}) or {}
            # ForEach / IfCondition / Until: direct activity lists
            for key in ("activities", "ifTrueActivities", "ifFalseActivities", "defaultActivities"):
                if isinstance(inner.get(key), list):
                    _collect_types(inner[key])
            # Switch: cases is [{value, activities}, ...]
            for case in inner.get("cases", []) or []:
                if isinstance(case, dict):
                    _collect_types(case.get("activities", []))

    _collect_types(detail.get("properties", {}).get("activities", []))
    manifest["pipeline_activity_types"][name] = sorted(types)

# Flag pipelines with parked activity types
PARKED_TYPES = {"ExecuteSSISPackage", "DatabricksNotebook", "DatabricksSparkJar",
                "DatabricksSparkPython", "AzureBatch", "Custom"}

print("=== Migration Manifest ===")
for pipeline, types in manifest["pipeline_activity_types"].items():
    parked = set(types) & PARKED_TYPES
    status = "⛔ PARKED" if parked else "✅ Migratable"
    print(f"{status}  {pipeline}: {types}")
    if parked:
        print(f"         ↳ Parked activity types: {parked}")

print(f"\nTotal: {len(pipelines)} pipelines, {len(datasets)} datasets, {len(linked_services)} linked services")
```

---

## Handling Pagination

Synapse endpoints use `nextLink` for continuation; Fabric endpoints use `continuationToken`:

```python
def paginate_synapse(url, token):
    items = []
    while url:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        r.raise_for_status()
        data = r.json()
        items.extend(data.get("value", []))
        url = data.get("nextLink")
    return items

def paginate_fabric(url, token):
    items = []
    while url:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        r.raise_for_status()
        data = r.json()
        items.extend(data.get("value", []))
        # Fabric uses continuationToken, not nextLink. Preserve any other
        # query-string params already present on `url` and URL-encode the token.
        cont = data.get("continuationToken")
        if cont:
            parts = urlsplit(url)
            query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                     if k != "continuationToken"]
            query.append(("continuationToken", cont))
            url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
        else:
            url = None
    return items
```

> Fabric API uses `continuationToken` (query param) rather than a full `nextLink` URL.
