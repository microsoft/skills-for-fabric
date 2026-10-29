# Validation & Testing — Post-Migration Verification

Step-by-step checks to confirm each migrated pipeline is structurally valid and functionally correct in Fabric before handing off to production.

---

## Validation Checklist

| Check | Description | Pass Criteria |
|---|---|---|
| **V1** | Pipeline definition round-trips | Call `getDefinition` (POST LRO) and verify the returned definition contains all activities |
| **V2** | Pipeline runs without error | Status = `Completed` (job-instance terminal status per Fabric pipeline REST API) |
| **V3** | TridentNotebook activities succeed end-to-end | Notebook completes; output readable |
| **V4** | Variable Library values accessible | `@pipeline().libraryVariables.*` expressions resolve |
| **V5** | Copy activity with inlined dataset succeeds | Row count > 0 or expected; no connector errors |
| **V6** | Expression references valid | No null values from `libraryVariables` expressions; no remaining `@pipeline().globalParameters` references |

---

## V1 — Pipeline Definition Round-Trip

After deploying a pipeline, retrieve its definition and verify the activity structure is intact.

```bash
FABRIC_TOKEN="<fabric-token>"
FABRIC_WS_ID="<workspace-id>"
PIPELINE_ITEM_ID="<pipeline-item-id>"

az rest --method POST \
  --headers "Authorization=Bearer ${FABRIC_TOKEN}" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${FABRIC_WS_ID}/items/${PIPELINE_ITEM_ID}/getDefinition"
```

The response is a long-running operation (LRO). Poll until complete:

