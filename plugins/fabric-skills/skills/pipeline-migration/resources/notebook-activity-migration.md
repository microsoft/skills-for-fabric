# Notebook Activity Migration — SynapseNotebook → TridentNotebook

Deep reference for migrating Synapse `SynapseNotebook` pipeline activities to Fabric `TridentNotebook` activities. This is the primary migration path for pipeline-heavy Synapse workloads.

---

## Overview of Changes

| Property | Synapse `SynapseNotebook` | Fabric `TridentNotebook` | Notes |
|---|---|---|---|
| Activity type | `SynapseNotebook` | `TridentNotebook` | Direct rename |
| Notebook reference | `typeProperties.notebook.referenceName` (name string) | `typeProperties.notebookId` (GUID) | Must be the Fabric item GUID |
| Workspace reference | Implicit (same Synapse workspace) | `typeProperties.workspaceId` (GUID) | Must be the Fabric workspace GUID |
| Spark pool | `typeProperties.sparkPool.referenceName` (pool name) | **Removed** | Pool selection moves to the Fabric Environment attached to the notebook |
| Session configuration | `typeProperties.sessionConfiguration` | **Removed** | Driver/executor size moves to Fabric Environment |
| Spark conf overrides | `typeProperties.conf` | **Removed** | Apply via Environment or `%%configure` magic in the notebook |
| Notebook parameters | `typeProperties.parameters` (object) | `typeProperties.parameters` (object) | Unchanged: same key and same value schema (`{ "value": ..., "type": ... }`) |
| Timeout format | `7.00:00:00` (d.hh:mm:ss) | `0.12:00:00` (d.hh:mm:ss) | Synapse default 7 days; Fabric max is 12 hours for interactive — adjust |
| Retry | Same `policy` schema | Same `policy` schema | Compatible |

---

## Before and After: Simple Notebook Activity

### Before (Synapse)

```json
{
  "name": "Run ETL Notebook",
  "type": "SynapseNotebook",
  "dependsOn": [],
  "policy": {
    "timeout": "7.00:00:00",
    "retry": 0,
    "retryIntervalInSeconds": 30,
    "secureOutput": false,
    "secureInput": false
  },
  "typeProperties": {
    "notebook": {
      "referenceName": "ETLNotebook",
      "type": "NotebookReference"
    },
    "sparkPool": {
      "referenceName": "SalesSparkPool",
      "type": "BigDataPoolReference"
    }
  }
}
```

### After (Fabric)

```json
{
  "name": "Run ETL Notebook",
  "type": "TridentNotebook",
  "dependsOn": [],
  "policy": {
    "timeout": "0.12:00:00",
    "retry": 0,
    "retryIntervalInSeconds": 30,
    "secureOutput": false,
    "secureInput": false
  },
  "typeProperties": {
    "notebookId": "aaaaaaaa-1111-2222-3333-444444444444",
    "workspaceId": "bbbbbbbb-5555-6666-7777-888888888888"
  }
}
```

---

## Before and After: Parameterized Notebook Activity

### Before (Synapse)

```json
{
  "name": "Run Parameterized ETL",
  "type": "SynapseNotebook",
  "dependsOn": [
    {
      "activity": "Check Source",
      "dependencyConditions": ["Succeeded"]
    }
  ],
  "policy": {
    "timeout": "1.00:00:00",
    "retry": 2,
    "retryIntervalInSeconds": 60,
    "secureOutput": false,
    "secureInput": false
  },
  "typeProperties": {
    "notebook": {
      "referenceName": "IngestNotebook",
      "type": "NotebookReference"
    },
    "sparkPool": {
      "referenceName": "MediumSparkPool",
      "type": "BigDataPoolReference"
    },
    "sessionConfiguration": {
      "driverMemory": "28g",
      "driverCores": 4,
      "executorMemory": "28g",
      "executorCores": 4,
      "numExecutors": 2,
      "conf": {
        "spark.dynamicAllocation.enabled": "false"
      }
    },
    "parameters": {
      "inputPath": {
        "value": "/data/sales/raw",
        "type": "string"
      },
      "outputPath": {
        "value": "/data/sales/bronze",
        "type": "string"
      },
      "runDate": {
        "value": {
          "value": "@pipeline().parameters.runDate",
          "type": "Expression"
        },
        "type": "string"
      },
      "batchSize": {
        "value": {
          "value": "@int(pipeline().parameters.batchSize)",
          "type": "Expression"
        },
        "type": "int"
      },
      "enableDebugLogging": {
        "value": false,
        "type": "bool"
      }
    }
  }
}
```

