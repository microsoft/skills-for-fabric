# Migration Troubleshooting Guide

Common migration failures, edge cases, and resolution steps. Items are flagged during migration and surfaced in the [migration report](migration-report.md) with links back to the relevant section here.

> **Philosophy**: The legacy notebook and Spark job definition issues in this guide do **not** block artifact copying; affected items are copied as-is, failures are logged, and this guide is linked from the report for post-migration remediation. This does not override fail-closed conversion gates in other migration paths. In particular, Dedicated SQL Pool objects classified as `ManualReviewRequired` are not converted or deployed until the required decision or approval is recorded.

---

## G1: `spark.read.synapsesql()` — No Direct Fabric Equivalent

**Flag ID**: `SYNAPSESQL_NO_EQUIVALENT`

**When it fires**: Code audit detects `synapsesql` pattern in a notebook or SJD.

**Symptom**: After migration, running the notebook fails with:
```
AnalysisException: Failed to find data source: synapsesql
```

**Root cause**: The `spark.read.synapsesql()` connector reads from Synapse Dedicated SQL Pools. This connector does not exist in Fabric.

### Resolution Options

| Option | When to Use | Steps |
|---|---|---|
| **A: Lakehouse shortcut** | Data is in ADLS Gen2 behind the Dedicated SQL Pool (external tables) | Create a OneLake shortcut to the source storage → read as Delta/Parquet. See [connectivity-migration.md](connectivity-migration.md) |
| **B: Fabric Warehouse JDBC** | Data must come from a SQL endpoint (Dedicated Pool or Fabric Warehouse) | Replace with JDBC read using `notebookutils.credentials.getToken()` for auth |
| **C: Data pipeline** | The notebook was doing bulk reads from SQL that should be a pipeline activity | Create a Fabric Data Pipeline with a Copy activity instead |

### Code Example — Option B (JDBC)

```python
# ❌ BEFORE — Synapse
df = spark.read.synapsesql("mypool.dbo.FactSales")

# ✅ AFTER — Fabric (JDBC to SQL endpoint)
jdbc_url = "jdbc:sqlserver://myserver.sql.azuresynapse.net:1433;database=mypool"
token = notebookutils.credentials.getToken("https://database.windows.net/")

df = (spark.read
    .format("jdbc")
    .option("url", jdbc_url)
    .option("dbtable", "dbo.FactSales")
    .option("accessToken", token)
    .option("encrypt", "true")
    .option("hostNameInCertificate", "*.sql.azuresynapse.net")
    .load())
```

