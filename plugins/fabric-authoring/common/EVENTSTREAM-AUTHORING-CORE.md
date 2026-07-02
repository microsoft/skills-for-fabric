# EVENTSTREAM-AUTHORING-CORE.md — Eventstream Topology and Lifecycle Patterns for Fabric

> **Purpose**: Shared reference for Eventstream authoring skills. Covers the Eventstream resource model, source configuration, operator (transformation) types, destination configuration, stream types, item definitions, and lifecycle management via the Fabric REST API.
> **Language-agnostic** — all API references are raw REST specifications (verb, URL, headers, payload). No CLI commands or SDK code.
> **Schema source**: Property schemas are aligned with the official [`eventstream-definition.json`](https://github.com/microsoft/fabric-event-streams/blob/main/API%20Templates/eventstream-definition.json) template from `microsoft/fabric-event-streams`.

---

## Eventstream Resource Model

An Eventstream is a **graph-based real-time event ingestion and routing pipeline** in Microsoft Fabric's Real-Time Intelligence experience. Its topology consists of four node types connected by `inputNodes` references:

| Node Type | Role | Direction |
|-----------|------|-----------|
| **Source** | Ingests events into the pipeline | Entry point |
| **Operator** | Transforms events in-flight (filter, aggregate, join, etc.) | Middle |
| **Stream** | Publishes processed events (DefaultStream or DerivedStream) | Middle / Output |
| **Destination** | Routes events to a Fabric item or external endpoint | Exit point |

### Graph Flow

```text
Source → DefaultStream → [Operator(s)] → Destination(s)
                                       → DerivedStream → Destination(s)
```

**Topology optimization**: Push-based destinations (Lakehouse, Eventhouse, Custom Endpoint) can connect directly to an operator's output via `inputNodes` — a DerivedStream in between is **not required**. Use a DerivedStream only when you need the operator's output to be published to Real-Time Hub or consumed by multiple downstream nodes.

Nodes reference their inputs via `inputNodes: [{"name": "<upstream-node-name>"}]`.

### Eventstream Properties

| Property | Type | Default | Range | Description |
|----------|------|---------|-------|-------------|
| `retentionTimeInDays` | Integer | 1 | 1–90 | How long events are retained |
| `eventThroughputLevel` | Enum | `Low` | `Low`, `Medium`, `High` | Throughput tier |

---

## Source Configuration

### Source Type Catalog (API-Supported)

25 source types are available via the REST API `type` enum (per the official `microsoft/fabric-event-streams` template):

| Category | Type Enum | Description | Key Properties |
|----------|-----------|-------------|----------------|
| **Azure Messaging** | `AzureEventHub` | Azure Event Hubs — high-volume event ingestion | `dataConnectionId`, `consumerGroupName`, `inputSerialization` |
| | `AzureIoTHub` | Azure IoT Hub — device telemetry | `dataConnectionId`, `consumerGroupName`, `inputSerialization` |
| **Change Data Capture** | `AzureSQLDBCDC` | Azure SQL Database CDC | `dataConnectionId`, `tableName` |
| | `AzureSQLMIDBCDC` | Azure SQL Managed Instance CDC | `dataConnectionId`, `tableName` |
| | `AzureCosmosDBCDC` | Azure Cosmos DB CDC | `dataConnectionId`, `containerName`, `databaseName`, `offsetPolicy` |
| | `MySQLCDC` | MySQL database CDC | `dataConnectionId`, `tableName`, `serverId`, `port` |
| | `PostgreSQLCDC` | PostgreSQL database CDC | `dataConnectionId`, `tableName`, `slotName`, `port` |
| | `SQLServerOnVMDBCDC` | SQL Server on VM CDC | `dataConnectionId`, `tableName` |
| **Cloud Streaming** | `ApacheKafka` | Apache Kafka (self-hosted) | `dataConnectionId`, `topic`, `consumerGroupName`, `autoOffsetReset`, `saslMechanism`, `securityProtocol` |
| | `ConfluentCloud` | Confluent Cloud for Apache Kafka | `dataConnectionId`, `topic`, `consumerGroupName`, `autoOffsetReset` |
| | `AmazonKinesis` | Amazon Kinesis Data Streams | `dataConnectionId`, `region`, `startPosition`, `startTimestamp` |
| | `AmazonMSKKafka` | Amazon Managed Streaming for Kafka | `dataConnectionId`, `topic`, `consumerGroupName`, `autoOffsetReset`, `saslMechanism`, `securityProtocol` |
| | `GooglePubSub` | Google Cloud Pub/Sub | `dataConnectionId` |
| **Azure Services** | `AzureEventGridNamespace` | Azure Event Grid Namespace | `namespaceResourceId`, `topic` |
| | `AzureDataExplorer` | Azure Data Explorer (Kusto) | `dataConnectionId`, `databaseName`, `tableNames` |
| **IoT / Messaging** | `Mqtt` | MQTT broker | `dataConnectionId`, `serverVersion`, `topic` |
| | `SolacePubSub` | Solace PubSub+ broker | `dataConnectionId`, `pubSubType`, `messageVpnName`, `topics`, `queue`, `mapUserProperties`, `mapSolaceProperties` |
| | `RealTimeWeather` | Live weather for a GPS coordinate (Azure Maps, updated every minute, no extra Azure subscription needed) | `latitude` (float), `longitude` (float) |
| **Custom** | `CustomEndpoint` | Custom app or Kafka client via connection string | (empty — connection-string based) |
| **Sample** | `SampleData` | Built-in sample data generators | `type`: one of `Bicycles`, `YellowTaxi`, `StockMarket`, `Buses`, `SP500Stocks`, `SemanticModelLogs` |
| **Fabric System Events** | `FabricWorkspaceItemEvents` | Workspace item create/update/delete events | `eventScope`, `workspaceId`, `includedEventTypes[]`, `filters[]` |
| | `FabricJobEvents` | Fabric job lifecycle events | `eventScope`, `workspaceId`, `itemId`, `includedEventTypes[]`, `filters[]` |
| | `FabricOneLakeEvents` | OneLake file/folder change events | `tenantId`, `workspaceId`, `itemId`, `oneLakePaths[]`, `includedEventTypes[]`, `filters[]` |

> **Note**: `AzureBlobStorageEvents` and `FabricCapacityUtilizationEvents` appear in Microsoft Learn docs but are not included in the official API template. They may be valid but should be tested before use.

### Source Node Schema

```json
{
  "name": "<unique-name>",
  "type": "<SourceTypeEnum>",
  "properties": {
    "dataConnectionId": "<cloud-connection-guid>",
    "consumerGroupName": "$Default",
    "inputSerialization": {
      "type": "Json",
      "properties": { "encoding": "UTF8" }
    }
  }
}
```

- `id` (UUID): Optional on CREATE, required on UPDATE — system-generated.
- `dataConnectionId`: References a Fabric cloud connection. Required for most source types.
- `consumerGroupName`: Applies to Event Hub, IoT Hub, and Kafka-based sources.
- `inputSerialization`: Encoding of incoming events (`Json`, `Csv`, `Avro`).

### Sources Not in Official API Template

6 additional sources are available in the Fabric UI but are not present in the official `eventstream-definition.json` template: Azure Service Bus, Anomaly Detection, HTTP, MongoDB CDC, Cribl, Azure IoT Operations.

---

## Transformation Operators

### Operator Type Catalog (API-Supported)

8 operator types are available via the REST API `type` enum:

| Type | Purpose | Key Properties |
|------|---------|----------------|
| `Filter` | Select rows matching conditions | `conditions[]` with column reference, `operatorType`, value; **`value.dataType` must match the source column type** — see Literal Data Types table |
| `Aggregate` | Compute aggregates with partitioning | `aggregations[]` with `aggregateFunction`, `partitionBy`, **`duration`** (flat — NOT inside a `window` object) |
| `GroupBy` | Group by columns + aggregate within time window | `aggregations[]`, `groupBy[]`, `window` (with nested `type` + `properties.duration`) |
| `Join` | Combine two streams on a matching key | `joinType`, `joinOn[]`, `duration` |
| `ManageFields` | Rename, cast, or compute columns | `columns[]` with `type` (Rename/Cast/FunctionCall) + `alias` |
| `Union` | Merge streams with matching schemas | Input from multiple `inputNodes` |
| `Expand` | Flatten **arrays** into individual rows | `column`, `ignoreMissingOrEmpty`; **column must be array-type** — nested objects/records are rejected at runtime |
| `SQL` | Streaming SQL (Azure Stream Analytics syntax) | `query` — `SELECT...INTO...FROM` with windowing; **inputNodes must be Stream-type** (see gotcha #21) |

### AggregateFunction Enum Values

The `aggregateFunction` property on Aggregate and GroupBy operators accepts these exact values (case-sensitive):

| Value | Alias NOT Accepted |
|-------|-------------------|
| `Average` | — |
| `Sum` | — |
| `Count` | — |
| `Minimum` | `Min` ❌ is rejected |
| `Maximum` | `Max` ❌ is rejected |

### Operator Node Schema

```json
{
  "name": "<unique-name>",
  "type": "<OperatorTypeEnum>",
  "inputNodes": [{"name": "<upstream-node>"}],
  "properties": { },
  "inputSchemas": []
}
```

### Node Naming Rules

**All user-defined node names (sources, operators, destinations, DerivedStreams) MUST be:**
- **Alphanumeric only** — no underscores, hyphens, dots, or spaces
- **3–63 characters** long
- **Unique** within the topology

Use **PascalCase**: `EHStockAggregates`, `FilterPremium`, `LakehouseDest` (not `EH_stock_aggregates`, `filter-premium`)

> **Exception — DefaultStream names:** The platform auto-generates the DefaultStream name using the pattern `{eventstreamName}-stream` (e.g., `myEventstream-stream`). This system-generated name *may* contain hyphens — it is the only exception to the alphanumeric constraint. When referencing any stream in `inputNodes`, use the exact name from the topology.

> At runtime, the ASA engine generates internal identifiers by prefixing node names (e.g., `dst-`). Underscores in user-defined names cause rejection: *"Invalid output name. Please use only alphanumeric identifiers."*

### FilterOperatorType Enum Values

The `operatorType` property on Filter conditions accepts these exact values:

| Value | Meaning |
|-------|---------|
| `GreaterThan` | `>` |
| `LessThan` | `<` |
| `GreaterThanOrEqual` | `>=` |
| `LessThanOrEqual` | `<=` |
| `NotEqual` | `!=` |

> **Note**: No `EqualTo` / `Equal` / `Equals` enum has been confirmed to work. For integer equality (e.g., `x == 0`), use `LessThan` with value `1` as a workaround.

### Aggregate vs GroupBy — Schema Difference

**Aggregate** uses a flat `duration` per aggregation entry:
```json
{ "aggregateFunction": "Sum", "column": {...}, "alias": "SUM_x",
  "partitionBy": [{...}], "duration": { "value": 1, "unit": "Minute" } }
```

**GroupBy** uses a nested `window` object at the properties level:
```json
"properties": { "aggregations": [...], "groupBy": [...],
  "window": { "type": "Tumbling", "properties": { "duration": {...}, "offset": {...} } } }
```

These are NOT interchangeable. Using `window` on Aggregate or `duration` on GroupBy will fail.

### Window Types (for GroupBy)

| Window | Behaviour |
|--------|-----------|
| `Tumbling` | Fixed-size, non-overlapping intervals. Properties: `duration` (value + unit), `offset` |
| `Hopping` | Fixed-size, overlapping intervals. Properties: `duration`, `hop` |
| `Sliding` | Triggered by events, not wall-clock time |

### Literal Data Types

When building Filter conditions (or any operator property with a `value` literal), the `dataType` field **must** match the source column's actual type. There is no implicit type coercion — a type mismatch causes runtime errors and a blank operator in the UI.

| Source Column Type | `dataType` Value | Example `value` |
|--------------------|------------------|-----------------|
| int / integer      | `BigInt`         | `"100"`         |
| float / double     | `Float`          | `"50.0"`        |
| string / varchar   | `Nvarchar(max)`  | `"active"`      |
| datetime           | `DateTime`       | `"2025-01-01T00:00:00Z"` |
| boolean            | `Bit`            | `"true"`        |

> All values are passed as strings regardless of type. The `dataType` tells the engine how to interpret and compare the value.

### Filter Operator Example

```json
{
  "name": "HighTempFilter",
  "type": "Filter",
  "inputNodes": [{"name": "myEventstream-stream"}],
  "properties": {
    "conditions": [{
      "column": {
        "node": null,
        "columnName": "temperature",
        "columnPath": null,
        "expressionType": "ColumnReference"
      },
      "operatorType": "GreaterThan",
      "value": {
        "dataType": "Float",
        "value": "30.0",
        "expressionType": "Literal"
      }
    }]
  }
}
```

### GroupBy Operator Example (Tumbling Window)

```json
{
  "name": "AvgTempPerRoom",
  "type": "GroupBy",
  "inputNodes": [{"name": "myEventstream-stream"}],
  "properties": {
    "aggregations": [{
      "aggregateFunction": "Average",
      "column": {
        "node": null,
        "columnName": "temperature"
      },
      "alias": "AvgTemp"
    }],
    "groupBy": [{
      "node": null,
      "columnName": "roomId"
    }],
    "window": {
      "type": "Tumbling",
      "properties": {
        "duration": { "value": 5, "unit": "Minute" },
        "offset": { "value": 1, "unit": "Minute" }
      }
    }
  }
}
```

### Join Operator Example

```json
{
  "name": "SensorJoin",
  "type": "Join",
  "inputNodes": [{"name": "FilteredStream"}, {"name": "ReferenceStream"}],
  "properties": {
    "joinType": "Inner",
    "joinOn": [{
      "left": { "node": "leftNodeName", "columnName": "deviceId" },
      "right": { "node": "rightNodeName", "columnName": "deviceId" }
    }],
    "duration": { "value": 1, "unit": "Minute" }
  }
}
```

### ManageFields Operator Example

```json
{
  "name": "FieldTransforms",
  "type": "ManageFields",
  "inputNodes": [{"name": "myEventstream-stream"}],
  "properties": {
    "columns": [
      {
        "type": "Rename",
        "properties": {
          "column": { "node": null, "columnName": "temp" }
        },
        "alias": "temperature_celsius"
      },
      {
        "type": "Cast",
        "properties": {
          "targetDataType": "BigInt",
          "column": { "node": null, "columnName": "sensorId" }
        },
        "alias": "sensor_id_int"
      }
    ]
  }
}
```

### SQL Operator Example

```json
{
  "name": "SqlTransform",
  "type": "SQL",
  "inputNodes": [{"name": "myEventstream-stream"}],
  "properties": {
    "query": "SELECT deviceId, AVG(temperature) AS avg_temp INTO [OutputStream] FROM [myEventstream-stream] GROUP BY deviceId, TumblingWindow(minute, 5)"
  }
}
```

### SQL Operator — Design Rules

The SQL operator uses Azure Stream Analytics (ASA) SQL syntax and has the following **by-design** requirements:

1. **`INTO [alias]` must match a downstream node name.** The `INTO` clause in the SQL query routes output to a named node in the topology. The alias must exactly match the `name` of a Destination or DerivedStream node that lists this SQL operator in its `inputNodes`. If no node matches the alias, the ASA engine rejects the query at activation with: *"The output {alias} used in the query was not defined."*

2. **`FROM [alias]` must match an upstream node name.** The `FROM` clause must reference the exact `name` of the stream listed in `inputNodes` (typically the DefaultStream or a DerivedStream).

3. **Input must be a Stream-type node.** The SQL operator's `inputNodes` must reference a `DefaultStream` or `DerivedStream` — not another operator (see Gotcha #21).

4. **SQL → DerivedStream → Destination is blocked.** A Destination cannot follow a DerivedStream that is fed by a SQL operator (see Gotcha #23). Use SQL → Destination directly, or SQL → DerivedStream for Real-Time Hub publishing only.

**Example topology showing correct alias alignment:**

```text
Source → DefaultStream("MainStream") → SQL(INTO [AlertStream]) → DerivedStream("AlertStream")
                                                                          ↑ names must match
```

### CDC Sources — SQL Routing Pattern

When using CDC sources (e.g., `AzureSQLDBCDC`), events arrive in **Debezium envelope format** with nested `schema` and `payload` objects. The `payload` contains:
- `op`: operation type (`r`=read/snapshot, `c`=create, `u`=update, `d`=delete)
- `before`: row state before change (null for inserts/snapshots)
- `after`: row state after change (null for deletes)
- `source.table`: the originating table name

**Use the SQL operator to flatten and route CDC events by table:**

```sql
-- Route and flatten Orders
SELECT
    payload.op AS cdc_operation,
    payload.after.OrderId AS OrderId,
    payload.after.CustomerId AS CustomerId,
    payload.after.Status AS Status,
    payload.source.[table] AS source_table,
    EventProcessedUtcTime
INTO [LHOrders]
FROM [CdcStream]
WHERE payload.source.[table] = 'Orders'

-- Route and flatten Products to a separate destination
SELECT
    payload.op AS cdc_operation,
    payload.after.ProductId AS ProductId,
    payload.after.ProductName AS ProductName,
    payload.source.[table] AS source_table,
    EventProcessedUtcTime
INTO [LHProducts]
FROM [CdcStream]
WHERE payload.source.[table] = 'Products'
```

**Design notes:**
- **Dot notation** (`payload.after.ColumnName`) extracts nested Debezium fields into flat columns
- **`payload.source.[table]`** requires bracket escaping because `table` is a reserved word
- **Delete events** have null `after` — all extracted `after.*` columns will be empty
- **Multiple `INTO` clauses** in a single SQL operator route to different destination nodes
- **Without flattening**, Lakehouse destinations drop the nested `payload` — only metadata columns (`EventProcessedUtcTime`, `PartitionId`) survive. Eventhouse preserves the raw payload as `dynamic` columns
- **DeltaFlow (Preview)** automates this flattening and routing via the portal UI; REST API support is not yet documented

### Aggregate Operator Example

```json
{
  "name": "AvgByDevice",
  "type": "Aggregate",
  "inputNodes": [{"name": "myEventstream-stream"}],
  "properties": {
    "aggregations": [{
      "aggregateFunction": "Average",
      "column": { "node": null, "columnName": "temperature" },
      "alias": "AVG_temperature",
      "partitionBy": [{ "node": null, "columnName": "deviceId" }],
      "duration": { "value": 1, "unit": "Minute" }
    }]
  }
}
```

### Expand Operator Example

> **Expand only works on array-type columns.** If the column is a nested object/record (e.g., `temperatureSummary: { past6Hours: {...} }`), Expand will fail at runtime with: *"The column referenced is invalid because it is not of the same type as the upstream."* Use SQL with dot notation (e.g., `temperature.value`) to extract nested object fields instead.

```json
{
  "name": "FlattenTags",
  "type": "Expand",
  "inputNodes": [{"name": "myEventstream-stream"}],
  "properties": {
    "column": { "node": null, "columnName": "tags" },
    "ignoreMissingOrEmpty": true
  }
}
```

### Preview Operators

No operators are currently known to be UI-only / preview. The SQL operator was previously preview but is now confirmed in the official API template.

### Choosing the Right Operator — Decision Tree

Use this guide to pick the best operator for a given user intent. SQL is the most powerful but also the most error-prone; native operators are simpler and less likely to fail.

```text
User intent
├── Simple row filtering ("keep rows where X > Y")?
│   └── ✅ Filter operator — simplest, lowest risk
├── Rename / cast / compute columns ("rename col_a to col_b")?
│   └── ✅ ManageFields operator
├── Flatten an array column into rows ("explode tags")?
│   └── ✅ Expand operator — column MUST be array type
├── Merge two streams ("combine both feeds")?
│   └── ⚠️ Union operator — schemas must match; **currently unreliable in multi-source topologies** (see Gotcha #18) — prefer SQL UNION after projecting both branches to the same schema
├── Correlate two streams on a key ("match orders to payments")?
│   └── ⚠️ Join operator — **currently unreliable in multi-source topologies** (see Gotcha #18) — verify single-stream constraints before using
├── Time-windowed aggregation with grouping ("count per vendor every 5 min")?
│   └── ✅ GroupBy operator — uses nested `window` object
├── Simple aggregate with partitioning ("average temp per device")?
│   └── ✅ Aggregate operator — uses flat `duration`
├── Need LAG / LEAD / CASE / UNION / multiple INTO?
│   └── ✅ SQL operator (only option for advanced analytics)
├── Need CDC Debezium flattening ("flatten payload.after")?
│   └── ✅ SQL operator with dot notation
└── Need multi-destination routing ("route fraud to one table, all to another")?
    └── ✅ SQL operator with multiple SELECT...INTO clauses
```

**Rule of thumb:** If a native operator can do it, prefer it over SQL. SQL is needed only for: window functions (LAG/LEAD), CASE expressions, multi-destination routing, CDC flattening, and UNION after projecting both branches to the same schema.

### SQL Operator — Intent-to-Pattern Library

When using the SQL operator, match the user's intent to the correct pattern. Patterns are organized by complexity — start simple, escalate only as needed.

#### Tier 1: Simple Filtering (Low Risk ⭐)

**User says:** "Filter out events where temperature < 30"

```sql
SELECT *
INTO [OutputDest]
FROM [MainStream]
WHERE temperature >= 30
```

Common mistake: Forgetting `INTO [OutputDest]` — the alias must match a downstream node name exactly.

#### Tier 2: Time-Windowed Aggregation (Medium Risk ⭐⭐)

**User says:** "Count taxi rides per payment type every 5 minutes"

```sql
SELECT
    payment_type,
    COUNT(*) AS ride_count,
    SUM(fare_amount) AS total_fare
INTO [AggregatedOutput]
FROM [MainStream]
GROUP BY payment_type, TumblingWindow(minute, 5)
```

Common mistakes:
- ❌ Forgetting `TumblingWindow` in GROUP BY — required for streaming aggregation
- ❌ Wrong time unit — must be `second`, `minute`, `hour` (lowercase)
- ❌ Using `GROUP BY payment_type` without a window — streaming SQL requires a time window

#### Tier 3: Window Functions / Anomaly Detection (High Risk ⭐⭐⭐)

**User says:** "Detect temperature spikes — flag when current reading is 10° above previous"

```sql
SELECT
    deviceId,
    temperature,
    LAG(temperature, 1) OVER (PARTITION BY deviceId LIMIT DURATION(minute, 10)) AS prev_temp,
    temperature - LAG(temperature, 1) OVER (PARTITION BY deviceId LIMIT DURATION(minute, 10)) AS temp_delta
INTO [AlertOutput]
FROM [MainStream]
WHERE temperature - LAG(temperature, 1) OVER (PARTITION BY deviceId LIMIT DURATION(minute, 10)) > 10
```

Common mistakes:
- ❌ Missing `LIMIT DURATION` — ASA requires a bounded window for LAG/LEAD
- ❌ Missing `PARTITION BY` — without it, LAG looks across all devices
- ❌ Using `OVER (ORDER BY timestamp)` — ASA uses `LIMIT DURATION`, not `ORDER BY`

#### Tier 4: Conditional Routing / Fraud Detection (High Risk ⭐⭐⭐⭐)

**User says:** "Flag suspicious rides: low fare but long distance. Aggregate by payment type per minute."

```sql
-- Route suspicious rides (CASE classifies, no WHERE needed — all rows evaluated)
SELECT
    medallion,
    fare_amount,
    trip_distance,
    CASE
        WHEN fare_amount < 5.0 AND trip_distance > 10.0 THEN 'suspicious'
        ELSE 'normal'
    END AS fraud_flag
INTO [FraudAlerts]
FROM [MainStream]

-- Aggregate all rides
SELECT
    payment_type,
    COUNT(*) AS ride_count,
    AVG(fare_amount) AS avg_fare
INTO [AllRideStats]
FROM [MainStream]
GROUP BY payment_type, TumblingWindow(minute, 1)
```

Common mistakes:
- ❌ INTO alias mismatch — each INTO must match a different downstream node
- ❌ CASE without END — always close CASE expressions
- ❌ Mixing aggregated and non-aggregated columns outside GROUP BY

#### Tier 5: CDC Flattening + Multi-Table Routing (High Risk ⭐⭐⭐⭐)

**User says:** "Route CDC changes: Orders to one table, Products to another, flatten the Debezium payload"

```sql
-- Route and flatten Orders (exclude deletes where payload.after is null)
SELECT
    payload.op AS cdc_operation,
    payload.after.OrderId AS OrderId,
    payload.after.CustomerId AS CustomerId,
    payload.after.[Status] AS [Status],
    payload.source.[table] AS source_table,
    EventProcessedUtcTime
INTO [LHOrders]
FROM [CdcStream]
WHERE payload.source.[table] = 'Orders' AND payload.op <> 'd'

-- Route and flatten Products (exclude deletes)
SELECT
    payload.op AS cdc_operation,
    payload.after.ProductId AS ProductId,
    payload.after.ProductName AS ProductName,
    payload.source.[table] AS source_table,
    EventProcessedUtcTime
INTO [LHProducts]
FROM [CdcStream]
WHERE payload.source.[table] = 'Products' AND payload.op <> 'd'
```

Common mistakes:
- ❌ Forgetting bracket escaping for reserved words: `[table]`, `[Status]`, `[Close]`, `[Open]`, `[Order]`, `[Year]`
- ❌ Projecting `payload.after.*` without filtering out deletes (`op = 'd'`) — `after` is null for deletes, producing rows with null business keys
- ❌ Missing dot notation — without `payload.after.*` flattening, Lakehouse destinations only get metadata columns

#### Common Reserved Words (Not Exhaustive)

These column/field names are commonly encountered and **must** be bracket-escaped in SQL queries: `[Close]`, `[Open]`, `[Year]`, `[Order]`, `[Status]`, `[table]`, `[Date]`, `[Time]`, `[Key]`, `[Value]`, `[Type]`, `[Group]`, `[Select]`, `[From]`, `[Where]`, `[Index]`. Use exact casing as it appears in the source data (e.g., `[table]` for Debezium CDC, not `[Table]`).

### SQL Operator — Error Troubleshooting

| Error Message | Cause | Fix |
|---|---|---|
| *"The output {alias} used in the query was not defined"* | `INTO [alias]` doesn't match any downstream node name | Ensure a Destination or DerivedStream with that exact `name` has this SQL operator in its `inputNodes` |
| *"Operator 'SQL' must have parent(s) of type 'Stream'"* | SQL operator's `inputNodes` references an Operator, not a Stream | Insert a DerivedStream between the upstream operator and the SQL operator |
| *"Incorrect syntax near 'Close'"* (or Open, Year, Order, etc.) | Reserved word used without brackets | Escape with brackets: `[Close]`, `[Order]` |
| *"Comparison is not allowed for types..."* | Filter `value.dataType` doesn't match source column type | Check source schema — use `BigInt` for int, `Float` for float, `Nvarchar(max)` for string |
| Operator shows blank in UI (no error) | `dataType` mismatch in Filter/Aggregate value | Verify `dataType` matches source exactly — there is no implicit coercion |
| *"Invalid output name. Please use only alphanumeric identifiers"* | Node name contains `_`, `-`, `.`, or spaces | Use PascalCase alphanumeric names: `FilteredOutput` not `filtered_output` |
| Aggregate uses `Min`/`Max` — deployment fails silently | Wrong enum value | Use `Minimum` / `Maximum` (not `Min` / `Max`) |
| SQL→DerivedStream→Destination: destination never receives data | Blocked topology path | Wire SQL directly to Destination (`SQL → Destination`), or use DerivedStream only for Real-Time Hub |
| Expand fails: *"column referenced is invalid..."* | Expand used on nested object instead of array | Use SQL with dot notation (`obj.field`) for nested objects; Expand only works on array columns |
| Lakehouse destination only gets metadata columns (no payload) | CDC events not flattened | Add SQL operator with `payload.after.*` dot notation to flatten Debezium envelope |

### SQL Operator — Anti-Patterns

These topology and SQL patterns **will fail** — avoid them:

| ❌ Anti-Pattern | Why It Fails | ✅ Correct Pattern |
|---|---|---|
| Operator → SQL (e.g., Filter → SQL) | SQL requires Stream-type input, not Operator output | Operator → DerivedStream → SQL |
| SQL → DerivedStream → Destination | Blocked path — destination never receives data | SQL → Destination (direct), or SQL → DerivedStream (for Real-Time Hub only) |
| SQL `INTO` alias / internal stream ID with `_` or `-` | ASA engine rejects non-alphanumeric internal IDs for SQL output aliases | PascalCase alphanumeric alias: `StockAggregates` not `stock_aggregates` |
| Node name < 3 chars (`"LH"`) | API rejects names under 3 characters | Use 3+ char names: `LHDest` |
| `Min` / `Max` as AggregateFunction | Enum only accepts full names | `Minimum` / `Maximum` |
| `EqualTo` as FilterOperatorType | Not a valid enum value | `LessThan` with value+1 (for integers) or `GreaterThanOrEqual` + `LessThanOrEqual` pair |
| `window` object on Aggregate operator | Aggregate uses flat `duration`, not `window` | `"duration": {"value": 1, "unit": "Minute"}` at aggregation level |
| `duration` at properties level on GroupBy | GroupBy uses nested `window` object | `"window": {"type": "Tumbling", "properties": {"duration": ...}}` |
| Time-window aggregation without `TumblingWindow` in GROUP BY | Streaming SQL requires bounded time windows | Always include `TumblingWindow(unit, size)` in GROUP BY |
| Unescaped reserved words in SQL queries | Parser treats them as keywords | Wrap in brackets: `[Close]`, `[Status]`, `[table]` |
| Expand on nested object column | Expand only supports array columns | Use SQL with dot notation: `obj.field` |

---

## Destination Configuration

### Destination Type Catalog (API-Supported)

| Type | Purpose | Key Properties |
|------|---------|----------------|
| `Lakehouse` | Delta table ingestion | `workspaceId`, `itemId`, `schema`, `deltaTable`, `minimumRows`, `maximumDurationInSeconds`, `inputSerialization` |
| `Eventhouse` | KQL Database ingestion | `dataIngestionMode`, `workspaceId`, `itemId` (**must be KQL Database ID, NOT Eventhouse ID**), `databaseName`, `tableName` |
| `Activator` | Fabric Activator (Reflex) triggers | `workspaceId`, `itemId` |
| `CustomEndpoint` | External app / Kafka client | Connection-string based |

### Destination Node Schema

```json
{
  "name": "<unique-name>",
  "type": "<DestinationTypeEnum>",
  "properties": { },
  "inputNodes": [{"name": "<upstream-node>"}]
}
```

### Eventhouse Ingestion Modes

| Mode | Value | Behaviour | API-Automatable? |
|------|-------|-----------|------------------|
| Processed Ingestion | `ProcessedIngestion` | Events route through the Eventstream processing engine to Eventhouse | ✅ Yes — **recommended for API/CLI automation** |
| Direct Ingestion | `DirectIngestion` | Events flow directly from source to Eventhouse via Kusto streaming ingestion — lowest latency | ⚠️ Partial — requires UI-created data connection (see below) |

#### ProcessedIngestion (Recommended for API automation)

Use this mode when deploying Eventstream→Eventhouse pipelines via REST API, CLI skills, or CI/CD. No pre-existing data connection is required — the Eventstream platform handles ingestion internally.

**Required properties:**
- `workspaceId` — workspace containing the KQL Database
- `itemId` — the **KQL Database** GUID (not the Eventhouse item ID)
- `databaseName` — KQL Database display name
- `tableName` — target KQL table (the engine will auto-create a table based on the event schema it infers; if the event schema is already known, consider pre-creating the table for precise schema control)
- `inputSerialization` — **mandatory** (see Gotcha #14): `{"type": "Json", "properties": {"encoding": "UTF8"}}`

**Example:**
```json
{
  "name": "StocksRawDest",
  "type": "Eventhouse",
  "properties": {
    "dataIngestionMode": "ProcessedIngestion",
    "workspaceId": "<workspace-guid>",
    "itemId": "<kql-database-guid>",
    "databaseName": "MyKQLDatabase",
    "tableName": "StocksRaw",
    "inputSerialization": {
      "type": "Json",
      "properties": { "encoding": "UTF8" }
    }
  },
  "inputNodes": [{"name": "myEventstream-stream"}]
}
```

**Pre-requisites (can be automated via `eventhouse-authoring-cli`):**
1. *(Recommended)* KQL table pre-created with explicit schema (`.create table`) — avoids schema-inference surprises
2. Streaming ingestion policy enabled (`.alter table T policy streamingingestion enable`)

**Latency:** ~10-30 seconds (event processing engine batches before ingestion).

#### DirectIngestion (Lowest latency — requires UI setup)

Use this mode only when sub-second ingestion latency is critical AND the data connection has been pre-created via the Eventhouse UI.

> ⚠️ **API limitation:** The `connectionName` references a Fabric-managed "data stream" connection that can ONLY be created through the Eventhouse portal UI ("Get Data" → "Eventstream"). No REST API exists to create this connection programmatically. Deploying with `connectionName: null` results in a permanent error state on the destination.

**Required properties:**
- `workspaceId`, `itemId` (KQL Database GUID), `databaseName`, `tableName`
- `connectionName` — the name of the UI-created data stream connection (found in Eventhouse → KQL Database → Data streams tab)
- `mappingRuleName` — a JSON ingestion mapping on the target table

**Pre-requisites:**
1. KQL table exists with compatible schema
2. JSON ingestion mapping created (via `eventhouse-authoring-cli`): `.create table T ingestion json mapping "MappingName" '[...]'`
3. Streaming ingestion policy enabled
4. **Data stream connection created via Eventhouse UI** (not automatable via API)

**Important constraints:**
- Once a destination is deployed as DirectIngestion (`KustoPullMode`), its mode cannot be changed to ProcessedIngestion (`KustoPushMode`) via update — the API rejects with: *"Node type cannot be updated. Original type: KustoPullMode, attempted new type: KustoPushMode"*
- To switch modes: delete the destination node (use a new node ID) and recreate with the desired mode

#### Cross-Skill Collaboration Pattern

For the recommended ProcessedIngestion path, use skills in sequence:

| Step | Skill | Command |
|------|-------|---------|
| 1. Create KQL table | `eventhouse-authoring-cli` | `.create table StocksRaw (Date:datetime, Open:real, ...)` |
| 2. Enable streaming | `eventhouse-authoring-cli` | `.alter table StocksRaw policy streamingingestion enable` |
| 3. Deploy Eventstream | `eventstream-authoring-cli` | Deploy topology with ProcessedIngestion destination |

### Lakehouse Destination Example

```json
{
  "name": "SalesLakehouse",
  "type": "Lakehouse",
  "properties": {
    "workspaceId": "bbbb1111-cc22-3333-44dd-555555eeeeee",
    "itemId": "cccc2222-dd33-4444-55ee-666666ffffff",
    "schema": "",
    "deltaTable": "raw_events",
    "minimumRows": 100000,
    "maximumDurationInSeconds": 120,
    "inputSerialization": {
      "type": "Json",
      "properties": { "encoding": "UTF8" }
    }
  },
  "inputNodes": [{"name": "myEventstream-stream"}]
}
```

---

## Stream Types

| Type | Purpose |
|------|---------|
| `DefaultStream` | Main output stream from a source — created automatically |
| `DerivedStream` | Stream created from an operator's output — can be published to Real-Time Hub and subscribed to by other consumers |

### Stream Node Schema

```json
{
  "name": "myEventstream-stream",
  "type": "DefaultStream",
  "properties": {},
  "inputNodes": [{"name": "myEventHubSource"}]
}
```

DerivedStream requires `inputSerialization` in properties:

```json
{
  "name": "filteredStream",
  "type": "DerivedStream",
  "properties": {
    "inputSerialization": {
      "type": "Json",
      "properties": { "encoding": "UTF8" }
    }
  },
  "inputNodes": [{"name": "HighTempFilter"}]
}
```

---

## Eventstream Lifecycle (REST API)

### CRUD Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Create | POST | `/v1/workspaces/{workspaceId}/eventstreams` |
| Get | GET | `/v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}` |
| List | GET | `/v1/workspaces/{workspaceId}/eventstreams` |
| Update | PATCH | `/v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}` |
| Delete | DELETE | `/v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}` |

### Definition Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get Definition | GET | `/v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}/definition` |
| Update Definition | PUT | `/v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}/definition` |
| Create with Definition | POST | `/v1/workspaces/{workspaceId}/items` (type: `Eventstream`) |

### Topology API Endpoints

The Topology API provides runtime inspection, connection retrieval, and operational control — separate from the Items/Definition API. [Reference](https://learn.microsoft.com/en-us/rest/api/fabric/eventstream/topology).

| Operation | Method | Endpoint | Scope |
|-----------|--------|----------|-------|
| Get Topology | GET | `.../eventstreams/{id}/topology` | Read |
| Get Source | GET | `.../eventstreams/{id}/sources/{sourceId}` | Read |
| Get Destination | GET | `.../eventstreams/{id}/destinations/{destId}` | Read |
| Get Source Connection | GET | `.../eventstreams/{id}/sources/{sourceId}/connection` | ReadWrite |
| Get Dest Connection | GET | `.../eventstreams/{id}/destinations/{destId}/connection` | ReadWrite |
| Pause Eventstream | POST | `.../eventstreams/{id}/pause` | ReadWrite |
| Pause Source | POST | `.../eventstreams/{id}/pause/sources/{sourceId}` | ReadWrite |
| Pause Destination | POST | `.../eventstreams/{id}/pause/destinations/{destId}` | ReadWrite |
| Resume Eventstream | POST | `.../eventstreams/{id}/resume` | ReadWrite |
| Resume Source | POST | `.../eventstreams/{id}/resume/sources/{sourceId}` | ReadWrite |
| Resume Destination | POST | `.../eventstreams/{id}/resume/destinations/{destId}` | ReadWrite |

> All paths are prefixed with `/v1/workspaces/{workspaceId}`. Read scope = `Eventstream.Read.All`; ReadWrite scope = `Eventstream.ReadWrite.All`.

### Custom Endpoint Source — Retrieving Connection Details

The Items API `getDefinition` returns `"properties": {}` for Custom Endpoint sources. Use the **Topology API** to retrieve the Kafka/Event Hub connection info:

```text
GET /v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}/sources/{sourceId}/connection
```

Response:

```json
{
  "fullyQualifiedNamespace": "namespace.servicebus.windows.net",
  "eventHubName": "es_<guid>",
  "accessKeys": {
    "primaryKey": "...",
    "secondaryKey": "...",
    "primaryConnectionString": "Endpoint=sb://namespace.servicebus.windows.net/;...",
    "secondaryConnectionString": "..."
  }
}
```

**Limitation**: Only Custom Endpoint sources are supported by this endpoint.

**Kafka producer configuration** using the connection details:

| Setting | Value |
|---------|-------|
| `bootstrap_servers` | `{fullyQualifiedNamespace}:9093` |
| `topic` | `{eventHubName}` |
| `security_protocol` | `SASL_SSL` |
| `sasl_mechanism` | `PLAIN` |
| `sasl_plain_username` | `$ConnectionString` |
| `sasl_plain_password` | `{primaryConnectionString}` |

### Pause and Resume

Use pause/resume for operational control without deleting the topology:

```text
POST /v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}/pause
POST /v1/workspaces/{workspaceId}/eventstreams/{eventstreamId}/resume
```

Granular control is also available per source or destination (see table above).

### Create Eventstream (Simple)

```text
POST /v1/workspaces/{workspaceId}/eventstreams
Content-Type: application/json

{
  "displayName": "my-eventstream",
  "description": "IoT sensor data pipeline"
}
```

Response: `201 Created` with `id`, `displayName`, `description`, `type`.

---

## Item Definitions and Deployment

### Definition Structure

An Eventstream item definition consists of up to 3 parts, each base64-encoded:

| Part | Path | Required | Content |
|------|------|----------|---------|
| Topology | `eventstream.json` | ✅ | Sources, destinations, operators, streams |
| Properties | `eventstreamProperties.json` | ❌ | `retentionTimeInDays`, `eventThroughputLevel` |
| Platform | `.platform` | ❌ | Item metadata (type, displayName, logicalId) |

### Create with Definition Payload

```text
POST /v1/workspaces/{workspaceId}/items
Content-Type: application/json

{
  "displayName": "my-eventstream",
  "type": "Eventstream",
  "description": "Full topology deployment",
  "definition": {
    "parts": [
      {
        "path": "eventstream.json",
        "payload": "<base64-encoded-topology-json>",
        "payloadType": "InlineBase64"
      },
      {
        "path": "eventstreamProperties.json",
        "payload": "<base64-encoded-properties-json>",
        "payloadType": "InlineBase64"
      }
    ]
  }
}
```

### Compatibility Level

The `eventstream.json` object includes `"compatibilityLevel": "1.0"` (or `"1.1"`). Use the latest version supported by your Fabric capacity.

---

## Gotchas and Limitations

| # | Issue | Cause | Workaround |
|---|-------|-------|------------|
| 1 | Max 11 combined sources + destinations | Limit applies only to CustomEndpoint sources and CustomEndpoint/Eventhouse-direct-ingestion destinations | Other types don't count toward this limit |
| 2 | Definition payload must be base64-encoded | API contract — raw JSON is rejected | Encode the `eventstream.json` content to base64 before submitting |
| 3 | Eventstream name with `_` or `.` breaks SQL operator | Known preview limitation | Avoid underscores and dots in Eventstream display names |
| 4 | `403 Forbidden` on create | Insufficient permissions | Caller needs Contributor role or higher on the workspace |
| 5 | Source with cloud connection fails | Identity lacks connection access | Grant the calling identity (user or SPN) access to the cloud connection |
| 6 | Eventhouse DirectIngestion fails | `connectionName` references a Fabric-managed data stream connection that can only be created via UI. Deploying with `connectionName: null` leaves destination in permanent error. | **Prefer `ProcessedIngestion` mode for API automation** (no data connection needed). If DirectIngestion is required, create the data connection via Eventhouse UI first, then reference its name. See *Eventhouse Ingestion Modes* section. |
| 7 | Update Definition returns `202 Accepted` | Long-running operation | Poll the `Location` header URL until completion |
| 8 | Some sources not in official API template | `AzureBlobStorageEvents`, `FabricCapacityUtilizationEvents` in Learn docs but not in template | Test before using; may require specific API version |
| 9 | `429 Too Many Requests` | API throttling | Implement exponential backoff; respect `Retry-After` header |
| 10 | DerivedStream not visible in Real-Time Hub | Missing `inputSerialization` | Add `inputSerialization` to the DerivedStream properties |
| 11 | Destination tables are created on first data arrival | Destination tables (e.g., Lakehouse Delta tables, Eventhouse KQL tables) are not created until data actually flows through the pipeline | After deploying, allow time for the first events to arrive before querying destinations; the tables appear automatically once data flows |
| 12 | Throughput level change requires empty topology | Cannot change `eventThroughputLevel` while sources are active | Deploy an empty topology first (clear sources/operators/destinations), update the definition with the new throughput level, then redeploy the full topology |
| 13 | Only one DefaultStream per topology | API rejects definitions with multiple `DefaultStream` nodes | Use `DerivedStream` nodes (connected via operators) for additional stream branches |
| 14 | Eventhouse ProcessedIngestion destination requires `inputSerialization` | API rejects the destination without it | Add `"inputSerialization": {"type": "Json", "properties": {"encoding": "UTF8"}}` to the destination properties |
| 15 | No schema validation at deployment time | The API accepts Filter/Aggregate/GroupBy operators referencing columns that do not exist in the source (e.g., filtering on `speed` when the SampleData Bicycles schema only has `BikepointID`, `Street`, `Neighborhood`, `Latitude`) — deployment succeeds silently | Always verify operator column references against the actual source schema before deploying. See **Source Output Schemas** below |
| 16 | Create-with-definition is async (202, not 200) | `POST .../eventstreams` with a `definition` body returns `202 Accepted` + `Location` header for long-running operation polling — NOT `200 OK` | Poll the `Location` URL every 10-20s until `status` is `Succeeded` or `Failed`; `az rest` returns exit code 0 for 202 so check response status explicitly |
| 17 | Eventhouse `itemId` must be KQL Database ID | The `itemId` in Eventhouse destination properties must be the **KQL Database** GUID, not the Eventhouse item GUID. Error: "Unable to extract cluster URL from the Eventhouse KQL database item ID" | Look up the KQL Database ID via `GET .../kqlDatabases` or in the Fabric portal; `databaseName` must be the KQL DB display name |
| 18 | Join/Union operators unusable with multi-source topologies | API enforces: (1) only one `DefaultStream`, (2) `DerivedStream` must come from an operator output, (3) operators can't reference sources directly — this makes native Join/Union impossible with two separate sources | Use SQL operator with self-join (`FROM [stream] s1 JOIN [stream] s2`) or `UNION ALL` syntax within a single stream |
| 19 | Node names must be ≥3 characters | Names like `"LH"` or `"EH"` (2 chars) are rejected: "Property 'Name's value 'LH' is invalid" | Use descriptive names like `"LakehouseDest"`, `"FilterOp"`, `"EventhouseDest"` |
| 20 | Deleted Eventstream names have a cooldown period | After deleting an Eventstream, recreating with the same name fails with "ItemDisplayNameNotAvailableYet" for several minutes | Use unique suffixes (e.g., timestamps) or implement retry with backoff |
| 21 | SQL operator requires Stream-type parent node | Unlike other operators (Filter, ManageFields, etc.) which can chain directly from other operators, `SQL` requires its `inputNodes` to reference a `DefaultStream` or `DerivedStream` — not another operator. Error: "Operator 'SQL' must have parent(s) of type 'Stream'" | Insert a `DerivedStream` between the upstream operator and the SQL operator (e.g., Expand → DerivedStream → SQL) |
| 22 | `Min`/`Max` are not valid AggregateFunction enums | `"Min"` and `"Max"` are rejected. The correct values are `"Minimum"` and `"Maximum"`. See **AggregateFunction Enum Values** table above | Use `Minimum` and `Maximum` (not `Min`/`Max`) |
| 23 | SQL→DerivedStream→Destination path is blocked | A Destination node cannot be downstream of a path containing a SQL operator followed by a DerivedStream. Error: "Destination cannot be in a path that contains SQL operator followed by a derived stream" | Connect SQL directly to the Destination (no DerivedStream in between); use DerivedStream from SQL only for Real-Time Hub publishing with no downstream Destination |
| 24 | `EqualTo` is not a valid FilterOperatorType | The equality comparison enum is not confirmed. Known valid values: `GreaterThan`, `LessThan`, `GreaterThanOrEqual`, `LessThanOrEqual`, `NotEqual` | For integer equality (e.g., `x == 0`), use `LessThan` with value `1` as a workaround |
| 25 | Aggregate operator uses flat `duration`, not `window` | Unlike GroupBy which uses a nested `window` object, Aggregate requires `duration` as a direct property per aggregation entry. Using `window` on Aggregate causes "Required property 'duration' not found" | Use `"duration": { "value": N, "unit": "Minute" }` directly inside each aggregation |
| 26 | Data flow starts automatically after successful deployment | A correct topology begins processing events as soon as the `Create with Definition` POST succeeds (202 → completion). No manual portal activation is needed — this is by design | Ensure the topology is correct before deploying; incorrect definitions may deploy successfully but fail at runtime |
| 27 | Node names must be alphanumeric only (no underscores) | At runtime the ASA engine generates internal output identifiers by prefixing node names (e.g., `dst-`). If the node name contains underscores, the resulting identifier is rejected: *"Invalid output name 'dst-eh_stock_aggregates'. Please use only alphanumeric identifiers with [3-63] characters."* | Use PascalCase for ALL node names — sources, operators, destinations, and streams (e.g., `EHStockAggregates` not `EH_stock_aggregates`) |
| 28 | Expand operator requires array-type columns | Expand only works on columns that contain JSON arrays (e.g., `[{...}, {...}]`). Nested objects/records (e.g., `temperatureSummary: { past6Hours: {...} }`) are rejected at runtime: *"The column referenced is invalid because it is not of the same type as the upstream."* | Use SQL with dot notation to extract nested object fields (e.g., `SELECT temperature.value AS temp_c FROM [stream]`) |
| 29 | CDC Debezium events lose payload in Lakehouse destinations | CDC sources (e.g., `AzureSQLDBCDC`) emit Debezium-envelope JSON with deeply nested `schema` and `payload` objects. When sent directly to a Lakehouse Delta table, only flat metadata columns (`EventProcessedUtcTime`, `PartitionId`, `EventEnqueuedUtcTime`) survive — the nested payload is dropped. Eventhouse handles this correctly via `dynamic` columns | Use a SQL operator to flatten the Debezium payload before the Lakehouse destination (e.g., `SELECT payload.op, payload.after.CustomerId ... INTO [LHDest] FROM [stream]`), or enable DeltaFlow (Preview) which handles CDC-to-analytics transformation automatically |

### Source Output Schemas

Reference these schemas when building operators that reference source columns. The API performs **no validation** — incorrect column names deploy silently but produce runtime errors.

#### SampleData Schemas

| Type Enum | Fields |
|-----------|--------|
| `Bicycles` | `BikepointID` (int), `Street` (string), `Neighborhood` (string), `Latitude` (float), `Longitude` (float), `No_Bikes` (int), `No_Empty_Docks` (int) |
| `YellowTaxi` | `VendorID` (int), `tpep_pickup_datetime` (datetime), `tpep_dropoff_datetime` (datetime), `passenger_count` (int), `trip_distance` (float), `RatecodeID` (int), `store_and_fwd_flag` (string), `PULocationID` (int), `DOLocationID` (int), `payment_type` (int), `fare_amount` (float), `extra` (float), `mta_tax` (float), `tip_amount` (float), `tolls_amount` (float), `improvement_surcharge` (float), `total_amount` (float) |
| `StockMarket` | `symbol` (string), `price` (float), `volume` (int), `time` (datetime) |
| `Buses` | `Timestamp` (datetime), `TripId` (string), `StationNumber` (int), `SchedulTime` (datetime), `Properties` (string) |
| `SP500Stocks` | `Date` (datetime), `Open` (float), `High` (float), `Low` (float), `Close` (float), `Adjusted_Close` (float), `Volume` (int), `Ticker` (string) |
| `SemanticModelLogs` | `Timestamp` (datetime), `OperationName` (string), `ItemId` (string), `ItemKind` (string), `ItemName` (string), `WorkspaceId` (string), `WorkspaceName` (string), `CapacityId` (string) |

#### RealTimeWeather Schema

Powered by Azure Maps Weather service. Updated every minute per location. No Azure Maps account needed — cost is included in Fabric capacity.

| Field | Type | Description |
|-------|------|-------------|
| `dateTime` | datetime | Observation time (ISO 8601) |
| `description` | string | Weather condition phrase (e.g., "Partly cloudy") |
| `iconCode` | int | Numeric icon identifier |
| `hasPrecipitation` | boolean | Whether precipitation is occurring |
| `temperature` | object | `{ "value": float, "unit": string }` — current temperature |
| `realFeelTemperature` | object | RealFeel™ temperature |
| `realFeelTemperatureShade` | object | RealFeel™ in shade |
| `relativeHumidity` | int | Humidity percentage (0–100) |
| `dewPoint` | object | Dew point temperature |
| `wind` | object | `{ "speed": { "value", "unit" }, "direction": { "degrees", "localizedDescription" } }` |
| `windGust` | object | Wind gust speed and direction |
| `uvIndex` | int | UV radiation strength |
| `visibility` | object | Visibility distance |
| `cloudCover` | int | Cloud cover percentage (0–100) |
| `pressure` | object | Atmospheric pressure |
| `precipitationSummary` | object | Precipitation totals over past 1/6/12/24 hours |
| `temperatureSummary` | object | Temperature min/max over past 6/12/24 hours |
| `daytime` | boolean | `true` = day, `false` = night |

> **Tip:** For Filter/Aggregate on nested fields (e.g., `temperature.value`), use the `Expand` operator first or reference via `columnPath`. For simple comparisons, use top-level fields like `relativeHumidity`, `uvIndex`, `cloudCover`.