```python
import requests, time, base64, json, os

def get_pipeline_definition(workspace_id, pipeline_item_id, fabric_token,
                            max_polls=None, base_poll_interval=None):
    headers = {"Authorization": f"Bearer {fabric_token}"}
    # Per-request HTTP timeout as (connect, read). Long-running migrations
    # must not hang indefinitely on a transient network stall.
    http_timeout = (
        float(os.environ.get("FABRIC_HTTP_CONNECT_TIMEOUT", 10)),
        float(os.environ.get("FABRIC_HTTP_READ_TIMEOUT", 60)),
    )
    # Polling cadence: getDefinition on large pipelines can exceed the
    # naive 30 * 2 s = 60 s budget. Make max_polls and base_poll_interval
    # configurable (env vars or call args), and honor Retry-After when the
    # service supplies a polling hint — matches the LRO pattern in
    # pipeline-orchestrator.md fabric_post.
    if max_polls is None:
        max_polls = int(os.environ.get("FABRIC_LRO_MAX_POLLS", 150))
    if base_poll_interval is None:
        base_poll_interval = float(os.environ.get("FABRIC_LRO_POLL_INTERVAL", 2))

    # Start getDefinition
    r = requests.post(
        f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{pipeline_item_id}/getDefinition",
        headers=headers, timeout=http_timeout,
    )

    if r.status_code == 200:
        # Empty / non-JSON bodies on 200 are rare for getDefinition but possible
        # for other Fabric endpoints -- guard so the success path can't raise
        # a bare ValueError from r.json() on an empty or malformed body.
        if not r.content:
            raise RuntimeError(
                f"getDefinition returned HTTP 200 with an empty body for pipeline "
                f"{pipeline_item_id!r} -- Fabric definition payload missing."
            )
        try:
            return r.json()
        except ValueError as exc:
            raise RuntimeError(
                f"getDefinition returned HTTP 200 with a non-JSON body for "
                f"pipeline {pipeline_item_id!r}: {exc}. "
                f"Body excerpt: {r.text[:500]!r}"
            ) from exc
    
    # Handle LRO — prefer Location/Operation-Location header; fall back to x-ms-operation-id
    op_url = r.headers.get("Location") or r.headers.get("Operation-Location")
    operation_id = r.headers.get("x-ms-operation-id")
    if not op_url and operation_id:
        op_url = f"https://api.fabric.microsoft.com/v1/operations/{operation_id}"
    if not op_url:
        # Anything that isn't 200 and didn't surface a poll URL is an error.
        # raise_for_status() only fires for >=400, so a 202 with no headers
        # (or any other non-error status missing the LRO handles) would
        # otherwise fall through to op_url.startswith(...) and AttributeError.
        r.raise_for_status()
        raise RuntimeError(
            f"getDefinition returned HTTP {r.status_code} with no Location, "
            f"Operation-Location, or x-ms-operation-id header — cannot poll. "
            f"Response body: {r.text[:500]}"
        )
    # Some Fabric endpoints return a relative Location/Operation-Location
    # (e.g. "/v1/operations/..."). Resolve against the Fabric base before
    # polling so requests.get() receives a valid absolute URL.
    if op_url.startswith("/"):
        op_url = f"https://api.fabric.microsoft.com{op_url}"

    # Honor the original Retry-After hint, if any, for the first sleep.
    last_response = r
    for _ in range(max_polls):
        retry_after = last_response.headers.get("Retry-After")
        sleep_s = float(retry_after) if retry_after else base_poll_interval
        time.sleep(sleep_s)
        poll = requests.get(op_url, headers=headers, timeout=http_timeout)
        poll.raise_for_status()
        last_response = poll
        state = poll.json()
        status = state.get("status")
        if status == "Succeeded":
            result_url = state.get("resourceLocation") or state.get("result", {}).get("resourceLocation")
            if result_url:
                if result_url.startswith("/"):
                    result_url = f"https://api.fabric.microsoft.com{result_url}"
                # Fetch and validate the resourceLocation payload defensively:
                # raise on 4xx/5xx, and guard r.json() on an empty 200 body so
                # the success path can't fail with a confusing ValueError.
                result_resp = requests.get(result_url, headers=headers, timeout=http_timeout)
                result_resp.raise_for_status()
                if not result_resp.content:
                    raise RuntimeError(
                        f"getDefinition resourceLocation returned HTTP "
                        f"{result_resp.status_code} with an empty body "
                        f"({result_url}) -- Fabric definition payload missing."
                    )
                try:
                    return result_resp.json()
                except ValueError as exc:
                    raise RuntimeError(
                        f"getDefinition resourceLocation returned HTTP "
                        f"{result_resp.status_code} with a non-JSON body "
                        f"({result_url}): {exc}. "
                        f"Body excerpt: {result_resp.text[:500]!r}"
                    ) from exc
            return state
        elif status == "Failed":
            raise RuntimeError(f"getDefinition failed: {state}")
        elif status == "Cancelled":
            raise RuntimeError(f"getDefinition cancelled: {state}")
    
    raise TimeoutError(
        f"getDefinition LRO timed out after {max_polls} polls "
        f"(base interval {base_poll_interval}s). Increase FABRIC_LRO_MAX_POLLS "
        f"or FABRIC_LRO_POLL_INTERVAL for large pipeline definitions."
    )


def decode_pipeline_content(definition_response: dict) -> dict:
    """Decode base64 pipeline-content.json from getDefinition response."""
    parts = definition_response.get("definition", {}).get("parts", [])
    for part in parts:
        if part.get("path") != "pipeline-content.json":
            continue
        payload = part.get("payload")
        if not payload:
            raise ValueError(
                "pipeline-content.json part has no 'payload' field — "
                f"got keys {sorted(part.keys())}. Cannot decode."
            )
        payload_type = part.get("payloadType")
        if payload_type and payload_type != "InlineBase64":
            # We only know how to decode InlineBase64. Surface unexpected
            # payload types clearly so the error is actionable instead of a
            # cryptic base64 decode failure.
            raise ValueError(
                f"Unsupported payloadType '{payload_type}' for "
                f"pipeline-content.json — only 'InlineBase64' is supported."
            )
        return json.loads(base64.b64decode(payload).decode())
    raise KeyError("pipeline-content.json not found in definition")


def verify_activities(fabric_pipeline: dict, expected_names: list[str]) -> list[str]:
    """Return list of expected activity names NOT found in the pipeline."""
    activities = fabric_pipeline.get("properties", {}).get("activities", [])
    # Defensive: pipeline JSON is third-party content, so an activity entry
    # could be malformed (non-dict, missing 'name'). Filter rather than let
    # the set comprehension KeyError and abort the whole validation run.
    actual_names = {
        a.get("name")
        for a in activities
        if isinstance(a, dict) and a.get("name")
    }
    return [n for n in expected_names if n not in actual_names]


# Example
pipeline_def = get_pipeline_definition(FABRIC_WS_ID, PIPELINE_ITEM_ID, FABRIC_TOKEN)
pipeline_content = decode_pipeline_content(pipeline_def)
missing = verify_activities(pipeline_content, ["Run ETL Notebook", "Copy Orders", "Get Source File Metadata"])
if missing:
    print(f"⚠️  Missing activities: {missing}")
else:
    print("✅ V1: All expected activities present")
```

---

## V2 — Pipeline Run

Trigger a pipeline run and wait for it to complete.

> The same Fabric pipeline GUID is used as both `PIPELINE_ITEM_ID` (under the generic `/v1/workspaces/{wsId}/items/{itemId}/...` Item-management surface) and as the path segment under the Data Factory job surface `/v1/workspaces/{wsId}/datapipelines/{pipelineItemId}/jobs/...`. The parameter name is kept consistent (`pipeline_item_id`) across both surfaces below to avoid ambiguity.

