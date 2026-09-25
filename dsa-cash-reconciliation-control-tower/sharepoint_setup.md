# SharePoint and Microsoft Graph setup

## Values supplied by your administrator

The repository deliberately does not invent tenant IDs, application IDs,
SharePoint site IDs, library/drive IDs, URLs, or credentials. Ask the
Microsoft 365/Entra administrator to provide:

- Tenant ID (`MS_TENANT_ID`)
- Public-client application ID (`MS_CLIENT_ID`)
- Exact SharePoint site identifier (`SHAREPOINT_SITE_ID`)
- Document library/drive identifier (`SHAREPOINT_DRIVE_ID`)
- Root folder path (`SHAREPOINT_ROOT_FOLDER`), usually the controlled raw
  landing folder

Copy `.env.example` to `.env`, set these values, and keep `.env` local. The
Graph connector requires all five values; it fails explicitly if any are
missing. `config/column_mappings.yaml` maps each source name to a path relative
to the configured root. The expected landing-zone folders are:

```text
01 Raw/
  SnapPay/
  BluePay/
  BMO/
  JDE/
  Adjustments/
02 Configuration/
03 Output/
```

Adjust the root and relative source-folder mappings to the actual library
layout. Only source mappings in SnapPay, BluePay, BMO, and JDE are downloaded
as reconciliation inputs. Adjustments, Configuration, and Output are not
treated as transaction sources.

## App registration and permission

1. Register a **public client** application for the local prototype and enable
   the interactive redirect URI `http://localhost` as required by MSAL
   Python's `acquire_token_interactive`.
2. Add the delegated Microsoft Graph `Sites.Selected` permission and obtain
   administrator consent.
3. Have an authorized SharePoint administrator grant this application the
   **read** role on only the intended site. `Sites.Selected` does not grant
   site access by itself; the per-site grant is a separate administrative
   step. Do not grant write permissions.
4. Verify that the signed-in reviewer can also read the controlled library and
   source folders.

Microsoft describes selected permissions as a way to scope access to selected
SharePoint/OneDrive resources: [Selected permissions overview](https://learn.microsoft.com/graph/permissions-selected-overview).
Interactive public-client authentication uses MSAL's interactive token
acquisition and PKCE; see [MSAL Python acquire tokens](https://learn.microsoft.com/entra/msal/python/getting-started/acquiring-tokens#interactive).

## Read-only behavior and filtering

The Graph client only sends `GET` requests. It recursively lists folders,
ignores unapproved extensions, downloads `.xlsx`, `.xlsm`, and `.csv` bytes,
and captures file ID, name, size, modified/created timestamps, eTag, parent
path, download URL, and SHA-256. No SharePoint metadata or file content is
written back. Local downloads are under ignored `data/raw/<source>/<hash>/`.
The same content hash cannot be processed twice in one run/reporting period;
the run is aborted if a duplicate is mixed with new files, avoiding a partial
success. A previously used source file can be processed for another reporting
period.

The Graph list operation can prefilter by SharePoint `lastModifiedDateTime`
for a requested period; this is only a file-level intake optimization. The
reconciliation engine applies the authoritative period filter to each parsed
row's transaction/posting date. Files whose modified timestamp is outside the
period can contain in-period transactions; adjust the intake policy if this
pre-filter would exclude such files.

## Delta-token extension

`GraphSharePointClient.read_delta(repository)` starts with the drive root delta
endpoint, follows every Graph `@odata.nextLink`, and persists the returned
`@odata.deltaLink` in SQLite application state for future runs. It returns
metadata changes only; it is an architecture hook, not a scheduled sync
service. A production delta consumer must scope returned items to the
configured root, handle deleted/renamed items, handle expired delta tokens by
reinitializing, and apply the same approved-extension/hash gates. See
[driveItem: delta](https://learn.microsoft.com/graph/api/driveitem-delta?view=graph-rest-1.0).

## Operational safeguards

- Tokens remain in process memory; no serialized token cache is written.
- The Graph permission is read-only; the client has no upload/edit/delete code.
- Never paste financial workbook contents into an AI service or source-control
  issue.
- Use a dedicated, access-controlled workstation and protected disk for
  runtime financial data.
- Revoke the site grant and app consent when the prototype is no longer needed.