### After (Fabric)

```json
{
  "name": "Run Parameterized ETL",
  "type": "TridentNotebook",
  "dependsOn": [
    {
      "activity": "Check Source",
      "dependencyConditions": ["Succeeded"]
    }
  ],
  "policy": {
    "timeout": "0.12:00:00",
    "retry": 2,
    "retryIntervalInSeconds": 60,
    "secureOutput": false,
    "secureInput": false
  },
  "typeProperties": {
    "notebookId": "cccccccc-1111-2222-3333-444444444444",
    "workspaceId": "dddddddd-5555-6666-7777-888888888888",
    "parameters": {
      "inputPath": {
        "value": "/data/sales/raw",
        "type": "string"
      },
      "outputPath": {
        "value": "/data/sales/bronze",
        "type": "string"
      },
      "runDate": {
        "value": {
          "value": "@pipeline().parameters.runDate",
          "type": "Expression"
        },
        "type": "string"
      },
      "batchSize": {
        "value": {
          "value": "@int(pipeline().parameters.batchSize)",
          "type": "Expression"
        },
        "type": "int"
      },
      "enableDebugLogging": {
        "value": false,
        "type": "bool"
      }
    }
  }
}
```

> **Note**: `sessionConfiguration` (driver/executor sizing) is removed. Configure the Fabric Environment for this notebook with the equivalent node type and pool settings. For `SalesSparkPool` with 4 cores + 28g memory, use a Fabric **Large** node (8 vCores, 56 GB RAM) or configure a custom Environment.

---

## Spark Pool → Fabric Environment Mapping

When a Synapse `SynapseNotebook` activity specifies a `sparkPool`, that pool's configuration must be replicated in a Fabric Environment attached to the notebook.

### Pool Size Equivalents

| Synapse Pool Node Size | Approx. Fabric Node Type | `sessionConfiguration` |
|---|---|---|
| Small (4 vCores, 28 GB) | **Small** (4 vCores, 32 GB) | `driverCores: 4, driverMemory: "28g"` |
| Medium (8 vCores, 56 GB) | **Medium** (8 vCores, 64 GB) | `driverCores: 8, driverMemory: "56g"` |
| Large (16 vCores, 112 GB) | **Large** (16 vCores, 128 GB) | `driverCores: 16, driverMemory: "112g"` |
| XLarge (32 vCores, 224 GB) | **XLarge** (32 vCores, 256 GB) | `driverCores: 32` |
| XXLarge (64 vCores, 448 GB) | **XXLarge** (64 vCores, 512 GB) | `driverCores: 64` |

> If multiple `SynapseNotebook` activities reference different pools, create a Fabric Environment per pool profile and attach the correct Environment to each notebook. Notebook-level Environment attachment is set in the Fabric Notebook's settings, not in the pipeline activity JSON.

### Session Configuration Fields

Remove these fields from `sessionConfiguration` — they are either auto-managed by Fabric or set via Fabric Environment:

| `sessionConfiguration` field | Disposition |
|---|---|
| `driverMemory` | ➜ Set in Fabric Environment node size |
| `driverCores` | ➜ Set in Fabric Environment node size |
| `executorMemory` | ➜ Set in Fabric Environment node size |
| `executorCores` | ➜ Set in Fabric Environment node size |
| `numExecutors` | ➜ Fabric uses autoscaling; set min/max via Environment |
| `conf.*` | ➜ Move to Fabric Environment Spark properties, or use `%%configure` magic in the notebook |

---

## Notebook Parameter Type Mapping

Parameter types are the same in Synapse and Fabric — the schema does not change.

| Type String | Synapse | Fabric | Notes |
|---|---|---|---|
| `"string"` | ✅ | ✅ | Identical |
| `"int"` | ✅ | ✅ | Identical |
| `"float"` | ✅ | ✅ | Identical |
| `"bool"` | ✅ | ✅ | Identical |