```python
import requests, time, os

# Per-request HTTP timeout (connect, read). Mirrors the pattern in
# pipeline-orchestrator.md / get_pipeline_definition so validation runs
# never hang indefinitely on a transient network stall.
_HTTP_TIMEOUT = (
    float(os.environ.get("FABRIC_HTTP_CONNECT_TIMEOUT", 10)),
    float(os.environ.get("FABRIC_HTTP_READ_TIMEOUT", 60)),
)

def run_pipeline(workspace_id, pipeline_item_id, fabric_token, parameters=None):
    headers = {
        "Authorization": f"Bearer {fabric_token}",
        "Content-Type": "application/json"
    }
    body = {}
    if parameters:
        body["executionData"] = {"parameters": parameters}
    
    r = requests.post(
        f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/datapipelines/{pipeline_item_id}/jobs/instances?jobType=Pipeline",
        headers=headers,
        json=body,
        timeout=_HTTP_TIMEOUT,
    )
    r.raise_for_status()
    
    # Get job instance ID from Location header
    location = r.headers.get("Location", "")
    if location:
        from urllib.parse import urlparse
        path_segments = [s for s in urlparse(location).path.split("/") if s]
        job_instance_id = path_segments[-1] if path_segments else r.json().get("id")
    else:
        job_instance_id = r.json().get("id")
    return job_instance_id


def wait_for_pipeline_run(workspace_id, pipeline_item_id, job_instance_id, fabric_token, timeout_seconds=3600):
    headers = {"Authorization": f"Bearer {fabric_token}"}
    deadline = time.time() + timeout_seconds
    
    while time.time() < deadline:
        r = requests.get(
            f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/datapipelines/{pipeline_item_id}/jobs/instances/{job_instance_id}",
            headers=headers,
            timeout=_HTTP_TIMEOUT,
        )
        r.raise_for_status()
        status_data = r.json()
        status = status_data.get("status")
        
        # Fabric Job Scheduler getJobInstance returns "Completed" as the
        # terminal success state on a job instance (not "Succeeded" --
        # "Succeeded" is what the per-activity queryactivityruns response
        # carries at the activity level). See the pipeline REST API docs:
        # learn.microsoft.com/fabric/data-factory/pipeline-rest-api
        if status == "Completed":
            print(f"✅ V2: Pipeline run completed successfully")
            return status_data
        elif status in ("Failed", "Cancelled"):
            failure_reason = status_data.get("failureReason", {})
            raise RuntimeError(
                f"Pipeline run {status}: {failure_reason.get('message', 'Unknown error')}"
            )
        
        time.sleep(15)  # Poll every 15 seconds
    
    raise TimeoutError(f"Pipeline run did not complete within {timeout_seconds} seconds")


# Example
job_id = run_pipeline(FABRIC_WS_ID, PIPELINE_ITEM_ID, FABRIC_TOKEN, 
                      parameters={"runDate": "2024-01-01"})
result = wait_for_pipeline_run(FABRIC_WS_ID, PIPELINE_ITEM_ID, job_id, FABRIC_TOKEN)
```

---

## V3 — TridentNotebook Activity Verification

After a pipeline run that includes `TridentNotebook` activities, confirm the notebook ran successfully and produced expected output.

```python
def verify_notebook_activity_output(run_result: dict, activity_name: str, expected_key: str = None):
    """
    Check that a TridentNotebook activity in the run result succeeded.
    
    Args:
        run_result: The completed job instance response
        activity_name: Name of the TridentNotebook activity
        expected_key: Optional key to check in runOutput JSON
    """
    # Note: Fabric run result may need activity-level status via separate API
    # This checks the top-level run status as a proxy. Terminal success on
    # a job instance is "Completed" per the pipeline REST API.
    status = run_result.get("status")
    if status != "Completed":
        raise AssertionError(f"Run did not complete. Status: {status}")
    
    print(f"✅ V3: Pipeline containing notebook activity '{activity_name}' succeeded")
    print(f"   Run ID: {run_result.get('id')}")
    print(f"   Start: {run_result.get('startTimeUtc')}")
    print(f"   End: {run_result.get('endTimeUtc')}")
```

**Common TridentNotebook failure reasons:**

| Failure Message | Root Cause | Fix |
|---|---|---|
| `"Item not found"` | `notebookId` GUID is wrong or notebook was deleted | Re-run notebook GUID lookup and update pipeline |
| `"Session could not be started"` | No Fabric capacity available; Spark session failed | Check workspace capacity; try again during off-peak |
| `"Notebook execution failed"` | Code error inside the notebook | Check notebook run history in Fabric portal |
| `"Parameter type mismatch"` | Notebook expects `int` but pipeline passed `string` | Align parameter types in `parameters` |
| `"Timeout"` | Notebook ran longer than `policy.timeout` | Increase timeout (max 12h) or split notebook |

---

## V4 — Variable Library Accessibility

Confirm that `@pipeline().libraryVariables.*` expressions resolve correctly during a run.

