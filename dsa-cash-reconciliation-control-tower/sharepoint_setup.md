# SharePoint setup

## September 2026 pilot: local synchronized folder

The active pilot does not call Microsoft Graph. Sign in to the organization’s
approved SharePoint/OneDrive sync client using your normal organization
process, allow the approved library to synchronize, and set
`LOCAL_SHAREPOINT_ROOT` in `.env` or paste the synchronized folder into the
app sidebar. The app recursively reads workbook metadata from that folder and
does not modify, rename, move, or save over source files.

The pilot selects only `.xlsx` files whose names start with these exact
prefixes:

- `SnapPay AR Transaction`
- `BMO BLUEPAY`
- `BLUEPAY Fiserv Bankcard`
- `RC BLUEPAY GENERAL`
- `G.L. 1.1070`

It reports filename-derived source group suggestions. The user can change each
suggestion in Configuration Validation. Header/column mapping is never
inferred. Filename selection does not prove the transaction data is from
September 2026; period membership must be independently verified after the
column/date mappings are approved. The pilot profile page does not reconcile.

No Graph token, Entra app registration, site ID, drive ID, or Graph permission
is required for this local pilot.

## Optional future Graph integration

The repository deliberately does not invent tenant IDs, application IDs,
SharePoint site IDs, library/drive IDs, URLs, or credentials. Ask the
Microsoft 365/Entra administrator to provide:

- Tenant ID (`MS_TENANT_ID`)
- Public-client application ID (`MS_CLIENT_ID`)
- Exact SharePoint site identifier (`SHAREPOINT_SITE_ID`)
- Document library/drive identifier (`SHAREPOINT_DRIVE_ID`)
- Root folder path (`SHAREPOINT_ROOT_FOLDER`)

For a future Graph mode only, copy `.env.example` to `.env` and populate those
values. The optional Graph client uses interactive delegated authentication
and `Sites.Selected` read access granted for the specific site. The active
pilot does not invoke this client.

## Local source-profile behavior

The profile scanner traverses the configured local root, selects matching
workbooks by filename, and opens them with a read-only workbook reader. It
records path, name, byte size, filename-derived source group, worksheet names,
row counts below row 1, first-row headers, and profile errors. It does not
write extracted rows to disk. The downloadable profile report is created in
memory and contains source files, worksheets, headers, and missing required
fields. A reviewer must explicitly save/approve the mapping; mapping and
approval metadata are stored under ignored local `data/`.

## Future Graph safeguards

The optional Graph client only sends `GET` requests. It recursively lists
folders, supports `.xlsx`, `.xlsm`, and `.csv`, and captures file metadata and
SHA-256. A later Graph pilot must review folder scoping, file-period selection,
delta-token recovery, and duplicate handling before enabling its user-facing
mode. See [driveItem: delta](https://learn.microsoft.com/graph/api/driveitem-delta?view=graph-rest-1.0)
and [Selected permissions overview](https://learn.microsoft.com/graph/permissions-selected-overview).