Expression parameters use the `{"value": "<expr>", "type": "Expression"}` envelope — identical in both.

---

## Obtaining the Fabric Notebook GUID

### Method 1: List All Notebooks in Workspace

```bash
FABRIC_WS_ID="<workspace-id>"
FABRIC_TOKEN="<fabric-token>"

az rest --method GET \
  --headers "Authorization=Bearer ${FABRIC_TOKEN}" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${FABRIC_WS_ID}/notebooks" \
  --query "value[].{name:displayName, id:id}" -o table
```

### Method 2: Filter by Name (JMESPath)

```bash
az rest --method GET \
  --headers "Authorization=Bearer ${FABRIC_TOKEN}" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${FABRIC_WS_ID}/notebooks" \
  --query "value[?displayName=='IngestNotebook'].id | [0]" -o tsv
```

### Method 3: Python — Build Full Name→GUID Map

```python
import os
import requests
from urllib.parse import quote

_HTTP_TIMEOUT = (
    float(os.environ.get("FABRIC_HTTP_CONNECT_TIMEOUT", 10)),
    float(os.environ.get("FABRIC_HTTP_READ_TIMEOUT", 60)),
)

def get_notebook_guid_map(workspace_id: str, fabric_token: str) -> dict[str, str]:
    """Return {notebookName: notebookId} for all notebooks in the workspace."""
    headers = {"Authorization": f"Bearer {fabric_token}"}
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks"
    notebooks = {}
    while url:
        r = requests.get(url, headers=headers, timeout=_HTTP_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        for nb in data.get("value", []):
            notebooks[nb["displayName"]] = nb["id"]
        cont = data.get("continuationToken")
        # Fabric continuation tokens are base64-like and routinely contain '+',
        # '/', and '=' characters that must be percent-encoded; concatenating
        # the raw token into the query string breaks pagination.
        url = (
            f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks"
            f"?continuationToken={quote(cont, safe='')}"
        ) if cont else None
    return notebooks

# Usage
notebook_map = get_notebook_guid_map(FABRIC_WS_ID, FABRIC_TOKEN)
# notebook_map = {"IngestNotebook": "cccc...", "ETLNotebook": "dddd..."}
```

---

## Automated Transformation Script

Use this to transform all `SynapseNotebook` activities in a pipeline definition:

