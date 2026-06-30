# ITEM-DEFINITIONS-CORE.md — Fabric Item Definition Structures

> **Purpose**: Definition envelope, platform file, per-item-type parts, content structure, and decoded examples.
> Used by skills that create, read, or update item definitions programmatically.

---

## Definition Envelope

All definition payloads share a common envelope:

```json
{
  "definition": {
    "format": "<format>",
    "parts": [
      {
        "path": "<filePath>",
        "payload": "<base64-encoded-content>",
        "payloadType": "InlineBase64"
      }
    ]
  }
}
```

- `format` — item-type-specific (e.g. `ipynb`, `TMDL`, `PBIR`). Most item types have a single default format (omit or set to `null`).
- `parts` — array of definition files. Each part has a `path` (file name/path), `payload` (Base64-encoded content), and `payloadType` (always `InlineBase64`).

### Platform File

The `.platform` part contains item metadata (type, display name, description, logical ID). It is:
- **Returned** by Get Item Definition (always included).
- **Accepted** by Create Item with Definition (optional).
- **Accepted** by Update Item Definition **only** when `?updateMetadata=true` is set.

> Ref: https://learn.microsoft.com/en-us/fabric/cicd/git-integration/source-code-format

## Per-Item-Type Definitions

Not all item types support definition APIs. The subsections below document each supported type’s parts, formats, and decoded content structure.

### Support Matrix

