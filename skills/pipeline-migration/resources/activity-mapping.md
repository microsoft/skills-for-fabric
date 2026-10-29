# Activity Type Mapping — Synapse → Fabric Data Factory

Complete mapping of Synapse Analytics pipeline activity types to their Fabric Data Factory equivalents, with before/after JSON examples and parking decisions for unsupported activities.

---

## Activity Status Legend

| Symbol | Meaning |
|---|---|
| ✅ Compatible | Activity type name and `typeProperties` are identical or near-identical — minimal changes required |
| ✅ Migrated | Activity type name changes or `typeProperties` require structural edits |
| ⚠️ Rewrite | Activity has no direct equivalent; must be rewritten using a supported type |
| ⛔ Parked | No viable Fabric equivalent — activity is logged as a blocker and skipped |

---

## Full Activity Mapping Table

| Synapse `type` | Fabric `type` | Status | Key Changes |
|---|---|---|---|
| `SynapseNotebook` | `TridentNotebook` | ✅ Migrated | Type rename, ref by GUID, drop `sparkPool`/`sessionConfiguration`, keep `parameters` unchanged — see [notebook-activity-migration.md](notebook-activity-migration.md) |
| `Copy` | `Copy` | ✅ Migrated | Dataset refs inlined — see [dataset-inlining.md](dataset-inlining.md) |
| `Lookup` | `Lookup` | ✅ Migrated | Dataset ref inlined |
| `GetMetadata` | `GetMetadata` | ✅ Migrated | Dataset ref inlined |
| `Validation` | `GetMetadata` + `IfCondition` | ✅ Migrated | Split into 2 activities — see [§ Validation Activity](#validation-activity--getmetadata--ifcondition) |
| `ForEach` | `ForEach` | ✅ Compatible | Update connection refs in inner activities |
| `IfCondition` | `IfCondition` | ✅ Compatible | Update connection refs in inner activities |
| `Switch` | `Switch` | ✅ Compatible | Update connection refs in inner activities |
| `Until` | `Until` | ✅ Compatible | Update connection refs in inner activities |
| `Wait` | `Wait` | ✅ Compatible | None |
| `Fail` | `Fail` | ✅ Compatible | None |
| `SetVariable` | `SetVariable` | ✅ Compatible | None |
| `AppendVariable` | `AppendVariable` | ✅ Compatible | None |
| `ExecutePipeline` | `ExecutePipeline` | ✅ Compatible | Add `workspaceId` to `typeProperties` — see [§ ExecutePipeline](#executepipeline) |
| `WebActivity` | `WebActivity` | ✅ Compatible | Authentication method differences — see [§ WebActivity](#webactivity) |
| `Script` | `Script` | ✅ Compatible | Update connection reference name to Fabric connection |
| `Delete` | `Delete` | ✅ Migrated | Dataset ref inlined |
| `Filter` | `Filter` | ✅ Compatible | None |
| `SparkJobDefinition` | `SparkJobDefinition` | ✅ Migrated | Replace SJD name reference with Fabric SJD GUID; update `workspaceId` |
| `HDInsightSpark` | `TridentNotebook` or `SparkJobDefinition` | ⚠️ Rewrite | HDInsight clusters don't exist in Fabric; rewrite workload as Fabric notebook or SJD |
| `AzureMLBatchExecution` | `WebActivity` | ⚠️ Rewrite | Call Azure ML REST endpoint directly via WebActivity |
| `AzureMLUpdateResource` | `WebActivity` | ⚠️ Rewrite | Call Azure ML REST endpoint directly via WebActivity |
| `AzureFunctionActivity` | `WebActivity` | ⚠️ Rewrite | Use function URL + `x-functions-key` header; see [§ AzureFunction → WebActivity](#azurefunctionactivity--webactivity) |
| `DatabricksNotebook` | ⛔ Parked | See [pipeline-gotchas.md](pipeline-gotchas.md) | No native Fabric equivalent |
| `DatabricksSparkJar` | ⛔ Parked | See [pipeline-gotchas.md](pipeline-gotchas.md) | No native Fabric equivalent |
| `DatabricksSparkPython` | ⛔ Parked | See [pipeline-gotchas.md](pipeline-gotchas.md) | No native Fabric equivalent |
| `ExecuteSSISPackage` | ⛔ Parked | See [pipeline-gotchas.md](pipeline-gotchas.md) | No Fabric equivalent |
| `AzureBatch` | ⛔ Parked | See [pipeline-gotchas.md](pipeline-gotchas.md) | No Fabric equivalent |
| `Custom` | ⛔ Parked | See [pipeline-gotchas.md](pipeline-gotchas.md) | No Fabric equivalent |
| `MapReduce` | ⛔ Parked | No Fabric equivalent | HDInsight MapReduce not available in Fabric |
| `Pig` | ⛔ Parked | No Fabric equivalent | HDInsight Pig not available in Fabric |
| `Hive` | ⛔ Parked | No Fabric equivalent | HDInsight Hive not available in Fabric |

---

## Compatible Activities — What to Check

Even for "compatible" activity types, verify these common fields during migration:

1. **`dependsOn`** — activity dependency expressions are identical; preserve as-is
2. **`policy`** — timeout/retry format is compatible; preserve as-is
3. **Connection references** — any `linkedServiceName` in `typeProperties` must be replaced with a Fabric Connection name
4. **Expression syntax** — `@pipeline().parameters`, `@activity().output`, `@variables()` — all compatible
5. **`@pipeline().globalParameters`** — must be replaced with `@pipeline().libraryVariables` — see [global-parameters-to-variable-library.md](global-parameters-to-variable-library.md)

---

## Validation Activity → GetMetadata + IfCondition

The `Validation` activity in Synapse waits until a file/folder exists or a minimum size is met, then succeeds. Fabric has no `Validation` type — it must be replaced with two activities.

### Before (Synapse)

```json
{
  "name": "Validate Source File",
  "type": "Validation",
  "dependsOn": [],
  "typeProperties": {
    "dataset": {
      "referenceName": "SourceFileDataset",
      "type": "DatasetReference"
    },
    "timeout": "7.00:00:00",
    "sleep": 10,
    "minimumSize": 1024,
    "childItems": false
  }
}
```

### After (Fabric) — Until Loop + IfCondition

`GetMetadata` returns `exists: false` rather than failing when a file is missing, so `policy.retry` cannot drive polling — `retry` only fires on activity *failure*. Use an explicit `Until` loop instead: poll `GetMetadata`, sleep between iterations, and break out when the file appears (or when the outer pipeline times out). A trailing `IfCondition` enforces the `minimumSize` predicate the same way as the Validation activity's `minimumSize` field.

```json
[
  {
    "name": "Wait For Source File",
    "type": "Until",
    "dependsOn": [],
    "typeProperties": {
      "expression": {
        "value": "@activity('Get Source File Metadata').output.exists",
        "type": "Expression"
      },
      "timeout": "7.00:00:00",
      "activities": [
        {
          "name": "Get Source File Metadata",
          "type": "GetMetadata",
          "policy": {
            "timeout": "0.00:05:00",
            "retry": 0
          },
          "typeProperties": {
            "fieldList": ["exists", "size"],
            "storeSettings": {
              "type": "AzureBlobFSReadSettings",
              "recursive": false
            },
            "formatSettings": {
              "type": "BinaryReadSettings"
            }
          },
          "linkedService": {
            "referenceName": "<fabric-connection-name>",
            "type": "LinkedServiceReference"
          }
        },
        {
          "name": "Sleep Between Polls",
          "type": "Wait",
          "dependsOn": [
            { "activity": "Get Source File Metadata", "dependencyConditions": ["Completed"] }
          ],
          "typeProperties": {
            "waitTimeInSeconds": 10
          }
        }
      ]
    }
  },
  {
    "name": "Assert Source File Valid",
    "type": "IfCondition",
    "dependsOn": [
      {
        "activity": "Wait For Source File",
        "dependencyConditions": ["Succeeded"]
      }
    ],
    "typeProperties": {
      "expression": {
        "value": "@and(activity('Get Source File Metadata').output.exists, greaterOrEquals(activity('Get Source File Metadata').output.size, 1024))",
        "type": "Expression"
      },
      "ifFalseActivities": [
        {
          "name": "Fail - Source File Invalid",
          "type": "Fail",
          "typeProperties": {
            "message": {
              "value": "@concat('Source file does not exist or is too small. Exists: ', string(activity('Get Source File Metadata').output.exists), ', Size: ', string(activity('Get Source File Metadata').output.size))",
              "type": "Expression"
            },
            "errorCode": "ValidationFailed"
          }
        }
      ]
    }
  }
]
```

### Mapping Synapse Validation Properties

| Synapse `typeProperties` | Fabric Replacement |
|---|---|
| `timeout` | Set as `typeProperties.timeout` on the `Until` loop — caps the total polling window |
| `sleep` (retry interval) | `waitTimeInSeconds` on the inner `Wait` activity inside the `Until` loop |
| `minimumSize` | Use `greaterOrEquals(activity(...).output.size, <minimumSize>)` in the trailing `IfCondition` expression |
| `childItems: true` | Use `fieldList: ["childItems"]` in `GetMetadata` and check `length(activity(...).output.childItems) > 0` |
| `childItems: false` | Use `fieldList: ["exists", "size"]` — validate file presence and size |

---

## ExecutePipeline

### Before (Synapse)

```json
{
  "name": "Run Child Pipeline",
  "type": "ExecutePipeline",
  "typeProperties": {
    "pipeline": {
      "referenceName": "ChildPipeline",
      "type": "PipelineReference"
    },
    "waitOnCompletion": true,
    "parameters": {
      "runDate": {
        "value": "@pipeline().parameters.runDate",
        "type": "Expression"
      }
    }
  }
}
```

### After (Fabric)

```json
{
  "name": "Run Child Pipeline",
  "type": "ExecutePipeline",
  "typeProperties": {
    "pipeline": {
      "referenceName": "<fabric-child-pipeline-item-id>",
      "type": "PipelineReference"
    },
    "workspaceId": "<fabric-workspace-id>",
    "waitOnCompletion": true,
    "parameters": {
      "runDate": {
        "value": "@pipeline().parameters.runDate",
        "type": "Expression"
      }
    }
  }
}
```

> **Key change**: Add `workspaceId` to `typeProperties`. `workspaceId` is required even for same-workspace child pipelines — Fabric does not fall back to the current workspace the way Synapse did (see [PG7](pipeline-gotchas.md#pg7--executepipeline-must-include-workspaceid)). The `pipeline.referenceName` should be the Fabric item ID (GUID) of the child pipeline.

---

## WebActivity

Compatible in Fabric with minor authentication differences.

### Authentication Changes

| Synapse Auth Method | Fabric Equivalent |
|---|---|
| `MSI` (Managed Service Identity) | `MSI` — works in Fabric with workspace identity |
| `Basic` | `Basic` — compatible |
| `ClientCertificate` | `ClientCertificate` — compatible |
| None (anonymous) | Same |

```json
{
  "name": "Call REST API",
  "type": "WebActivity",
  "typeProperties": {
    "url": "https://api.example.com/data",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "value": "@json(concat('{\"date\":\"', pipeline().parameters.runDate, '\"}'))",
      "type": "Expression"
    },
    "authentication": {
      "type": "MSI",
      "resource": "https://management.azure.com/"
    }
  }
}
```

---

## AzureFunctionActivity → WebActivity

Fabric has no `AzureFunctionActivity` type. Rewrite using `WebActivity` with the function URL and key.

### Before (Synapse)

```json
{
  "name": "Run Azure Function",
  "type": "AzureFunctionActivity",
  "typeProperties": {
    "functionLinkedService": {
      "referenceName": "MyFunctionAppLinkedService",
      "type": "LinkedServiceReference"
    },
    "functionName": "ProcessData",
    "method": "POST",
    "body": {
      "value": "@pipeline().parameters.inputPayload",
      "type": "Expression"
    }
  }
}
```

### After (Fabric)

Use two activities: a `WebActivity` to fetch the host key from Key Vault, then a `WebActivity` to invoke the function. The function key is a **secret** and must not be stored in a Variable Library (Variable Libraries are not a secrets store — see secret-hygiene guidance in `pipeline-gotchas.md`).

```json
[
  {
    "name": "Get Function Key",
    "type": "WebActivity",
    "policy": {
      "secureInput": true,
      "secureOutput": true
    },
    "typeProperties": {
      "url": "https://<vault-name>.vault.azure.net/secrets/function-host-key?api-version=7.4",
      "method": "GET",
      "authentication": {
        "type": "MSI",
        "resource": "https://vault.azure.net"
      }
    }
  },
  {
    "name": "Run Azure Function",
    "type": "WebActivity",
    "dependsOn": [
      { "activity": "Get Function Key", "dependencyConditions": ["Succeeded"] }
    ],
    "policy": {
      "secureInput": true
    },
    "typeProperties": {
      "url": "https://<functionapp>.azurewebsites.net/api/ProcessData",
      "method": "POST",
      "headers": {
        "x-functions-key": {
          "value": "@activity('Get Function Key').output.value",
          "type": "Expression"
        },
        "Content-Type": "application/json"
      },
      "body": {
        "value": "@pipeline().parameters.inputPayload",
        "type": "Expression"
      }
    }
  }
]
```

> **Do not** store the function host key in a Variable Library — Variable Library values are visible in run history and to anyone with read access to the workspace. Fetch the key from Key Vault at runtime via `WebActivity` with `secureInput`/`secureOutput`, as shown above. Variable Library is appropriate for non-sensitive config (environment names, URLs, table names) only.

---

## HDInsightSpark → TridentNotebook or SparkJobDefinition

Synapse `HDInsightSpark` activities run PySpark scripts on an HDInsight cluster. The equivalent in Fabric is a `TridentNotebook` (for interactive-style) or `SparkJobDefinition` (for production batch jobs).

### Recommended Rewrite Path

1. Convert the HDInsight PySpark script into a Fabric Notebook or SJD
2. Migrate any `mssparkutils` references using the **synapse-migration** skill
3. Reference the Fabric Notebook or SJD via `TridentNotebook` or `SparkJobDefinition` activity

### Before (Synapse HDInsightSpark)

```json
{
  "name": "Run Spark Script",
  "type": "HDInsightSpark",
  "typeProperties": {
    "rootPath": "adlscontainer/scripts",
    "entryFilePath": "process_data.py",
    "arguments": ["--date", "@pipeline().parameters.runDate"],
    "sparkJobLinkedService": {
      "referenceName": "HDInsightLinkedService",
      "type": "LinkedServiceReference"
    }
  }
}
```

### After (Fabric TridentNotebook)

```json
{
  "name": "Run Spark Script",
  "type": "TridentNotebook",
  "typeProperties": {
    "notebookId": "<fabric-notebook-guid>",
    "workspaceId": "<fabric-workspace-guid>",
    "parameters": {
      "runDate": {
        "value": {
          "value": "@pipeline().parameters.runDate",
          "type": "Expression"
        },
        "type": "string"
      }
    }
  }
}
```

> If the script uses `sys.argv` argument passing, convert it to use `notebookutils.notebook.getParameterValues()` or declare notebook cell parameters.

---

## Inner Activity Recursion

`ForEach`, `IfCondition`, `Switch`, and `Until` contain nested activities. Apply all migration transformations recursively to their inner activity arrays:

| Parent Activity | Inner Activity Array Keys |
|---|---|
| `ForEach` | `activities` |
| `IfCondition` | `ifTrueActivities`, `ifFalseActivities` |
| `Switch` | `cases[].activities`, `defaultActivities` |
| `Until` | `activities` |

```python
INNER_ACTIVITY_KEYS = {
    "ForEach": ["activities"],
    "IfCondition": ["ifTrueActivities", "ifFalseActivities"],
    "Switch": ["defaultActivities"],  # also cases[i].activities
    "Until": ["activities"],
}

def transform_activity(activity, notebook_map, connection_map, dataset_map):
    """Recursively transform an activity and all nested inner activities."""
    activity_type = activity.get("type")
    
    # Transform this activity
    activity = apply_type_transform(activity, notebook_map, connection_map, dataset_map)
    
    # Recurse into inner activities
    inner_keys = INNER_ACTIVITY_KEYS.get(activity_type, [])
    for key in inner_keys:
        inner = activity.get("typeProperties", {}).get(key, [])
        activity["typeProperties"][key] = [
            transform_activity(a, notebook_map, connection_map, dataset_map)
            for a in inner
        ]
    
    # Special case: Switch has cases with nested activities
    if activity_type == "Switch":
        cases = activity.get("typeProperties", {}).get("cases", [])
        for case in cases:
            case["activities"] = [
                transform_activity(a, notebook_map, connection_map, dataset_map)
                for a in case.get("activities", [])
            ]
    
    return activity
```
