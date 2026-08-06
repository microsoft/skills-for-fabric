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
| [§ Complexity Classification](#complexity-classification) | T1-T4 classifier algorithm |
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
SqlPackage /Action:Extract `
    /SourceConnectionString:"Server=tcp:$synapseServer,1433;Database=$dedicatedPool;Encrypt=True" `
    /AccessToken:$token `
  /TargetFile:"$outputPath/$dedicatedPool.dacpac" `
  /p:ExtractAllTableData=False `
  /p:VerifyExtraction=True `
  /p:ExtractReferencedServerScopedElements=False `
  /p:Storage=File `
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

---

## Script Extraction

### Read the DACPAC Model

`SqlPackage /Action:Script` produces a deployment script only when given a target and does not create one file per source object. Do not use it as the inventory source. Load the schema-only DACPAC with DacFx and emit one normalized source file plus one inventory record per model object.

Use `TSqlModel.GetObjects(DacQueryScopes.All)` and classify objects by their DacFx `ObjectType`. At minimum, include:

- schemas, tables, columns, data types, defaults, identities, sequences, and partition specifications
- primary, foreign, unique, and check constraints; indexes, columnstore indexes, statistics, and materialized views
- views, procedures, scalar/table functions, triggers, synonyms, and external objects
- users, roles, permissions, row-level security, masking, workload groups, and classifiers
- all model relationships and referenced-object identifiers, not regex-only `FROM` and `JOIN` matches

For each object, use DacFx properties and relationships as the authoritative metadata. Use `GetScript()` only to retain normalized source text for complexity and conversion analysis.

```csharp
// Illustrative core of the DacFx extractor
using Microsoft.SqlServer.Dac.Model;

var dacpac = TSqlModel.LoadFromDacpac("pool.dacpac");
var objects = dacpac.GetObjects(DacQueryScopes.All)
        .Where(o => !o.ObjectType.Name.StartsWith("BuiltIn", StringComparison.Ordinal));

foreach (var sourceObject in objects)
{
        var objectType = sourceObject.ObjectType.Name;
        var objectName = sourceObject.Name?.ToString() ?? "";
        var sourceText = sourceObject.GetScript() ?? "";
        // Serialize DacFx properties, relationships, and source text into the
        // canonical inventory record. Do not infer names or dependencies by regex.
}
```

### Supplement with Read-Only Catalog Queries

A DACPAC does not represent every operational or external dependency. Query source catalogs read-only and merge results into the same inventory. Record each query, timestamp, success/failure, and error text so missing permissions become visible assessment blind spots.

Required catalog coverage includes `sys.schemas`, `sys.objects`, `sys.columns`, `sys.types`, `sys.default_constraints`, `sys.check_constraints`, `sys.key_constraints`, `sys.foreign_keys`, `sys.indexes`, `sys.index_columns`, `sys.partitions`, `sys.sql_modules`, `sys.sql_expression_dependencies`, `sys.database_principals`, `sys.database_permissions`, `sys.database_role_members`, `sys.security_policies`, `sys.masked_columns`, `sys.external_tables`, `sys.external_data_sources`, `sys.external_file_formats`, `sys.database_scoped_credentials`, `sys.pdw_table_distribution_properties`, and available workload-management/catalog views.

Never query table rows. Catalog and definition metadata only are permitted.

---

## Schema Inventory

### Canonical Inventory Contract

Write `schema-inventory.json` and `schema-inventory.md` from the merged DacFx and catalog results. The JSON root is an object with an `objects` array and a `blindSpots` array. Every object record must include the stable source identifier, schema, name, type, normalized `sourceText` and source path when applicable, DacFx properties, dependency identifiers, catalog evidence, and any discovery warnings. Preserve failed metadata queries in `blindSpots`.

Before classification, verify that every required gap category in [dedicated-pool-gap-assessment.md](dedicated-pool-gap-assessment.md) has either collected evidence or an explicit query failure. An empty pool is valid and must produce an empty inventory, zero counts, and no conversion work; it must not be padded with sample objects.

**Output**:
- `schema-inventory.json` — structured data for downstream processing
- `schema-inventory.md` — human-readable summary

---

## Complexity Classification

### T1-T4 Classifier Algorithm

The classifier below defines the T1-T4 tiers used by this pattern.

```python
# complexity_classifier.py
import json
import re
from pathlib import Path
from typing import Dict, List

def classify_sql_object(sql_text: str, object_type: str, line_count: int) -> Dict:
    """
    Classify SQL object into T1 (simple) to T4 (complex) tiers.

    Tier Definitions:
    - T1: Simple SELECT, single table, basic WHERE
    - T2: Joins, CASE, GROUP BY, basic aggregations
    - T3: Window functions, CTEs, subqueries, UNION
    - T4: Procedures, cursors, temp tables, dynamic SQL, transactions
    """
    tier = "T1"  # Start optimistic
    reasons = []
    score = 0  # Complexity score (higher = more complex)

    # T4 automatic triggers (procedural/complex)
    if object_type == "Procedure":
        tier = "T4"
        reasons.append("Stored procedure (requires manual redesign)")
        score += 100

    if re.search(r'\bCURSOR\b', sql_text, re.IGNORECASE):
        tier = "T4"
        reasons.append("Uses CURSOR")
        score += 100

    if re.search(r'\bWHILE\b|\bLOOP\b', sql_text, re.IGNORECASE):
        tier = "T4"
        reasons.append("Contains procedural loops")
        score += 80

    if re.search(r'#\w+|##\w+', sql_text):  # Temp tables
        tier = "T4"
        reasons.append("Uses temp tables (#temp)")
        score += 70

    if re.search(r'\bEXEC\s*\(|\bsp_executesql\b', sql_text, re.IGNORECASE):
        tier = "T4"
        reasons.append("Dynamic SQL (EXEC or sp_executesql)")
        score += 90

    if re.search(r'\bBEGIN\s+TRY\b|\bBEGIN\s+TRAN', sql_text, re.IGNORECASE):
        tier = "T4"
        reasons.append("Transaction or TRY/CATCH logic")
        score += 60

    # T3 indicators (advanced SQL)
    if tier != "T4":
        if re.search(r'\bOVER\s*\(|\bROW_NUMBER\b|\bRANK\b|\bDENSE_RANK\b', sql_text, re.IGNORECASE):
            tier = "T3"
            reasons.append("Window functions (OVER clause)")
            score += 50

        if re.search(r'\bWITH\s+\w+\s+AS\s*\(', sql_text, re.IGNORECASE):
            tier = "T3"
            reasons.append("Common Table Expressions (CTEs)")
            score += 40

        if re.search(r'\bSELECT.*\bFROM\s*\(.*\bSELECT\b', sql_text, re.IGNORECASE | re.DOTALL):
            tier = "T3"
            reasons.append("Nested subqueries")
            score += 35

        if re.search(r'\bUNION\b|\bINTERSECT\b|\bEXCEPT\b', sql_text, re.IGNORECASE):
            tier = "T3"
            reasons.append("Set operations (UNION/INTERSECT/EXCEPT)")
            score += 30

        if re.search(r'\bPIVOT\b|\bUNPIVOT\b', sql_text, re.IGNORECASE):
            tier = "T3"
            reasons.append("PIVOT/UNPIVOT operations")
            score += 45

    # T2 indicators (moderate complexity)
    if tier == "T1":
        if re.search(r'\bJOIN\b', sql_text, re.IGNORECASE):
            tier = "T2"
            reasons.append("Contains JOINs")
            score += 20

        if re.search(r'\bCASE\b', sql_text, re.IGNORECASE):
            tier = "T2"
            reasons.append("Contains CASE statements")
            score += 15

        if re.search(r'\bGROUP\s+BY\b', sql_text, re.IGNORECASE):
            tier = "T2"
            reasons.append("Contains GROUP BY")
            score += 18

        if re.search(r'\b(?:SUM|AVG|COUNT|COUNT_BIG|MIN|MAX|STRING_AGG|APPROX_COUNT_DISTINCT)\s*\(', sql_text, re.IGNORECASE):
            tier = "T2"
            reasons.append("Aggregate functions")
            score += 10

        if re.search(r'\bLEFT\s+JOIN\b|\bRIGHT\s+JOIN\b|\bFULL\s+OUTER\s+JOIN\b', sql_text, re.IGNORECASE):
            tier = "T2"
            reasons.append("Outer joins")
            score += 12

    # Line count heuristic (large objects = more complex)
    if line_count > 200:
        score += 20
        reasons.append(f"Large object ({line_count} lines)")
    elif line_count > 100:
        score += 10

    # Multi-column complexity
    select_cols = len(re.findall(r',', sql_text[:sql_text.find('FROM') if 'FROM' in sql_text.upper() else len(sql_text)]))
    if select_cols > 20:
        score += 15
        reasons.append(f"Many columns ({select_cols})")

    return {
        "tier": tier,
        "score": score,
        "reasons": reasons
    }

def classify_all_objects(inventory_path: Path) -> List[Dict]:
    """Classify source-bearing objects from the canonical inventory."""
    inventory = json.loads(inventory_path.read_text())
    classified = []

    for item in inventory.get("objects", []):
        sql_text = item.get("sourceText", "")
        source_path = item.get("sourcePath")
        if not sql_text and source_path:
            sql_text = Path(source_path).read_text(encoding="utf-8", errors="ignore")
        if not sql_text:
            continue

        classification = classify_sql_object(
            sql_text,
            item["type"],
            item.get("lineCount", sql_text.count("\n") + 1)
        )

        classified.append({
            **item,
            **classification
        })

    return classified

def write_complexity_report(classified: List[Dict], output_path: Path):
    """Write complexity report with T1-T4 breakdown."""
    json_path = output_path / "complexity-report.json"
    json_path.write_text(json.dumps(classified, indent=2), encoding='utf-8')

    # Markdown summary
    md_path = output_path / "complexity-report.md"
    md_lines = ["# Complexity Report\n\n"]

    # Tier breakdown
    tier_counts = {"T1": 0, "T2": 0, "T3": 0, "T4": 0}
    for item in classified:
        tier_counts[item["tier"]] += 1

    md_lines.append("## Tier Distribution\n\n")
    md_lines.append("| Tier | Count | Percentage | Conversion Approach |\n")
    md_lines.append("|------|-------|------------|--------------------|\n")

    total = len(classified)
    approaches = {
        "T1": "Batch convert with LLM",
        "T2": "Batch convert with LLM",
        "T3": "Individual convert with PySpark window API",
        "T4": "Manual redesign required"
    }

    for tier in ["T1", "T2", "T3", "T4"]:
        count = tier_counts[tier]
        pct = 100 * count / total if total > 0 else 0
        md_lines.append(f"| {tier} | {count} | {pct:.1f}% | {approaches[tier]} |\n")

    # T4 objects (high priority)
    t4_objects = [item for item in classified if item["tier"] == "T4"]
    if t4_objects:
        md_lines.append("\n## T4 Objects (Require Manual Redesign)\n\n")
        md_lines.append("| Schema | Name | Type | Score | Reasons |\n")
        md_lines.append("|--------|------|------|-------|--------|\n")
        for item in sorted(t4_objects, key=lambda x: x["score"], reverse=True):
            reasons = ", ".join(item["reasons"][:2])
            md_lines.append(f"| {item['schema']} | {item['name']} | {item['type']} | {item['score']} | {reasons} |\n")

    # Conversion effort estimate
    effort_hours = (tier_counts["T1"] * 0.5 +
                    tier_counts["T2"] * 1.0 +
                    tier_counts["T3"] * 3.0 +
                    tier_counts["T4"] * 8.0)

    md_lines.append(f"\n## Estimated Conversion Effort\n\n")
    md_lines.append(f"- **Total Objects**: {total}\n")
    md_lines.append(f"- **T4 (Manual)**: {tier_counts['T4']} objects\n")
    md_lines.append(f"- **Estimated Hours**: {effort_hours:.1f} hours\n")
    md_lines.append(f"- **Estimated Days**: {effort_hours/8:.1f} days (1 developer)\n\n")

    md_path.write_text("".join(md_lines), encoding='utf-8')

    print(f"✅ Complexity report written:")
    print(f"   JSON: {json_path}")
    print(f"   Markdown: {md_path}")

# Run classification
if __name__ == "__main__":
    inventory_path = Path("./dacpac_output/schema-inventory.json")
    output_dir = Path("./dacpac_output")

    classified = classify_all_objects(inventory_path)
    write_complexity_report(classified, output_dir)

    # Summary stats
    tier_counts = {"T1": 0, "T2": 0, "T3": 0, "T4": 0}
    for item in classified:
        tier_counts[item["tier"]] += 1

    print(f"\nTier Breakdown:")
    for tier, count in tier_counts.items():
        print(f"  {tier}: {count}")
```

**Run**:
```powershell
python complexity_classifier.py
```

**Output**:
- `complexity-report.json` — Full classification data
- `complexity-report.md` — Human-readable summary with effort estimate

---

## Assessment Report

### Consolidated Discovery Report

```python
# assessment_report.py
import json
from pathlib import Path
from datetime import datetime

def generate_assessment_report(output_dir: Path):
    """Generate consolidated assessment report."""

    # Load data
    inventory_document = json.loads((output_dir / "schema-inventory.json").read_text())
    inventory = inventory_document.get("objects", [])
    complexity = json.loads((output_dir / "complexity-report.json").read_text())

    # Summary stats
    total_objects = len(inventory)
    tier_counts = {"T1": 0, "T2": 0, "T3": 0, "T4": 0}
    for item in complexity:
        tier_counts[item["tier"]] += 1

    # Effort estimate
    effort_hours = (tier_counts["T1"] * 0.5 +
                    tier_counts["T2"] * 1.0 +
                    tier_counts["T3"] * 3.0 +
                    tier_counts["T4"] * 8.0)

    # Build report
    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_objects": total_objects,
            "tier_distribution": tier_counts,
            "estimated_effort_hours": round(effort_hours, 1),
            "estimated_effort_days": round(effort_hours / 8, 1)
        },
        "recommendations": []
    }

    # Recommendations
    if tier_counts["T4"] > 0:
        report["recommendations"].append({
            "priority": "HIGH",
            "finding": f"{tier_counts['T4']} T4 objects require manual redesign",
            "action": "Review T4 objects with business stakeholders before conversion"
        })

    if total_objects > 0 and tier_counts["T4"] / total_objects > 0.3:
        report["recommendations"].append({
            "priority": "MEDIUM",
            "finding": f"T4 objects are {100*tier_counts['T4']/total_objects:.0f}% of total",
            "action": "Consider phased migration: T1-T3 first, T4 later"
        })

    # Top complex objects
    top_complex = sorted(complexity, key=lambda x: x["score"], reverse=True)[:10]
    report["top_10_complex"] = [{
        "schema": item["schema"],
        "name": item["name"],
        "type": item["type"],
        "tier": item["tier"],
        "score": item["score"],
        "reasons": item["reasons"][:3]
    } for item in top_complex]

    # Write report
    report_path = output_dir / "assessment-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f"✅ Assessment report written: {report_path}")
    print(f"\n📊 Summary:")
    print(f"   Total objects: {total_objects}")
    print(f"   T1 (simple): {tier_counts['T1']}")
    print(f"   T2 (moderate): {tier_counts['T2']}")
    print(f"   T3 (advanced): {tier_counts['T3']}")
    print(f"   T4 (complex): {tier_counts['T4']}")
    print(f"   Estimated effort: {effort_hours:.1f} hours ({effort_hours/8:.1f} days)")

# Run assessment
if __name__ == "__main__":
    output_dir = Path("./dacpac_output")
    generate_assessment_report(output_dir)
```

**Run**:
```powershell
python assessment_report.py
```

**Output**: `assessment-report.json` with summary, recommendations, and top complex objects.

---

## Migration Gap Report

After inventory and complexity classification, execute the complete [Dedicated Pool to Lakehouse Gap Assessment](dedicated-pool-gap-assessment.md). Produce:

- `migration-gap-report.json`
- `migration-gap-report.md`

The report must assess every discovered object across every required gap category, identify metadata-query failures and unknowns, and list concrete evidence and disposition for each finding. Present the Markdown report to the customer and obtain approval before conversion. Complexity and effort reports do not satisfy this requirement.

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