**Test pipeline structure** (minimal pipeline that writes a library variable to a pipeline variable for inspection):

```json
{
  "properties": {
    "activities": [
      {
        "name": "Read Library Variable",
        "type": "SetVariable",
        "typeProperties": {
          "variableName": "capturedEnv",
          "value": {
            "value": "@pipeline().libraryVariables.environmentName",
            "type": "Expression"
          }
        }
      },
      {
        "name": "Assert Variable Set",
        "type": "IfCondition",
        "dependsOn": [{ "activity": "Read Library Variable", "dependencyConditions": ["Succeeded"] }],
        "typeProperties": {
          "expression": {
            "value": "@not(empty(variables('capturedEnv')))",
            "type": "Expression"
          },
          "ifFalseActivities": [
            {
              "name": "Fail - Variable Empty",
              "type": "Fail",
              "typeProperties": {
                "message": "Variable Library value was null or empty",
                "errorCode": "LibraryVariableMissing"
              }
            }
          ]
        }
      }
    ],
    "variables": {
      "capturedEnv": { "type": "String" }
    },
    "libraryVariables": {
      "libraryId": "<variable-library-id>",
      "workspaceId": "<workspace-id>"
    }
  }
}
```

If the `Fail` activity is triggered, the Variable Library is not correctly attached to the pipeline.

---

## V5 — Copy Activity with Inlined Dataset

For Copy activities with inlined datasets, run the pipeline with a small data sample and verify:

1. Job-instance status = `Completed` (terminal success on the pipeline job instance)
2. Rows written > 0 (or expected count)
3. No connector errors in the run output

> **`Completed` vs `Succeeded`**: The Fabric pipeline job-instance polling endpoint returns `"status": "Completed"` on success. `Succeeded` is the per-activity value returned by `queryactivityruns` (and is also the right token for `dependencyConditions` between activities) — not the job-instance terminal status.

```python
def check_copy_activity_success(run_result: dict) -> bool:
    """
    Check that the pipeline run succeeded as a proxy for Copy activity success.
    Detailed per-activity output requires the Fabric monitoring API
    (queryactivityruns), which returns "Succeeded" at the activity level.
    """
    return run_result.get("status") == "Completed"
```

**Common Copy activity failures after inlining:**

| Failure | Root Cause | Fix |
|---|---|---|
| `"Connection not found"` | Fabric connection name doesn't match `linkedServiceName` | Create connection with matching display name or update reference |
| `"Access denied to storage"` | Workspace identity lacks RBAC on storage | Grant `Storage Blob Data Contributor` to workspace managed identity |
| `"File not found"` | Inlined path expression is incorrect | Check `folderPath` / `fileName` values after inlining |
| `"Schema mismatch"` | Column mapping not preserved during inlining | Re-add `translator` block from original Synapse Copy activity |

---

## V6 — Generate Validation Summary

After running all checks, generate a summary for each pipeline:

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PipelineValidationResult:
    pipeline_name: str
    pipeline_item_id: str
    v1_definition_ok: bool = False
    v2_run_status: Optional[str] = None
    v3_notebook_ok: Optional[bool] = None
    v4_library_vars_ok: Optional[bool] = None
    v5_copy_ok: Optional[bool] = None
    errors: list[str] = field(default_factory=list)

    def passed(self) -> bool:
        critical = [self.v1_definition_ok, self.v2_run_status == "Completed"]
        return all(critical) and not self.errors

    def summary_row(self) -> dict:
        return {
            "Pipeline": self.pipeline_name,
            "V1 Definition": "✅" if self.v1_definition_ok else "❌",
            "V2 Run": "✅" if self.v2_run_status == "Completed" else f"❌ {self.v2_run_status}",
            "V3 Notebook": "✅" if self.v3_notebook_ok else ("N/A" if self.v3_notebook_ok is None else "❌"),
            "V4 Library Vars": "✅" if self.v4_library_vars_ok else ("N/A" if self.v4_library_vars_ok is None else "❌"),
            "V5 Copy": "✅" if self.v5_copy_ok else ("N/A" if self.v5_copy_ok is None else "❌"),
            "Errors": "; ".join(self.errors) if self.errors else ""
        }


def print_validation_report(results: list[PipelineValidationResult]):
    passed = sum(1 for r in results if r.passed())
    print(f"\n{'='*60}")
    print(f"Pipeline Validation Report — {passed}/{len(results)} passed")
    print(f"{'='*60}")
    for r in results:
        row = r.summary_row()
        status = "✅ PASS" if r.passed() else "❌ FAIL"
        print(f"\n{status} | {row['Pipeline']}")
        for k, v in row.items():
            if k != "Pipeline":
                print(f"  {k}: {v}")
```

Results feed into [migration-report.md](migration-report.md) for the final handoff document.
