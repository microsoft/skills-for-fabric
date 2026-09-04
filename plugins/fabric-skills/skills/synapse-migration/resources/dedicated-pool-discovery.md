# Dedicated Pool Discovery and Assessment

> **Purpose**: Extract schema from Synapse Dedicated SQL Pool using DACPAC or catalog queries and classify objects by complexity (T1-T4)
> **Tools**: SqlPackage CLI, Python 3.10+, Azure CLI
> **Output**: `<pool>.dacpac`, SQL scripts, inventory, complexity assessment, and SQL Pool to Lakehouse gap reports

This phase is notebook-free. Do not use a discovery notebook or require notebook artifacts from the source or target workspace.

---

## Table of Contents

| Section | Description |
|---------|-------------|
| [§ DACPAC Extraction](#dacpac-extraction) | SqlPackage commands for schema export |
| [§ Script Extraction](#script-extraction) | Extract individual SQL files from DACPAC |
| [§ Schema Inventory](#schema-inventory) | Parse DACPAC to list tables, views, procedures |
| [§ Complexity Classification](#complexity-classification) | T1-T4 classification contract |
| [§ Assessment Report](#assessment-report) | Generate JSON report with conversion estimates |
| [§ Migration Gap Report](#migration-gap-report) | Required SQL Pool to Lakehouse compatibility findings |

---

## DACPAC Extraction

### Prerequisites

**Install SqlPackage**:
- Windows: [Download SqlPackage](https://learn.microsoft.com/sql/tools/sqlpackage/sqlpackage-download)
- Linux/Mac: `dotnet tool install -g microsoft.sqlpackage`

**Authentication**:
```powershell
# Azure AD auth (recommended)
az login
$token = az account get-access-token --resource https://database.windows.net --query accessToken -o tsv
```

### Extract Command

```powershell
# Define connection parameters
$synapseServer = "your-workspace.sql.azuresynapse.net"
$dedicatedPool = "your-pool-name"
$outputPath = "./dacpac_output"
New-Item -ItemType Directory -Force -Path $outputPath

# Extract DACPAC (Azure AD auth)
sqlpackage /Action:Extract `
    /SourceConnectionString:"Server=tcp:$synapseServer,1433;Database=$dedicatedPool;Encrypt=True" `
    /AccessToken:$token `
  /TargetFile:"$outputPath/$dedicatedPool.dacpac" `
  /p:ExtractAllTableData=False `
  /p:VerifyExtraction=True `
  /p:ExtractReferencedServerScopedElements=False `
  /DiagnosticsFile:"$outputPath/extract.log"

# Check exit code
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ DACPAC extracted successfully" -ForegroundColor Green
    $dacpacSize = (Get-Item "$outputPath/$dedicatedPool.dacpac").Length / 1MB
    Write-Host "   Size: $([math]::Round($dacpacSize, 2)) MB"
} else {
    Write-Host "❌ Extraction failed. Check extract.log" -ForegroundColor Red
    Get-Content "$outputPath/extract.log" | Select-Object -Last 20
    exit 1
}
```

Do not place SQL passwords in command arguments or generated migration artifacts. If Azure AD authentication is unavailable, stop and have the operator configure an approved secret-backed authentication flow outside this skill.

### Troubleshooting DACPAC Extraction

| Error | Cause | Resolution |
|-------|-------|------------|
| **Connection timeout** | Firewall blocks IP | Add client IP to Synapse firewall rules |
| **Authentication failed** | AAD token expired | Re-run `az login` |
| **SqlPackage not found** | Not in PATH | Use full path: `C:\Program Files\Microsoft SQL Server\160\DAC\bin\SqlPackage.exe` |
| **Cannot connect to server** | Pool is paused | Resume Dedicated Pool in Azure Portal |
| **Insufficient permissions** | Lacks metadata visibility | Grant database `CONNECT` and `VIEW DEFINITION`; add narrower catalog permissions only when a failed query proves they are needed |
| **Stored procedure body extraction returns empty/placeholder** | Manual XML parsing uses wrong property | Use DacFx `GetScript()` (recommended) or read `Property[@Name='BodyScript'].InnerText` from DACPAC `model.xml`. Do NOT use `Annotation[@Type='SysCommentsObjectAnnotation']/Property[@Name='Expression']` (that path does not exist). Property `HeaderContents` contains only the signature, not the body. |

---

## Script Extraction

**Defects #13-17 fixes**: Package and maintain a deterministic DacFx discovery/conversion executable that handles DacFx SDK resolution, `ModelLoadOptions`, non-scriptable child objects, and built-in object filtering automatically.

### Read the DACPAC Model

`sqlpackage /Action:Script` produces a deployment script only when given a target and does not create one file per source object. Do not use it as the inventory source. Run the maintained `../scripts/Invoke-DedicatedPoolTool.ps1` entry point against a `.dacpac` or a ZIP containing one DACPAC. That entry point builds `dedicated-pool-tool/DedicatedPoolTool.csproj`; its `Program.cs` pins the DacFx dependency, loads the resolved DACPAC with explicit `ModelLoadOptions { LoadAsScriptBackedModel = true }`, and emits normalized source evidence plus `schema-inventory.json`. A ZIP containing only a SQL project is rejected by default because MSBuild can execute arbitrary targets. Prefer compiling it in an isolated trusted environment and then passing the DACPAC; use `-AllowTrustedProjectBuild` only after reviewing and explicitly trusting the project.

**Defect #14 fix**: The packaged tool uses a pinned NuGet `Microsoft.SqlServer.DacFx` dependency declared in `DedicatedPoolTool.csproj`. The wrapper script clears `MSBuildSDKsPath` during `dotnet run` to ensure consistent DacFx resolution without manual environment configuration.

**Defect #15 fix**: The tool explicitly uses `ModelLoadOptions { LoadAsScriptBackedModel = true }` to ensure compatibility with installed DacFx versions.

**Defect #16 fix**: Wrap `GetScript()` and child-object traversal in exception handlers. Catch `DacModelException`, `InvalidOperationException`, and `NotSupportedException`; preserve the typed object record and add a `NonScriptableObject` blind spot instead of aborting discovery or classifying a child as `Unknown`.

**Defect #17 fix**: Filter out built-in system objects during classification. Use `DacQueryScopes.UserDefined` and additional checks to exclude:
- Built-in types (`sys.*`, `dbo.sysname`)
- Built-in roles (`public`, `db_owner`, etc.)
- System schemas (`sys`, `INFORMATION_SCHEMA`)
- DacFx child objects (columns, constraints, indexes, parameters) which belong in `supportingObjects`, not `objects`

Only user-defined top-level objects contribute to migratable-object counts and `Unknown` classification totals.

Use `TSqlModel.GetObjects(DacQueryScopes.UserDefined)` and classify objects by their DacFx `ObjectType`. Keep top-level conversion objects in `objects`, schemas/security principals and policies in `evidenceObjects`, and columns, constraints, indexes, parameters, and other children in `supportingObjects`. Only `objects` contributes to migratable-object and `Unknown` classification totals. At minimum, include:

- schemas, tables, columns, data types, defaults, identities, sequences, and partition specifications
- primary, foreign, unique, and check constraints; indexes, columnstore indexes, statistics, and materialized views
- views, procedures, scalar/table functions, triggers, synonyms, and external objects
- users, roles, permissions, row-level security, masking, workload groups, and classifiers
- all model relationships and referenced-object identifiers, not regex-only `FROM` and `JOIN` matches

For each object, use DacFx properties and relationships as the authoritative metadata. Call `GetScript()` only for top-level conversion and evidence objects. Catch `DacModelException`, `InvalidOperationException`, and `NotSupportedException`; preserve the typed object record and add a `NonScriptableObject` blind spot instead of aborting discovery or classifying a child as `Unknown`.

### Source-Contract Edge Validation (Defect #3 Fix)

For every procedure dependency on a table or view, emit a source-contract edge **during discovery** containing the referencing object stable ID, referenced object stable ID and type, every referenced column identifier, the referenced object's discovered ordered projection, and a resolution status. Match identifiers with the source model's collation semantics. Set the status to `Resolved` only when every referenced column exists in that projection; otherwise set `MissingReferencedColumn` and record the exact missing-column set.

**Critical**: Validate source-contract edges **before conversion starts**, not after generation. An unresolved object or column relationship is a discovery blind spot and must set the affected procedure to `ManualReviewRequired` status **before any notebook generation begins**. Never attempt conversion for procedures with unresolved column contracts. An unresolved object or column relationship is a discovery blind spot, not permission to infer a contract from generated SQL.

**Example**: When `uspComplex_SalesExceptionScan` references columns `OrderDateKey`, `ProductKey`, and `TotalProductCost` from `vwComplex_UnifiedSales`, but that view's discovered projection does not expose those three columns, the discovery phase must record a `MissingReferencedColumn` status with the exact missing set `["OrderDateKey", "ProductKey", "TotalProductCost"]`, set the procedure's conversion status to `ManualReviewRequired` with no generated notebook, and continue discovering and converting independently eligible procedures.

```csharp
// Illustrative core of the DacFx extractor (RECOMMENDED APPROACH)
using Microsoft.SqlServer.Dac.Model;

var options = new ModelLoadOptions { LoadAsScriptBackedModel = true };
var dacpac = TSqlModel.LoadFromDacpac("pool.dacpac", options);
var objects = dacpac.GetObjects(DacQueryScopes.UserDefined);

foreach (var sourceObject in objects)
{
        var objectType = sourceObject.ObjectType.Name;
        var objectName = sourceObject.Name?.ToString() ?? "";
        // The packaged tool calls GetScript only for top-level/evidence objects
        // and records supported DacFx exceptions as discovery blind spots.
        // Serialize DacFx properties, relationships, and source text into the
        // canonical inventory record. Do not infer names or dependencies by regex.
}
```

**Alternative: Manual XML parsing** (use only when DacFx tool is unavailable):

```powershell
# Extract stored procedure body from DACPAC model.xml
# CRITICAL: Use Property[@Name='BodyScript'], NOT Annotation[@Name='Expression']

$xml = [xml](Get-Content "extracted/model.xml")
$procedures = $xml.DataSchemaModel.Model.Element | Where-Object { $_.Type -eq 'SqlProcedure' }

foreach ($proc in $procedures) {
    $procName = $proc.Name
    
    # CORRECT: Read from Property[@Name='BodyScript']
    $bodyScriptProperty = $proc.Property | Where-Object { $_.Name -eq 'BodyScript' }
    if ($bodyScriptProperty -and $bodyScriptProperty.InnerText) {
        $sqlCode = $bodyScriptProperty.InnerText.Trim()
        Write-Host "✓ Extracted $($sqlCode.Length) characters from $procName"
    } else {
        Write-Warning "⚠ Could not extract T-SQL body for $procName"
    }
    
    # INCORRECT patterns to avoid:
    # ❌ $annotationElement.Property[@Name='Expression'] - this path does not exist
    # ❌ $proc.Property[@Name='HeaderContents'] - contains only signature, not body
}
```

**Property location summary for manual XML parsing**:
- **Full T-SQL body**: `Element[@Type='SqlProcedure']/Property[@Name='BodyScript']/InnerText`
- **Signature only**: `Element[@Type='SqlProcedure']/Property[@Name='HeaderContents']/InnerText` (e.g., "CREATE PROC [dbo].[uspName] AS")
- **Name**: `Element[@Type='SqlProcedure']/@Name` attribute

Do not attempt to read `Annotation[@Type='SysCommentsObjectAnnotation']/Property[@Name='Expression']` — that XML path does not exist in DACPAC model.xml structure.

### Supplement with Read-Only Catalog Queries

A DACPAC does not represent every operational or external dependency. Query source catalogs read-only and merge results into the same inventory. Record each query, timestamp, success/failure, and error text so missing permissions become visible assessment blind spots.

Required catalog coverage includes `sys.schemas`, `sys.objects`, `sys.columns`, `sys.types`, `sys.default_constraints`, `sys.check_constraints`, `sys.key_constraints`, `sys.foreign_keys`, `sys.indexes`, `sys.index_columns`, `sys.partitions`, `sys.sql_modules`, `sys.sql_expression_dependencies`, `sys.database_principals`, `sys.database_permissions`, `sys.database_role_members`, `sys.security_policies`, `sys.masked_columns`, `sys.external_tables`, `sys.external_data_sources`, `sys.external_file_formats`, `sys.database_scoped_credentials`, `sys.pdw_table_distribution_properties`, and available workload-management/catalog views. Use `sys.sql_expression_dependencies.referenced_minor_id` with `sys.columns` where available to corroborate column-level references; preserve a failed or incomplete resolution as a blind spot rather than falling back to regex-only parsing.

Never query table rows. Catalog and definition metadata only are permitted.

---

## Schema Inventory

### Canonical Inventory Contract

Write `schema-inventory.json` and `schema-inventory.md` from the merged DacFx and catalog results. The JSON root is an object with an `objects` array and a `blindSpots` array. Every object record must include the stable source identifier, schema, name, type, normalized `sourceText` and source path when applicable, DacFx properties, dependency identifiers, catalog evidence, and any discovery warnings. Preserve failed metadata queries in `blindSpots`.

Before classification, verify that every required gap category in [dedicated-pool-gap-assessment.md](dedicated-pool-gap-assessment.md) has either collected evidence or an explicit query failure. Also verify every procedure-to-table/view source-contract edge. Any `MissingReferencedColumn`, unresolved referenced object, or unknown projection must be linked to the affected procedure and carried into the gap assessment before conversion. An empty pool is valid and must produce an empty inventory, zero counts, and no conversion work; it must not be padded with sample objects.

**Output**:
- `schema-inventory.json` — structured data for downstream processing
- `schema-inventory.md` — human-readable summary

---

## Complexity Classification

### T1-T4 Classification Contract

Classify every source-bearing object from `schema-inventory.json`. Apply tiers from highest to lowest precedence; the first matching tier wins. Preserve every matched indicator as evidence rather than relying on an unexplained numeric score.

| Tier | Indicators | Conversion approach |
|---|---|---|
| T4 | Stored procedure; cursor or loop; temporary table; dynamic SQL; transaction; TRY/CATCH | Spark SQL notebook component planning; defer notebook cardinality and grouping until the post-discovery capacity and mapping assessment is approved |
| T3 | Window function; CTE; nested subquery; set operation; PIVOT/UNPIVOT | Individual conversion and focused semantic review |
| T2 | Join; CASE; GROUP BY; aggregate | Guided conversion with targeted tests |
| T1 | Simple projection/filter without a higher-tier indicator | Routine conversion and syntax validation |

Object size and a wide projection are supplemental effort indicators only; they must not lower a tier selected by a semantic indicator. Objects without source text remain in the inventory with classification `Unknown` and a reason that identifies the missing evidence.

Write both `complexity-report.json` and `complexity-report.md`. Each classified object must include its stable source identifier, schema, name, type, tier, matched indicators, line count, dependencies, and review status. The Markdown report must summarize tier counts and percentages, list all T4 and `Unknown` objects, and identify the conversion approach for each tier.

---

## Assessment Report

### Consolidated Discovery Report

Generate `assessment-report.json` from the canonical inventory and complexity report. Include:

- generation timestamp and source pool identifier
- total discovered objects and counts by type, schema, tier, and review status
- all discovery blind spots and failed metadata queries
- T4 and `Unknown` objects requiring manual review
- dependency blockers and recommended migration waves
- discovered procedure count and the inventory inputs required to project target notebook and workspace item totals
- effort assumptions and estimates, clearly labeled as planning estimates rather than commitments

If using the default planning heuristic, calculate estimated hours as $0.5T1 + 1T2 + 3T3 + 8T4$ and estimated days as hours divided by eight. Keep the coefficients in report metadata so reviewers can replace them. Never infer low effort for `Unknown` objects; report them separately until evidence is available.

---

## Migration Gap Report

After inventory and complexity classification, execute the complete [Dedicated Pool to Lakehouse Gap Assessment](dedicated-pool-gap-assessment.md). Produce:

- `migration-gap-report.json`
- `migration-gap-report.md`

The report must assess every discovered object across every required gap category, identify metadata-query failures and unknowns, and list concrete evidence and disposition for each finding. It must also compare `1:1`, `N:1`, and `N:N` procedure-notebook strategies using the discovered procedure inventory and projected workspace item demand. Present the Markdown report to the customer, then require the customer to provide and approve the complete mapping strategy and workspace placement before conversion. Complexity and effort reports do not satisfy this requirement.

---

## Summary

This discovery phase provides:
1. **DACPAC Extraction** — Schema export from Synapse Dedicated Pool
2. **Script Extraction** — Individual SQL files for each object
3. **Schema Inventory** — Structured metadata (type, dependencies, line count)
4. **Complexity Classification** — T1-T4 tiers with conversion approach
5. **Assessment Report** — Effort estimate and recommendations
6. **Migration Gap Report** — Complete SQL Pool to Lakehouse compatibility findings and customer approval

**Next Phase**: Proceed to [dedicated-pool-conversion.md](dedicated-pool-conversion.md) only after the migration gap report is complete and approved.
