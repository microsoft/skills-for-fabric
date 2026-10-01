# Synapse Connectivity Migration — Linked Services → Fabric Data Connections & OneLake Shortcuts

Reference for migrating Synapse Analytics connectivity patterns to Microsoft Fabric.

---

## Decision Guide: What Replaces a Linked Service?

Every response that migrates or explains a Synapse Linked Service must first state the complete distinction: use **Fabric Data Connections for external databases and services**, and use **OneLake Shortcuts for ADLS Gen2 or Blob storage**. State both replacement classes even when the discovered Linked Service needs only one, then name which class applies to that specific source.

| Synapse Linked Service Type | Fabric Replacement | When to Use |
|---|---|---|
| **Azure Data Lake Storage Gen2** | **OneLake Shortcut** (ADLS Gen2 shortcut) | Primary pattern — mount existing storage as a Lakehouse shortcut; no data copy |
| **Azure Blob Storage** | **OneLake Shortcut** (Azure Blob shortcut) | Same as ADLS — shortcut avoids re-ingestion |
| **Azure SQL Database** | **Fabric Data Connection** (SQL auth or Entra ID) | Fabric notebooks and pipelines connect via JDBC or Copy activity |
| **Azure SQL Managed Instance** | **Fabric Data Connection** (SQL) | JDBC in notebooks; Copy activity in pipelines |
| **Azure Synapse Analytics (SQL Pool)** | Not needed post-migration | Source becomes Fabric Warehouse |
| **Azure Cosmos DB** | **Fabric Data Connection** (Cosmos DB connector) | Use Spark connector with notebookutils credential |
| **Azure Event Hubs / Service Bus** | **Fabric Eventstream** or **Data Connection** | Eventstream for real-time; connection for batch |
| **REST / HTTP** | **Web activity** in Fabric Pipelines | For pipeline REST calls |
| **Key Vault** (for secrets) | `notebookutils.credentials.getSecret(keyVaultUrl, name)` | Direct Key Vault SDK call — no connection needed |
| **On-premises SQL (via IR)** | **On-premises Data Gateway** + Fabric Data Connection | Configure gateway in Fabric capacity settings |

---

## OneLake Shortcut: Replacing ADLS Gen2 Linked Services

This is the most common migration — Synapse often uses ADLS Gen2 linked services to access raw data.

### In Fabric Portal (UI)
1. Open the target **Lakehouse** → **Files** section
2. Select **New shortcut** → **Azure Data Lake Storage Gen2**
3. Provide the ADLS Gen2 URL and authentication (Organizational account / Service Principal / SAS)
4. The shortcut appears under `Files/` and is accessible via `abfss://` OneLake paths

### Via REST API

```bash
# Create a OneLake Shortcut to ADLS Gen2
WORKSPACE_ID="<workspace_id>"
LAKEHOUSE_ID="<lakehouse_id>"
TOKEN=$(az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv)

az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/items/${LAKEHOUSE_ID}/shortcuts" \
  --headers "Authorization=Bearer ${TOKEN}" "Content-Type=application/json" \
  --body '{
    "name": "raw_data",
    "path": "Files",
    "target": {
      "type": "AdlsGen2",
      "adlsGen2": {
        "location": "https://<storageaccount>.dfs.core.windows.net",
        "subpath": "/<container>/<folder>",
        "connectionId": "<connection-id>"
      }
    }
  }'
```

### Accessing Shortcut Data in Notebooks

```python
# Synapse — direct ADLS path via Linked Service auth
df = spark.read.parquet("abfss://container@storageaccount.dfs.core.windows.net/path/")

# Fabric — OneLake path after shortcut creation
df = spark.read.parquet("abfss://workspacename@onelake.dfs.fabric.microsoft.com/lakehouse.Lakehouse/Files/raw_data/path/")

# Or using relative path (within notebook's attached Lakehouse)
df = spark.read.parquet("Files/raw_data/path/")
```

---

## Fabric Data Connection: Replacing External Database Linked Services

For Synapse linked services pointing to external databases (Azure SQL, Cosmos DB, etc.), create a Fabric Data Connection.

### Creating a Data Connection (Portal)
1. Navigate to **Fabric workspace** → **New** → **Connection**
2. Choose the connector type (SQL Server, Azure SQL, etc.)
3. Configure host, database, credentials (Entra ID or username/password from Key Vault)
4. Save and reference by name from notebooks or pipelines

### Using a Data Connection in a Notebook

```python
# Read from external SQL via notebookutils connection token
conn_token = notebookutils.connection.getConnectionToken("AzureSQL_MyDB")

jdbc_url = "jdbc:sqlserver://<server>.database.windows.net;databaseName=<db>;encrypt=true"
df = spark.read.format("jdbc") \
    .option("url", jdbc_url) \
    .option("dbtable", "dbo.MyTable") \
    .option("accessToken", conn_token) \
    .load()
```

---

## Key Vault Secret Migration

Synapse Linked Services for Key Vault are replaced by direct `notebookutils.credentials.getSecret()` calls.

```python
# Synapse — Key Vault Linked Service (NOT available in Fabric)
secret = mssparkutils.credentials.getSecret("MyKeyVaultLinkedService", "my-secret")

# Fabric — direct Key Vault call using Entra ID token
secret = notebookutils.credentials.getSecret(
    "https://mykeyvault.vault.azure.net/",
    "my-secret"
)
```

> The Fabric notebook's Managed Identity (or the logged-in user's Entra ID) must have **Key Vault Secrets User** role on the Key Vault.

---

## Integration Runtime → On-Premises Data Gateway

| Synapse IR Type | Fabric Equivalent |
|---|---|
| **Azure Integration Runtime** (cloud-to-cloud) | Not needed — Fabric Pipelines use managed compute |
| **Self-hosted IR** (on-premises connectivity) | **On-premises Data Gateway** — install on on-prem network, register in Fabric |
| **Azure-SSIS IR** | Not directly supported — migrate SSIS packages to Fabric Pipelines or Azure Data Factory |

Configure the On-premises Data Gateway in **Fabric Admin Portal** → **Connections and Gateways**.

---

## Pipeline Connectivity: Synapse Dataset → Fabric Pipeline Source/Sink

In Synapse Pipelines, datasets define the connection + path. In Fabric Pipelines, the connection and path are inlined into the Copy activity.

```json
// Synapse Pipeline Copy Activity (dataset reference)
{
  "source": { "type": "AzureBlobFSSource", "dataset": { "referenceName": "MyADLSDataset" } }
}

// Fabric Pipeline Copy Activity (inline connection)
{
  "source": {
    "type": "DelimitedTextSource",
    "storeSettings": {
      "type": "AzureBlobFSReadSettings",
      "fileSystemName": "container",
      "folderPath": "path/to/data",
      "connectionRef": "MyDataConnection"
    }
  }
}
```
