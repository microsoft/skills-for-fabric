# Troubleshooting

Symptom → cause → fix for the issues encountered building a semantic-model-bound paginated report.

| Symptom | Cause | Fix |
|---|---|---|
| `400 InvalidDefinitionFormat` (`isRetriable:false`) from Fabric `POST /paginatedReports` | The Fabric definition API strictly validates RDL structure/namespaces and rejects most hand-authored RDLs. | Publish with the **Power BI Imports API** (multipart raw `.rdl`) instead — see [publishing.md](./publishing.md). It validates and renders. |
| Report renders but **columns are blank** (no error) | `<DataField>` doesn't match the DAX result column name (missing brackets / table qualification). | Bracket named columns (`[ClaimID]`), table-qualify grouping columns (`Product[Category]`). See [datasets-dax.md](./datasets-dax.md). |
| `401 Unauthorized` on import | Wrong token audience. | Use `--resource https://analysis.windows.net/powerbi/api` for the Imports API; `https://api.fabric.microsoft.com` for the Fabric API. |
| `404` when publishing first version | `nameConflict=Overwrite` used but the report doesn't exist yet. | Use `nameConflict=Abort` to create; only use `Overwrite` when the report already exists. |
| Import stuck / `Failed` with capacity error | Workspace not on Premium/Embedded/Fabric capacity. | Assign the workspace to a capacity that supports paginated reports. |
| `400` XML parse error building the RDL | Unescaped `&`, `<`, `>`, `"` in expressions/labels. | Escape centrally in the textbox helper; validate with `xml.dom.minidom.parseString()` before upload. |
| Report opens but data source fails to connect | Wrong connection string form (e.g. simplified `powerbi://…/myorg`). | Use the full `PBIDATASET` / `pbiazure://` connection string with the `rd:` security elements. See [datasource-connection.md](./datasource-connection.md). |
| Date parameter won't range-filter | Date column is stored as **Text** in the model. | `DATEVALUE(...)` in the DAX query, or filter as text. Only `Claim Date` is a true Date in autoclaims_sm. |
| Multi-value parameter returns nothing | `TREATAS({ @Param }, …)` mis-expands, or `<MultiValue>` not set. | Prefer RDL-layer `<Filter>` with `Operator=In`; ensure `<MultiValue>true</MultiValue>`. See [parameters-filters.md](./parameters-filters.md). |
| Subtotal/grand-total row missing or duplicated | `TablixRowHierarchy` leaf members don't match the body row count. | Match exactly 5 leaf members ↔ 5 body rows (header, group header, detail, group footer, grand total). See [layout.md](./layout.md). |
| `df` namespace / `MustUnderstand` errors | RDL 2016 skeleton incomplete. | Include `MustUnderstand="df"`, the `df` namespace, `<df:DefaultFontFamily>`, and put `rd:ReportUnitType`/`rd:ReportID` first. See [rdl-structure.md](./rdl-structure.md). |

## Debugging workflow

1. **Validate XML locally first** — `python -c "import xml.dom.minidom,sys; xml.dom.minidom.parse(sys.argv[1])" page_test.rdl`.
2. **Publish via Imports API** and **read the `error` object** on a `Failed` import — it names the offending element.
3. **Open and run** the report; if it renders empty, suspect `<DataField>` bracketing before anything else.
4. Iterate on one change at a time (data source → datasets → parameters → layout).