| Item Type | Supported Formats | Section |
|---|---|---|
| Notebook | `ipynb`, `FabricGitSource` | [Notebook](#notebook) |
| DataPipeline | *(default)* | [DataPipeline](#datapipeline) |
| SemanticModel | `TMSL`, `TMDL` (Prefer) | [SemanticModel](#semanticmodel) |
| Report | `PBIR-Legacy`, `PBIR` (Prefer) | [Report](#report) |
| Lakehouse | *(default)* | [Lakehouse](#lakehouse) |
| SparkJobDefinition | `SparkJobDefinitionV1`, `SparkJobDefinitionV2` | [SparkJobDefinition](#sparkjobdefinition) |
| Environment | *(default)* | [Environment](#environment) |
| Eventhouse | *(default)* | [Eventhouse](#eventhouse) |
| KQLDatabase | *(default)* | [KQLDatabase](#kqldatabase) |
| KQLDashboard | *(default)* | [Other Item Types](#other-item-types) |
| KQLQueryset | *(default)* | [Other Item Types](#other-item-types) |
| CopyJob | *(default)* | [Other Item Types](#other-item-types) |
| Dataflow | *(default)* | [Other Item Types](#other-item-types) |
| DataBuildToolJob | *(default)* | [Other Item Types](#other-item-types) |
| Eventstream | *(default)* | [Other Item Types](#other-item-types) |
| EventSchemaSet | *(default)* | [Other Item Types](#other-item-types) |
| GraphQLApi | *(default)* | [Other Item Types](#other-item-types) |
| GraphModel | *(default)* | [Other Item Types](#other-item-types) |
| HLSCohort | *(default)* | [Other Item Types](#other-item-types) |
| MirroredDatabase | *(default)* | [Other Item Types](#other-item-types) |
| MirroredAzureDatabricksCatalog | *(default)* | [Other Item Types](#other-item-types) |
| MountedDataFactory | *(default)* | [Other Item Types](#other-item-types) |
| Reflex | *(default)* | [Other Item Types](#other-item-types) |
| SnowflakeDatabase | *(default)* | [Other Item Types](#other-item-types) |
| VariableLibrary | *(default)* | [VariableLibrary](#variablelibrary) |

> Full schema index: https://github.com/microsoft/json-schemas/tree/main/fabric/item

### Notebook

> Spec: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/notebook-definition

**Formats**: `ipynb` (default), `FabricGitSource`

| Part Path | Content | Required |
|---|---|---|
| `notebook-content.ipynb` (ipynb format) | Jupyter notebook JSON | Yes |
| `notebook-content.py` / `.sql` / `.scala` / `.r` (FabricGitSource) | Source code with metadata comments | Yes |
| `.platform` | Item metadata JSON | No |

> **Note**: With `FabricGitSource`, the file extension matches the notebook language: `.py` (PySpark/Python), `.sql` (Spark SQL), `.scala` (Scala), `.r` (SparkR).

**Decoded ipynb content** (standard Jupyter format):

```json
{
  "nbformat": 4,
  "nbformat_minor": 5,
  "cells": [
    {
      "cell_type": "code",
      "source": ["# Welcome to your new notebook\n"],
      "execution_count": null,
      "outputs": [],
      "metadata": {}
    }
  ],
  "metadata": {
    "language_info": { "name": "python" }
  }
}
```

---

### DataPipeline

> Spec: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/datapipeline-definition

**Formats**: *(default — no format parameter needed)*

| Part Path | Content | Required |
|---|---|---|
| `pipeline-content.json` | Pipeline activities JSON | Yes |
| `.platform` | Item metadata JSON | No |

**Decoded content structure**:

```json
{
  "properties": {
    "description": "Pipeline description",
    "activities": [
      {
        "name": "ActivityName",
        "type": "TridentNotebook",
        "dependsOn": [],
        "policy": {
          "timeout": "0.12:00:00",
          "retry": 0,
          "retryIntervalInSeconds": 30
        },
        "typeProperties": {
          "notebookId": "<guid>",
          "workspaceId": "<guid>"
        }
      }
    ]
  }
}
```

**Key activity types**: `TridentNotebook`, `Copy`, `Lookup`, `GetMetadata`, `ForEach`, `IfCondition`, `Switch`, `Until`, `Wait`, `Fail`, `SetVariable`, `AppendVariable`, `ExecutePipeline`, `SparkJobDefinition`, `Script`, `WebActivity`, `PBISemanticModelRefresh`, `Delete`, `Filter`.

> **Note**: Each activity type has different `typeProperties`. The full activity type schemas are extensive (~30+ types). See the spec link above for complete `typeProperties` per activity type.

---

### SemanticModel

> Spec: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/semantic-model-definition

**Formats**: `TMSL`, `TMDL`

| Part Path (TMSL) | Content | Required |
|---|---|---|
| `model.bim` | Tabular model JSON (TMSL) | Yes |
| `definition.pbism` | Semantic model connection | Yes |
| `diagramLayout.json` | Diagram layout | No |
| `.platform` | Item metadata JSON | No |

| Part Path (TMDL) | Content | Required |
|---|---|---|
| `definition/database.tmdl` | Database definition | Yes |
| `definition/model.tmdl` | Model definition | Yes |
| `definition/tables/<TableName>.tmdl` | Per-table definitions | Yes |
| `definition.pbism` | Semantic model connection | Yes |
| `diagramLayout.json` | Diagram layout | No |
| `.platform` | Item metadata JSON | No |

---

### Report

> Spec: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/report-definition
> JSON Schemas: [`report/3.1.0`](https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.1.0/schema.json), [`page/1.0.0`](https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.0.0/schema.json)
> Schema index: https://github.com/microsoft/json-schemas/tree/main/fabric/item/report

**Formats**: `PBIR-Legacy`, `PBIR`

| Part Path (PBIR-Legacy) | Content | Required |
|---|---|---|
| `report.json` | Report layout and visuals | Yes |
| `definition.pbir` | Semantic model reference | Yes |
| `StaticResources/RegisteredResources/*` | Custom visuals, images, themes | No |
| `StaticResources/SharedResources/BaseThemes/*` | Base themes | No |
| `.platform` | Item metadata JSON | No |

| Part Path (PBIR) | Content | Required |
|---|---|---|
| `definition/report.json` | Report-level settings | Yes |
| `definition/version.json` | Format version | Yes |
| `definition/pages/pages.json` | Page listing | Yes |
| `definition/pages/<pageId>/page.json` | Per-page layout | Yes |
| `definition/pages/<pageId>/visuals/<visualId>/visual.json` | Per-visual config | Yes |
| `definition.pbir` | Semantic model reference | Yes |
| `StaticResources/RegisteredResources/*` | Custom visuals, images, themes | No |
| `.platform` | Item metadata JSON | No |

> **Important**: `definition.pbir` holds the semantic model reference. Fabric REST API only supports `byConnection` references (not `byPath`).

---

### Lakehouse

> Spec: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/lakehouse-definition

**Formats**: `LakehouseDefinitionV1`

| Part Path | Content | Required |
|---|---|---|
| `lakehouse.metadata.json` | Lakehouse properties (e.g., `defaultSchema`) | Yes |
| `shortcuts.metadata.json` | OneLake shortcuts array | No |
| `data-access-roles.json` | Data access roles (requires ALM setting enabled) | No |
| `alm.settings.json` | ALM settings for git/deployment pipelines | No |
| `.platform` | Item metadata JSON | No |

**Decoded lakehouse.metadata.json**:

```json
{ "defaultSchema": "dbo" }
```

**Decoded shortcuts.metadata.json** (array of shortcuts):

```json
[
  {
    "name": "TestShortcut",
    "path": "/Tables/dbo",
    "target": {
      "type": "OneLake",
      "oneLake": {
        "path": "Tables/dbo/publicholidays",
        "itemId": "00000000-0000-0000-0000-000000000000",
        "workspaceId": "00000000-0000-0000-0000-000000000000"
      }
    }
  }
]
```

> Supported shortcut target types: `OneLake`, `AdlsGen2`, `AmazonS3`, `GoogleCloudStorage`, `S3Compatible`, `Dataverse`. Each has different connection properties — see spec link.

---

### SparkJobDefinition

> Spec: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/spark-job-definition

**Formats**: `SparkJobDefinitionV1`, `SparkJobDefinitionV2`

| Part Path (V1) | Content | Required |
|---|---|---|
| `SparkJobDefinitionV1.json` | Job configuration JSON | Yes |
| `.platform` | Item metadata JSON | No |

| Part Path (V2) | Content | Required |
|---|---|---|
| `SparkJobDefinitionV1.json` | Job configuration JSON (same schema as V1) | Yes |
| `Main/<filename>` | Main executable file (e.g., `Main/main.py`) | No |
| `Libs/<filename>` | Library files (e.g., `Libs/lib1.py`) — multiple allowed | No |
| `.platform` | Item metadata JSON | No |

> **Note**: V2 only supports uploading `.py` and `.R` files. JAR files are not supported in `Main` or `Libs` parts. The JSON file is named `SparkJobDefinitionV1.json` even in V2 format (historical naming).

**Decoded SparkJobDefinitionV1.json**:

```json
{
  "executableFile": null,
  "defaultLakehouseArtifactId": "",
  "mainClass": "",
  "additionalLakehouseIds": [],
  "retryPolicy": null,
  "commandLineArguments": "",
  "additionalLibraryUris": [],
  "language": "",
  "environmentArtifactId": null
}
```

---

### Environment

> Spec: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/environment-definition

**Formats**: *(default — set format to `null`)*

| Part Path | Content | Required |
|---|---|---|
| `Libraries/CustomLibraries/<name>.jar` | Custom JAR library | No |
| `Libraries/CustomLibraries/<name>.py` | Custom Python script | No |
| `Libraries/CustomLibraries/<name>.whl` | Custom wheel package | No |
| `Libraries/CustomLibraries/<name>.tar.gz` | Custom R archive | No |
| `Libraries/PublicLibraries/environment.yml` | Conda/pip dependencies | No |
| `Setting/Sparkcompute.yml` | Spark compute settings | No |
| `.platform` | Item metadata JSON | No |

**Decoded environment.yml** (conda format):

```yaml
dependencies:
  - matplotlib==0.10.1
  - scipy==0.0.1
  - pip:
      - fuzzywuzzy==0.18.0
      - numpy==0.1.28
```

**Decoded Sparkcompute.yml**:

```yaml
enable_native_execution_engine: false
instance_pool_id: 655fc33c-2712-45a3-864a-b2a00429a8aa
driver_cores: 4
driver_memory: 28g
executor_cores: 4
executor_memory: 28g
dynamic_executor_allocation:
  enabled: true
  min_executors: 1
  max_executors: 2
spark_conf:
  spark.acls.enable: true
runtime_version: "1.3"
```

---

### VariableLibrary

> Spec: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/variable-library-definition
> REST API: https://learn.microsoft.com/en-us/rest/api/fabric/variablelibrary/items

**Formats**: *(default — no format parameter needed)*

> **Critical**: Variable Library does **NOT** support the `format` field in definition requests. Omit it entirely — including `"format": null"` may cause errors.

| Part Path | Content | Required |
|---|---|---|
| `variables.json` | Variable names, types, and default values | Yes |
| `settings.json` | Value Set ordering and library settings | Yes |
| `valueSets/<name>.json` | Per-environment overrides | Only when using Value Sets |
| `.platform` | Item metadata JSON | No |

#### Supported Variable Types

| Type | Description |
|---|---|
| `String` | Text values |
| `Boolean` | true / false |
| `Number` | Floating-point |
| `Integer` | Whole numbers |
| `DateTime` | ISO 8601 date-time |
| `ItemReference` | Fabric item GUID binding (lakehouse, warehouse) |

#### Decoded Content

**variables.json:**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/variableLibrary/definition/variables/1.0.0/schema.json",
  "variables": [
    {
      "name": "lakehouse_name",
      "note": "",
      "type": "String",
      "value": "bronze_lakehouse"
    },
    {
      "name": "enable_logging",
      "note": "",
      "type": "Boolean",
      "value": "true"
    },
    {
      "name": "target_warehouse",
      "note": "",
      "type": "ItemReference",
      "value": {
        "itemId": "bbbbbbbb-1111-2222-3333-cccccccccccc",
        "workspaceId": "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb"
      }
    }
  ]
}
```

**settings.json** (always present; `valueSetsOrder` is empty when no Value Sets are used):

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/variableLibrary/definition/settings/1.0.0/schema.json",
  "valueSetsOrder": []
}
```

When Value Sets are configured, list them in order:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/variableLibrary/definition/settings/1.0.0/schema.json",
  "valueSetsOrder": ["test", "prod"]
}
```

Each entry in `valueSetsOrder` must have a corresponding file under `valueSets/`.

**valueSets/dev.json:**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/variableLibrary/definition/valueSet/1.0.0/schema.json",
  "name": "dev",
  "variableOverrides": [
    { "name": "lakehouse_name", "value": "bronze_dev" },
    { "name": "enable_logging", "value": "true" }
  ]
}
```

#### Notebook Integration

Use `notebookutils.variableLibrary.getLibrary()` + dot notation:

```python
lib = notebookutils.variableLibrary.getLibrary("MyConfig")
name = lib.lakehouse_name          # String
flag = lib.enable_logging          # Returns string "true"/"false"

# Boolean: compare as string — bool("false") is True in Python!
if flag.lower() == "true": ...

# ❌ WRONG — .get("lib", "var") does not exist, causes runtime failure
```

> Ref: https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-utilities#variable-library-utilities

#### Pipeline Integration

Pipelines consume Variable Library values via `libraryVariables` in the pipeline JSON definition (sibling to `activities`):

```json
{
  "properties": {
    "activities": [{
      "name": "Run ETL",
      "type": "TridentNotebook",
      "typeProperties": {
        "notebookId": {
          "value": "@pipeline().libraryVariables.notebook_id",
          "type": "Expression"
        }
      }
    }],
    "libraryVariables": {
      "notebook_id": {
        "libraryName": "MyConfig",
        "libraryId": "<guid>",
        "variableName": "notebook_id",
        "type": "String"
      }
    }
  }
}
```

Each `libraryVariables` entry requires: `libraryName`, `libraryId`, `variableName`, and `type`.

**Pipeline type mappings** (do NOT use Variable Library type names):

| Variable Library Type | Pipeline Type |
|---|---|
| Boolean | **Bool** |
| Integer | **Int** |
| Number | **Double** |
| DateTime | **String** |
| String | **String** |
| ItemReference | **String** |

Dynamic references must use expression objects: `{"value": "@pipeline().libraryVariables.x", "type": "Expression"}`. A bare string is treated as a literal.

#### Gotchas

| # | Issue | Resolution |
|---|---|---|
| 1 | `.get("lib", "var")` fails at runtime | Use `getLibrary("lib").var` — always dot notation |
| 2 | `bool("false")` → `True` | Compare as string: `.lower() == "true"` |
| 3 | Definition rejected — format field | Variable Library does not support `format`; omit entirely |
| 4 | Pipeline variable wrong type | Map correctly: Boolean→Bool, Integer→Int, Number→Double |
| 5 | Pipeline expression literal | Wrap in `{"value": "...", "type": "Expression"}` |
| 6 | Pipeline variable not resolving | Include both `libraryName` and `libraryId` |
| 7 | Value Sets ignored | Add `valueSetsOrder` to `settings.json` |
| 8 | Value Set validation error | Create a matching file under `valueSets/` for every entry in `valueSetsOrder` |

---

### Eventhouse

> Spec: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/eventhouse-definition

**Formats**: `JSON`

| Part Path | Content | Required |
|---|---|---|
| `EventhouseProperties.json` | Eventhouse properties (currently empty: `{}`) | Yes |
| `.platform` | Item metadata JSON | No |

---

### KQLDatabase

> Spec: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/eventhouse-database-definition

**Formats**: `JSON`

| Part Path | Content | Required |
|---|---|---|
| `DatabaseProperties.json` | Database configuration JSON | Yes |
| `DatabaseSchema.kql` | KQL schema script (tables, functions, materialized views) | No |
| `.platform` | Item metadata JSON | No |

**Decoded DatabaseProperties.json**:

```json
{
  "databaseType": "ReadWrite",
  "parentEventhouseItemId": "<eventhouse-item-id>",
  "oneLakeCachingPeriod": "P36500D",
  "oneLakeStandardStoragePeriod": "P365000D"
}
```

**Decoded DatabaseSchema.kql** (KQL management commands):

```kql
.create-merge table MyLogs (Level:string, Timestamp:datetime, UserId:string, TraceId:string, Message:string, ProcessId:int)
```

---

### Other Item Types

The following item types also support definition APIs. See each spec link for full schema details.

| Item Type | Main Part Path(s) | Spec |
|---|---|---|
| KQLDashboard | `RealTimeDashboard.json` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/eventhouse-dashboard-definition) |
| KQLQueryset | `RealTimeQueryset.json` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/eventhouse-queryset-definition) |
| CopyJob | `copyjob-content.json` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/copyjob-definition) |
| Dataflow | `queryMetadata.json`, `mashup.pq` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/dataflow-definition) |
| DataBuildToolJob | `dbt-content.json` (live API; docs/spec say `dbtjob-content.json`) + `Code/dbt/*` project files | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/dbtjob-definition) |
| Eventstream | `eventstream.json`, `eventstreamProperties.json` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/eventstream-definition) |
| EventSchemaSet | `EventSchemaSetDefinition.json` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/eventschemaset-definition) |
| GraphQLApi | `graphql-definition.json` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/graphql-api-definition) |
| GraphModel | *(multiple JSON parts)* | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/graph-model-definition) |
| HLSCohort | `healthcarecohort.metadata.json` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/hlscohort-definition) |
| MirroredDatabase | `mirroring.json` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/mirrored-database-definition) |
| MirroredAzureDatabricksCatalog | `definition.json` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/mirrored-azuredatabricks-unitycatalog-definition) |
| MountedDataFactory | `mountedDataFactory-content.json` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/mounted-data-factory-definition) |
| Reflex | `ReflexEntities.json` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/reflex-definition) |
| SnowflakeDatabase | `SnowflakeDatabaseProperties.json` | [Spec](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/snowflake-database-definition) |

> Full schema index: https://github.com/microsoft/json-schemas/tree/main/fabric/item
> Item definition overview: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/item-definition-overview