```python
import json, copy
from typing import Optional

def transform_notebook_activity(activity: dict, notebook_map: dict, workspace_id: str) -> dict:
    """
    Convert a SynapseNotebook activity to a TridentNotebook activity.
    
    Args:
        activity: The Synapse activity dict to transform.
        notebook_map: {synapseNotebookName: fabricNotebookId}
        workspace_id: Fabric workspace GUID
    
    Returns:
        Transformed activity dict.
    
    Raises:
        KeyError: If the notebook name is not found in notebook_map.
    """
    if activity.get("type") != "SynapseNotebook":
        return activity  # Not a notebook activity — skip

    activity = copy.deepcopy(activity)
    props = activity.get("typeProperties", {})

    # 1. Get and validate notebook reference
    notebook_name = props.get("notebook", {}).get("referenceName")
    if not notebook_name:
        raise ValueError(f"Activity '{activity['name']}' has no notebook.referenceName")
    if notebook_name not in notebook_map:
        # Show a bounded sample plus total count instead of dumping the full
        # notebook map — real workspaces can have hundreds of notebooks and
        # the full list floods logs. Matches the workspace-not-found and
        # notebook-not-found hints in pipeline-orchestrator.md.
        available = sorted(notebook_map.keys())
        sample = available[:5]
        hint = (f"first {len(sample)} of {len(available)}: {sample}"
                if len(available) > 5 else str(sample))
        raise KeyError(
            f"Notebook '{notebook_name}' not found in Fabric workspace "
            f"({hint})."
        )
    notebook_id = notebook_map[notebook_name]

    # 2. Carry notebook parameters over unchanged: the Fabric TridentNotebook schema
    #    uses the same `parameters` key and value shape as Synapse.
    parameters = props.pop("parameters", None)

    # 3. Build new typeProperties (drop sparkPool, sessionConfiguration, conf, notebook)
    new_props = {
        "notebookId": notebook_id,
        "workspaceId": workspace_id,
    }
    if parameters:
        new_props["parameters"] = parameters

    # 4. Apply changes
    activity["type"] = "TridentNotebook"
    activity["typeProperties"] = new_props

    # 5. Adjust timeout: Fabric max is 0.12:00:00 (12 hours = 43200 s)
    policy = activity.get("policy", {})
    timeout = policy.get("timeout", "7.00:00:00")
    parsed = _parse_timeout_seconds(timeout)
    # Only clamp when we positively know the timeout exceeds the Fabric max.
    # When _parse_timeout_seconds returns None (unrecognized format), preserve
    # the original value so a valid custom timeout isn't silently overwritten
    # — and so a malformed value isn't silently treated as "<= 12 h" either.
    if parsed is not None and parsed > 43200:
        policy["timeout"] = "0.12:00:00"
        activity["policy"] = policy

    return activity


def _parse_timeout_seconds(timeout_str: str) -> Optional[int]:
    """Parse d.hh:mm:ss or hh:mm:ss into total seconds.

    Returns None on any parse error so the caller treats the value as
    "unknown" and preserves it unchanged, rather than mis-clamping it.
    Silently returning 0 here would let invalid timeout strings slip
    past the 12 h Fabric clamp (0 <= 43200), defeating the safety check
    described elsewhere; align with the orchestrator's fix_timeout(),
    which also preserves unrecognized values.

    Uses typing.Optional for Python 3.9 compatibility (the `int | None`
    PEP 604 syntax requires 3.10+).
    """
    try:
        # Treat any falsy / non-string input as "unknown" so the caller
        # preserves the original value rather than mis-clamping. Covers
        # the explicit-null case (policy.timeout present but null in the
        # source JSON) which would otherwise raise TypeError from
        # `"." in timeout_str` below.
        if not isinstance(timeout_str, str) or not timeout_str:
            return None
        if "." in timeout_str:
            day_part, time_part = timeout_str.split(".", 1)
            days = int(day_part)
        else:
            time_part = timeout_str
            days = 0
        h, m, s = time_part.split(":")
        return days * 86400 + int(h) * 3600 + int(m) * 60 + int(s)
    except (ValueError, AttributeError, TypeError):
        return None


def transform_pipeline_notebook_activities(
    pipeline_def: dict,
    notebook_map: dict,
    workspace_id: str
) -> tuple[dict, list[str]]:
    """
    Transform all SynapseNotebook activities in a pipeline definition.
    
    Returns:
        (transformed_pipeline_def, list_of_error_messages)
    """
    import copy
    pipeline_def = copy.deepcopy(pipeline_def)
    errors = []

    def transform_activities(activities: list) -> list:
        result = []
        for activity in activities:
            if activity.get("type") == "SynapseNotebook":
                try:
                    result.append(transform_notebook_activity(activity, notebook_map, workspace_id))
                except (KeyError, ValueError) as e:
                    errors.append(str(e))
                    result.append(activity)  # keep original on error
            else:
                # Recurse into nested containers
                for key in ("activities", "ifTrueActivities", "ifFalseActivities", "defaultActivities"):
                    if key in activity.get("typeProperties", {}):
                        activity["typeProperties"][key] = transform_activities(
                            activity["typeProperties"][key]
                        )
                if "cases" in activity.get("typeProperties", {}):
                    for case in activity["typeProperties"]["cases"]:
                        case["activities"] = transform_activities(case.get("activities", []))
                result.append(activity)
        return result

    props = pipeline_def.get("properties", {})
    props["activities"] = transform_activities(props.get("activities", []))

    # Also replace globalParameters expressions with libraryVariables.
    # Walk the object tree and rewrite only ADF expression strings
    # (string values starting with "@"). A blind serialized-JSON replace
    # could mutate unrelated literal text — e.g. descriptions, annotations,
    # or embedded code snippets containing the substring in prose form.
    #
    # Keep in sync with the equivalent helpers in:
    #   - skills/pipeline-migration/resources/pipeline-orchestrator.md
    #     (_rewrite_expressions inside the per-pipeline migration loop)
    #   - skills/pipeline-migration/resources/global-parameters-to-variable-library.md
    #     (rewrite_global_parameters in the Expression Rewrite section)
    def _rewrite_expressions(node):
        if isinstance(node, dict):
            # Only rewrite within the canonical ADF/Fabric expression dict
            # shape ({"value": "@...", "type": "Expression"}) so plain text
            # in description/annotation fields isn't accidentally mutated.
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

    pipeline_def = _rewrite_expressions(pipeline_def)

    return pipeline_def, errors


# --- Example usage ---
if __name__ == "__main__":
    FABRIC_WORKSPACE_ID = "dddddddd-5555-6666-7777-888888888888"

    notebook_map = {
        "IngestNotebook": "cccccccc-1111-2222-3333-444444444444",
        "TransformNotebook": "eeeeeeee-9999-aaaa-bbbb-cccccccccccc",
    }

    with open("synapse_pipeline.json") as f:
        pipeline_def = json.load(f)

    transformed, errors = transform_pipeline_notebook_activities(
        pipeline_def, notebook_map, FABRIC_WORKSPACE_ID
    )

    if errors:
        print("⚠️  Transformation errors (notebook GUIDs not found):")
        for e in errors:
            print(f"   {e}")

    with open("fabric_pipeline.json", "w") as f:
        json.dump(transformed, f, indent=2)

    print(f"✅ Transformation complete. Output: fabric_pipeline.json")
```

