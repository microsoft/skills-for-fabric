# Data Source — Semantic Model Connection

A paginated report binds to a Power BI semantic model through a single RDL `<DataSource>` using the
`PBIDATASET` provider.

## Use the `pbiazure` / `sobe_wowvirtualserver-<GUID>` form

```xml
<DataSource Name="SemanticModel">
  <ConnectionProperties>
    <DataProvider>PBIDATASET</DataProvider>
    <ConnectString>Data Source=pbiazure://api.powerbi.com/;Identity Provider="https://login.microsoftonline.com/organizations, https://analysis.windows.net/powerbi/api, f0b72488-7082-488a-a7e8-eada97bd842d";Initial Catalog=sobe_wowvirtualserver-{DATASET_GUID};Integrated Security=ClaimsToken</ConnectString>
  </ConnectionProperties>
  <rd:SecurityType>None</rd:SecurityType>
  <rd:DataSourceID>{any-guid}</rd:DataSourceID>
  <rd:PowerBIWorkspaceName>{WorkspaceName}</rd:PowerBIWorkspaceName>
  <rd:PowerBIDatasetName>{DatasetName}</rd:PowerBIDatasetName>
</DataSource>
```

Replace:
- `{DATASET_GUID}` — the semantic model's **GUID** (from `GET /workspaces/{id}/semanticModels`).
- `{WorkspaceName}` / `{DatasetName}` — display names (informational metadata).
- `{any-guid}` — any stable GUID for `rd:DataSourceID`.

## Why not the simplified form?

The `Data Source=powerbi://api.powerbi.com/v1.0/myorg/<ws>;Initial Catalog=<name>` form (what some
docs show) was **rejected by the Fabric definition validator** (`InvalidDefinitionFormat`). The
`pbiazure` + `sobe_wowvirtualserver-<GUID>` form is what Fabric-validated reports use. When you
publish through the **Power BI Imports API into the same workspace as the model**, the binding is
resolved for you and the report picks up the workspace model.

## Field notes

| Element | Purpose |
|---|---|
| `DataProvider` = `PBIDATASET` | Selects the Power BI semantic model provider |
| `Identity Provider="..."` | AAD authority + Power BI resource + first-party app id (copy verbatim) |
| `Integrated Security=ClaimsToken` | Auth flows from the signed-in identity — **no** username/password |
| `rd:SecurityType` = `None` | Credentials are token-based, not stored |

## Auth & RLS

- No credentials in the connection string. The report runs under the caller's identity and **respects
  Row-Level Security (RLS)** defined in the model.
- Publishing/rendering requires the workspace to be on **Premium / Embedded / Fabric capacity**.
