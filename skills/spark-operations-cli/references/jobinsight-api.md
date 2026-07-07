# JobInsight API Reference

> **Scope**: Copy Spark event logs from Fabric to OneLake for offline analysis using the JobInsight Scala library. This enables Tier 2 diagnostics (local Spark History Server) when online APIs are insufficient.

---

## Overview

JobInsight is a Scala library available on Fabric Spark clusters that provides diagnostic utilities for Spark job analysis. It is **not** available as a standalone package — it must run inside a Fabric Spark notebook or Livy session.

---

## LogUtils.copyEventLog

```scala
import com.microsoft.jobinsight.diagnostic.LogUtils

val contentLength: Long = LogUtils.copyEventLog(
    workspaceId: String,    // Fabric workspace UUID
    artifactId: String,     // Notebook / artifact UUID
    livyId: String,         // Spark Livy session UUID
    jobType: String,        // "sessions", "batches", etc.
    targetDir: String,      // abfss:// path where event logs are written
    overwrite: Boolean,     // true to overwrite existing logs (default: true)
    attemptId: Integer      // YARN attempt number; null = auto-detect, 1 = first attempt
)
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `workspaceId` | `String` | The Fabric workspace UUID containing the Spark session |
| `artifactId` | `String` | The UUID of the artifact (notebook, lakehouse job, etc.) that created the session |
| `livyId` | `String` | The Livy session UUID (from the Spark session list API) |
| `jobType` | `String` | Type of job: `"sessions"` (interactive notebooks), `"batches"` (Spark Job Definitions) |
| `targetDir` | `String` | OneLake abfss:// path for output. Event log files are written here. |
| `overwrite` | `Boolean` | If `true`, overwrites any existing event log at the target path (default: `true`) |
| `attemptId` | `Integer` | YARN application attempt number. Pass `1` for most sessions. Pass `null` for auto-detection. |

### Return Value

Returns a `Long` representing the total number of bytes copied.

### Target Directory Format

The recommended target directory pattern for lakehouse storage:

```
abfss://{workspaceId}@onelake.dfs.fabric.microsoft.com/{lakehouseId}/Files/spark-events/{livyId}/
```

This places event logs under the lakehouse Files section, organized by session.

---

## Requirements

| Requirement | Detail |
|-------------|--------|
| **Fabric Runtime** | ≥ 1.3 (Spark ≥ 3.5). JobInsight is NOT available on earlier runtimes. |
| **Same capacity** | The notebook running JobInsight must execute on the same capacity as the Spark session being debugged. |
| **Execution environment** | Must run on a Fabric Spark cluster (library is pre-installed). |
| **Authentication** | The authenticated user must have access to the source Spark session. |
| **Target permissions** | Target lakehouse directory must be writable (Contributor role). |
| **Language** | **Scala only** — not available in PySpark. |

---

## Attempt ID (7th Parameter)

The `attemptId` parameter controls how `copyEventLog` matches event-log files in blob storage.

**Internal flow:**
1. `CredentialProvider.getEventLogDirSasInfo()` → gets a SAS-scoped directory URL
2. `CredentialProvider.listFiles()` → lists blobs under that directory
3. `CredentialProvider.eventLogNamePattern(attemptId)` → builds a regex to filter files
4. Files matching the regex are copied to `targetDir`

**Regex behavior:**

| `attemptId` value | Generated regex | Matches |
|-------------------|-----------------|---------|
| `null` (auto-detect) | `application_[\d]+_[\d]+(\.inprogress)?` | `application_xxx_0001` only |
| `1` | `application_[\d]+_[\d]+_1(\.inprogress)?` | `application_xxx_0001_1` |
| `2` | `application_[\d]+_[\d]+_2(\.inprogress)?` | `application_xxx_0001_2` |

**Known issue:** Spark event-log files almost always include an attempt suffix (e.g. `_1`). When `attemptId = null`, the regex uses `String.matches()` (full match) and **does not** match file names with the `_1` suffix. Auto-detection queries cluster metadata to resolve the attempt number, but this metadata is garbage-collected within ~3 days of session completion. After that, the call falls back to the `null` regex and silently fails.

**Recommendation:** Always pass `attemptId = 1` unless you know the session had multiple YARN attempts (very rare for interactive notebook sessions).

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ClassNotFoundException: LogUtils` | Running outside Fabric Spark | Must run inside a Fabric notebook |
| `Failed to get event log, please check input parameters` | Event-log file name matching failed (see Attempt ID section) | Pass explicit `attemptId = 1` instead of `null` |
| `AccessDenied on source` | No access to session logs | Verify workspace permissions |
| `AccessDenied on target` | Cannot write to lakehouse | Need Contributor role on target workspace |
| `SessionNotFoundException` | Invalid livyId | Verify the session exists and has completed |

---

## Usage Example

### Direct in Fabric Notebook (Scala cell)

```scala
import com.microsoft.jobinsight.diagnostic.LogUtils

val workspaceId = "4cb9b656-c8f8-485e-a151-e81bb913abc8"
val notebookId  = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
val livyId      = "12345678-1234-1234-1234-123456789abc"
val lakehouseId = "abcdef12-3456-7890-abcd-ef1234567890"

val targetDir = s"abfss://$workspaceId@onelake.dfs.fabric.microsoft.com/$lakehouseId/Files/spark-events/$livyId/"

val bytesWritten = LogUtils.copyEventLog(
    workspaceId, notebookId, livyId,
    "sessions", targetDir, true, 1
)
println(s"Copied $bytesWritten bytes of event logs")
```

### Via Notebook Run API (Automation Pattern)

Since JobInsight is Scala-only and cluster-bound, the recommended automation pattern is:

1. Create a parameterized Scala notebook using a Fabric **parameter cell** (toggle the cell to "Parameter" in the notebook toolbar) to declare default values for `workspaceId`, `livyId`, and `targetDir`
2. Run it via the Fabric Notebook Run API:
   ```bash
   az rest --method post --resource "https://api.fabric.microsoft.com" \
     --url "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/items/$notebookId/jobs/RunNotebook/instances" \
     --body '{"executionData": {"parameters": {"workspaceId": "...", "livyId": "...", "targetDir": "..."}}}'
   ```
3. Poll the Location header for completion (see [COMMON-CLI.md § LRO Pattern](../../../common/COMMON-CLI.md#long-running-operations-lro-pattern))

---

## Downloading Event Logs from OneLake

After `copyEventLog` writes event logs to OneLake, download them locally for the Spark History Server:

```bash
# Get a storage token
TOKEN=$(az account get-access-token --resource https://storage.azure.com --query accessToken -o tsv)

# List event log files
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://onelake.dfs.fabric.microsoft.com/$workspaceId/$lakehouseId/Files/spark-events/$livyId?resource=filesystem&recursive=true" \
  | jq -r '.paths[].name'

# Download each file to local directory
LOCAL_DIR="$HOME/.spark-local/event-logs/$livyId"
mkdir -p "$LOCAL_DIR"

# For each file listed above:
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://onelake.dfs.fabric.microsoft.com/$workspaceId/$lakehouseId/<filepath>" \
  -o "$LOCAL_DIR/<filename>"
```

Then start the local Spark History Server — see [spark-history-server.md](spark-history-server.md).