---

## Notebook Return Values (Output)

Synapse notebook activities can return values to the pipeline via `mssparkutils.notebook.exit()`. The same pattern works in Fabric via `notebookutils.notebook.exit()`.

The returned value is accessible downstream via:
```
@activity('Run ETL Notebook').output.runOutput
```

This expression syntax is **identical** in both Synapse and Fabric pipelines.

### Synapse Notebook — Return Value

```python
# In the Synapse notebook
mssparkutils.notebook.exit('{"rowsProcessed": 1000, "status": "success"}')
```

### Fabric Notebook — Return Value (same pattern, new namespace)

```python
# In the Fabric notebook (after synapse-migration skill)
notebookutils.notebook.exit('{"rowsProcessed": 1000, "status": "success"}')
```

### Consuming the Return Value in the Pipeline

```json
{
  "name": "Check Rows Processed",
  "type": "IfCondition",
  "dependsOn": [
    { "activity": "Run ETL Notebook", "dependencyConditions": ["Succeeded"] }
  ],
  "typeProperties": {
    "expression": {
      "value": "@greaterOrEquals(int(activity('Run ETL Notebook').output.runOutput), 1)",
      "type": "Expression"
    },
    "ifFalseActivities": [
      {
        "name": "Fail - No Rows",
        "type": "Fail",
        "typeProperties": {
          "message": "Notebook returned zero rows processed",
          "errorCode": "EmptyResult"
        }
      }
    ]
  }
}
```

---

## Handling Multiple Pools (Multiple Environments)

When a pipeline calls notebooks that use different Spark pools, each notebook must have the correct Fabric Environment attached. The pipeline activity itself does not specify the environment — it's set on the notebook item in Fabric.

### Recommended Setup

1. Create a Fabric Environment per pool profile (e.g., `env-small`, `env-large`)
2. Attach the appropriate Environment to each Fabric Notebook (via notebook Settings → Spark Compute)
3. In the pipeline, reference notebooks by GUID — the Environment attachment is already set on the notebook

> This is a change from Synapse where the pipeline activity controlled which pool ran the notebook. In Fabric, the notebook owns its Environment selection.

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Using notebook display name instead of GUID | `notebookId` validation error at pipeline save | Get GUID from `GET /v1/workspaces/{wsId}/notebooks` |
| Leaving `sparkPool` in `typeProperties` | Schema validation error or ignored | Remove `sparkPool` block entirely |
| Renaming `parameters` to `notebookParameters` | `notebookParameters` is not a TridentNotebook type property, so the values are not passed to the notebook and it runs with its defaults | Keep the key as `parameters`, the documented TridentNotebook property |
| Timeout > 12 hours | Pipeline activity times out or validation error | Change to `0.12:00:00` (12h max for TridentNotebook) |
| Keeping `sessionConfiguration` | Ignored by Fabric; notebook uses its attached Environment | Remove `sessionConfiguration` block |
| Notebook not yet migrated to Fabric | `notebookId` not in `notebook_map` | Run **synapse-migration** skill for notebook content migration first |