> **See also**: [connector-refactoring.md § spark.read.synapsesql()](connector-refactoring.md#sparkreadsynapsesql--synapse-sql-connector) for the full before/after pattern.

---

## G2: Custom Library Version Conflicts with Fabric Runtime

**Flag ID**: `LIBRARY_VERSION_CONFLICT`

**When it fires**: Environment publish fails, or a notebook import fails with version resolution errors. Also flagged when Synapse pool libraries specify versions incompatible with Fabric Runtime 1.3 built-ins.

**Symptom**: After Environment publish or notebook execution:
```
ResolvePackageNotFound: ... conflicts with runtime built-in version
```
or
```
ImportError: cannot import name 'X' from 'Y' (wrong version installed)
```

**Root cause**: Synapse Spark pools may pin library versions (e.g., `pandas==1.4.3`) that conflict with Fabric Runtime 1.3 built-in versions (e.g., `pandas==2.1.1`). Fabric does not allow downgrading built-in libraries.

### Resolution Steps

1. **Identify conflicts** — compare `libraryRequirements.content` from the Synapse pool against Fabric Runtime 1.3 built-in versions:
   ```python
   # In a Fabric notebook, list built-in versions:
   import pkg_resources
   for pkg in sorted(pkg_resources.working_set, key=lambda p: p.key):
       print(f"{pkg.key}=={pkg.version}")
   ```

2. **Remove pins for built-in libraries** — if the Synapse requirements.txt pins a version that Fabric already provides at a newer version, remove the pin:
   ```
   # Synapse requirements.txt:
   pandas==1.4.3          ← REMOVE (Fabric has 2.1.1)
   scikit-learn==1.2.0    ← REMOVE (Fabric has 1.3.2)
   my-custom-lib==1.0.0   ← KEEP (not a built-in)
   ```

3. **Test for breaking API changes** — if the version jump is major (e.g., pandas 1.x → 2.x), code may break. Common issues:
   - `pandas.DataFrame.append()` removed in pandas 2.x → use `pd.concat()`
   - `sklearn.externals.joblib` removed → use `import joblib` directly
   - `numpy` dtype changes (e.g., `np.int` → `np.int64`)

4. **If a specific older version is required** — use `%pip install` in the notebook as a last resort:
   ```python
   %pip install pandas==1.4.3 --force-reinstall
   ```
   > This overrides the built-in version for the session only. Not recommended for production — may cause instability with other built-in libraries that depend on the newer version.

> **See also**: [library-compatibility.md](library-compatibility.md) for a complete list of Synapse-vs-Fabric library gaps.

---

## G3: Delta Lake Protocol Version Incompatibility

**Flag ID**: `DELTA_PROTOCOL_MISMATCH`

**When it fires**: A Lakehouse shortcut points to Delta tables written by Synapse using a newer or incompatible Delta protocol version.

**Symptom**: Reading the shortcutted table fails with:
```
DeltaErrors: The table has reader version X, which is not supported by this version of Delta Lake
```
or
```
Unsupported reader/writer feature: deletionVectors / columnMapping / v2Checkpoints
```

**Root cause**: Synapse Spark pools may write Delta tables using protocol features that the selected Fabric Runtime or downstream reader does not support, or the target DDL may contain logical column names that require Delta column mapping.

### Resolution Steps

1. **Check the protocol version** of the source Delta table:
   ```python
   # In a Synapse notebook (before migration):
   from delta.tables import DeltaTable
   dt = DeltaTable.forPath(spark, "abfss://container@account.dfs.core.windows.net/path/to/table")
   detail = dt.detail().select("minReaderVersion", "minWriterVersion").collect()[0]
   print(f"Reader: {detail.minReaderVersion}, Writer: {detail.minWriterVersion}")
   ```

2. **Check the selected Fabric Runtime and every downstream reader** against current Microsoft documentation. Do not use a hardcoded runtime/version matrix.

3. **Keep the source read-only.** If the source shortcut protocol is unsupported, record `ManualReviewRequired`; do not rewrite, drop, rename, or downgrade the source table as part of this migration.

4. **Plan new target DDL selectively** with `plan_delta_column_mapping`:
   - safe logical names: normal Delta DDL;
   - restricted names such as spaces, commas, semicolons, braces, parentheses, newlines, tabs, or equals signs: require downstream compatibility approval, then emit `TBLPROPERTIES ('delta.columnMapping.mode' = 'name')`;
   - existing compatible target or shortcut: validate and reuse it without protocol changes;
   - existing incompatible or uncertain target: block for manual review rather than altering it.

5. **Record protocol and mapping evidence** in `expected-schema.json` and `migration-manifest.json`, including offending logical names, current mode, decision, and approval.

> **Pre-migration check**: Inventory Delta protocol features and column mapping for every existing target or shortcut, and validate downstream compatibility before any target mutation.

---

## G4: Synapse Security Model — Managed Identities & IP Firewall

**Flag ID**: `SECURITY_MODEL_INCOMPATIBLE`

**When it fires**: The Synapse workspace uses security features that don't have direct Fabric equivalents.

### G4a: Managed Identity Differences

**Symptom**: After migration, notebooks fail with `403 Forbidden` when accessing external resources (ADLS, Key Vault, SQL).

| Synapse Feature | Fabric Equivalent | Migration Action |
|---|---|---|
| Workspace Managed Identity (system-assigned) | **Fabric Workspace Identity** | Enable Workspace Identity in Fabric Settings → grant same RBAC roles on external resources |
| User-assigned Managed Identity | **Not supported** | Switch to Fabric Workspace Identity or service principal stored in Key Vault |
| `LinkedServiceBasedTokenProvider` | **Not available** | Replace with `ClientCredsTokenProvider` + Key Vault. See [connector-refactoring.md](connector-refactoring.md) |

**Steps**:
1. Enable Fabric Workspace Identity: Workspace Settings → Identity → Enable
2. Grant the workspace identity the same roles the Synapse MSI had:
   - Storage Blob Data Reader/Contributor on ADLS Gen2 accounts
   - Key Vault Secrets User on Key Vault instances
   - SQL db_datareader on SQL databases (via Entra ID admin)
3. Update notebook code that used `mssparkutils.credentials.getToken()` — this works in Fabric with `notebookutils.credentials.getToken()`, but the identity backing it is now the Fabric workspace identity, not the Synapse MSI

### G4b: IP Firewall Rules

**Symptom**: Synapse workspace had IP-based access control. Fabric does not support IP firewall rules at the workspace level.

| Synapse Feature | Fabric Alternative |
|---|---|
| Synapse IP firewall rules | Entra ID Conditional Access with named locations |
| Managed Virtual Network | Fabric Managed Private Endpoints (requires Custom Pool in Environment) |
| Data Exfiltration Protection | Fabric tenant-level settings + Conditional Access |

**Steps**:
1. **Document existing IP rules** from the Synapse workspace: Portal → Synapse workspace → Firewalls
2. **Create Entra Conditional Access policy**: Entra ID → Security → Conditional Access → New policy
   - Target: Microsoft Fabric (app ID)
   - Condition: Named locations (replicate the IP ranges from Synapse firewall)
   - Grant: Allow access only from named locations
3. **For private connectivity**: Set up Managed Private Endpoints in a Fabric Environment with Custom Pool. See [security-governance.md § S6](security-governance.md)

> **See also**: [security-governance.md](security-governance.md) for the full security migration guide.

---

## G5: GPU Pool Migration Blocker

**Flag ID**: `GPU_POOL_UNSUPPORTED`

**When it fires**: Synapse Spark pool has `nodeSizeFamily == "HardwareAcceleratedGPU"`.

**Symptom**: No Fabric equivalent — GPU-accelerated Spark is not available in Fabric.

### Resolution Options

| Option | Steps |
|---|---|
| **Keep on Synapse** | Continue running GPU workloads on Synapse until Fabric adds GPU support |
| **Refactor to CPU** | Replace GPU-accelerated ML training with CPU-based alternatives (e.g., LightGBM, scikit-learn) |
| **Use Azure ML** | Move GPU training to Azure ML compute clusters and call from Fabric via REST API |

---

## G6: .NET for Spark (C#/F#) SJD Blocker

**Flag ID**: `DOTNET_SPARK_UNSUPPORTED`

**When it fires**: SJD has `language == "dotnet"` or `language == "csharp"`.

**Symptom**: Fabric does not support .NET for Apache Spark.

### Resolution

Rewrite the SJD in Python or Scala. Common patterns:

| C# Pattern | Python Equivalent |
|---|---|
| `spark.Sql("SELECT ...")` | `spark.sql("SELECT ...")` |
| `spark.Read().Parquet("...")` | `spark.read.parquet("...")` |
| `dataFrame.Filter(col => ...)` | `df.filter(F.col(...))` |
| `.WithColumn("x", Functions.Lit(1))` | `.withColumn("x", F.lit(1))` |

---

## G7: `bigDataPool` / `targetBigDataPool` Field is `null` (Not Missing)

**Flag ID**: `NULLABLE_POOL_REFERENCE`

**When it fires**: Code reads `properties.bigDataPool.referenceName` (notebooks) or `properties.targetBigDataPool.referenceName` (SJDs) and crashes with `AttributeError: 'NoneType' object has no attribute 'get'`.

**Root cause**: The Synapse API returns `"bigDataPool": null` (field present with value `null`) when no pool is assigned — instead of omitting the field entirely. The common pattern `.get("bigDataPool", {}).get("referenceName")` fails because `dict.get()` returns `None` (the actual value), not `{}` (the default).

### Resolution

Use the `or {}` defensive pattern:

```python
# ❌ WRONG — crashes when bigDataPool is null
pool_name = nb.get("bigDataPool", {}).get("referenceName", "")

# ✅ CORRECT — handles null, missing, and present cases
pool_name = (nb.get("bigDataPool") or {}).get("referenceName", "")
```

Same pattern applies to SJDs:
```python
pool_name = (sjd.get("targetBigDataPool") or {}).get("referenceName", "")
```

---

## G8: Notebook Session Configuration (`%%configure`)

**Flag ID**: `SESSION_CONFIG_IGNORED`

**When it fires**: Notebook contains `%%configure` magic with Synapse-specific driver/executor settings.

**Symptom**: `%%configure` is supported in Fabric but some Synapse-specific keys are silently ignored.

### Synapse-Specific Keys to Remove

```json
// ❌ These keys are Synapse-specific — remove from %%configure:
{
  "conf": {
    "spark.synapse.pool.name": "MyPool",          // → remove
    "spark.storage.synapse.linkedServiceName": "", // → remove
    "spark.synapse.workspace.name": ""             // → remove
  },
  "driverMemory": "28g",     // ✅ kept — works in Fabric
  "executorMemory": "28g",   // ✅ kept — works in Fabric
  "numExecutors": 4          // ✅ kept — works in Fabric
}
```

---

## G9: Shortcut Creation Failures (ADLS Connection Issues)

**Flag ID**: `SHORTCUT_CONNECTION_FAILED`

**When it fires**: Phase 1 shortcut creation fails with 403, 400 (credential), or connection reset errors.

**Symptom**: Lakehouse is created but shortcuts are missing — tables are not accessible. The migration script aborts remaining shortcuts after the first fatal error.

### Common Causes

| Error | Root Cause |
|---|---|
| 403 on shortcut creation | Connection's identity lacks `Storage Blob Data Reader` RBAC on the ADLS Gen2 storage account |
| 400 `"Stored Credential"` | Connection's OAuth token has expired, been revoked, or the user password was rotated |
| `ConnectionError` / connection reset | Network connectivity issue or Fabric API transient outage |

### Resolution

1. **403 (permission)**:
   - Identify the connection's identity (Service Principal or user) from the Fabric Portal → Manage connections
   - Grant `Storage Blob Data Reader` on the storage account (or container) via Azure Portal → IAM
   - Re-run the migration — it will resume from where it left off (existing shortcuts return 409)

2. **400 Stored Credential**:
   - Open Fabric Portal → Settings → Manage connections and gateways
   - Find the ADLS connection → Edit → Re-authenticate with valid credentials
   - Alternatively, create a new connection and delete the stale one
   - Re-run the migration

3. **Connection reset**:
   - Retry after a few minutes — this is typically transient
   - If persistent, check VNet/private endpoint configuration between Fabric and the storage account

> **Note**: The migration script uses an early-abort pattern for these errors — it stops creating shortcuts after the first fatal error because all subsequent shortcuts to the same storage account will fail for the same reason. See [lake-database-migration.md § Shortcut Creation Error Cascade](lake-database-migration.md#shortcut-creation-error-cascade) for the implementation pattern.

---

## Flag ID Summary — Quick Reference

Use these IDs in the migration report to link to the corresponding section:

| Flag ID | Section | Severity | Blocks Execution? |
|---|---|---|---|
| `SYNAPSESQL_NO_EQUIVALENT` | [G1](#g1-sparkreadsynapsesql--no-direct-fabric-equivalent) | High | Yes — runtime error |
| `LIBRARY_VERSION_CONFLICT` | [G2](#g2-custom-library-version-conflicts-with-fabric-runtime) | Medium | Maybe — depends on conflict |
| `DELTA_PROTOCOL_MISMATCH` | [G3](#g3-delta-lake-protocol-version-incompatibility) | High | Yes — cannot read table |
| `SECURITY_MODEL_INCOMPATIBLE` | [G4](#g4-synapse-security-model--managed-identities--ip-firewall) | Medium | Yes — 403 errors at runtime |
| `GPU_POOL_UNSUPPORTED` | [G5](#g5-gpu-pool-migration-blocker) | High | Yes — migration blocker |
| `DOTNET_SPARK_UNSUPPORTED` | [G6](#g6-net-for-spark-cf-sjd-blocker) | High | Yes — migration blocker |
| `NULLABLE_POOL_REFERENCE` | [G7](#g7-bigdatapool--targetbigdatapool-field-is-null-not-missing) | Low | No — null handled safely |
| `SESSION_CONFIG_IGNORED` | [G8](#g8-notebook-session-configuration-configure) | Low | No — silently ignored |
| `SHORTCUT_CONNECTION_FAILED` | [G9](#g9-shortcut-creation-failures-adls-connection-issues) | High | Partial — Lakehouse exists but tables missing |
