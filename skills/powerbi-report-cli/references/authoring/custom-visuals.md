# Custom Visuals (AppSource, Organizational, Private `.pbiviz`)

Custom visuals extend Power BI beyond the built-in catalog, so
`powerbi-report-author catalog`/`formatting` cannot describe them and **each kind
is registered differently in `report.json`**. This reference covers the three
kinds, finding a visual's GUID, registering and binding each, and verifying the
result in Power BI Desktop.

> A `visualType` that is not backed by a matching registration renders as *"To
> see this custom visual, add it to this report first"* — or a generic empty
> placeholder — in Desktop, and `powerbi-report-author validate` flags it with a
> `PBIR_VISUAL_TYPE_UNKNOWN` **warning** (never an error). See
> [Desktop verification](#desktop-verification) for exactly when that warning is
> suppressed.

## Contents

- [Overview: The Three Kinds](#overview-the-three-kinds)
- [Finding the GUID](#finding-the-guid)
- [1. AppSource (public) visual](#1-appsource-public-visual)
- [2. Organizational (org store) visual](#2-organizational-org-store-visual)
- [3. Private (`.pbiviz`) visual](#3-private-pbiviz-visual)
- [Binding data to a custom visual](#binding-data-to-a-custom-visual)
- [Desktop verification](#desktop-verification)

## Overview: The Three Kinds

Power BI supports three kinds of custom visual. Registration is what differs —
pick the row that matches your visual:

| Kind | Also called | Package stored in report? | Registered in `report.json` via |
|------|-------------|---------------------------|---------------------------------|
| AppSource | Public / marketplace | No — Desktop downloads it | `publicCustomVisuals` (array of GUID strings) |
| Organizational | Org store | No — loaded from tenant store | `resourcePackages` (an `OrganizationalStoreCustomVisual` package, `_OrgStore` name). **Not** the root `organizationCustomVisuals` array — that is schema-valid but does **not** register the plugin for rendering. |
| Private | Imported `.pbiviz` file | **Yes** — unpacked into `CustomVisuals/` | `resourcePackages` (a `CustomVisual` package) |

For all three kinds, `visual.visualType` is set to the visual's **GUID** —
**except organizational visuals, whose `visualType` is the GUID plus the
`_OrgStore` suffix** and must exactly match the package `name`
(see [§2](#2-organizational-org-store-visual)). Data roles come from the visual's
own `capabilities.dataRoles` (see [Binding data](#binding-data-to-a-custom-visual)).

> Only **private** visuals ship their package inside the report. AppSource and
> organizational visuals are resolved at open time from the marketplace / tenant
> store, so you need only the GUID — the AppSource GUID, or the `_OrgStore`
> package name (which carries the org GUID). No bundled package bytes and no
> tenant blob `path` are required; Desktop resolves the org package by GUID.

## Finding the GUID

A `.pbiviz` file is a zip. Its `package.json` holds `visual.guid`,
`visual.name`, and `visual.displayName`:

```bash
# The GUID is the value you put in visual.visualType and in the registrations below
unzip -p MyVisual.pbiviz package.json   # → { "visual": { "guid": "<GUID>", ... } }
```

For AppSource visuals you can also read the GUID from the marketplace package.
GUIDs look like `Aquarium1442671919391` (AppSource) or
`CHARTICULATOR_VISUAL_CustomVisual1341858CCF82CD818D4B1826A3CBC4F3E` (a private
Charticulator export). **Organizational visuals are tenant-specific:** you author
only the GUID and its `_OrgStore`-suffixed package name. Leave the tenant blob
`path` empty — Desktop resolves it from the tenant store by GUID on reload. The
GUID is not inferable from local files and there is no name→GUID lookup — **the
user must provide the org GUID** (or you copy it from a Desktop-authored instance
of the same visual). See
[§2](#2-organizational-org-store-visual).

> **⚠️ Never author from a name-guessed GUID.** There is no name→GUID lookup in
> the tooling (`catalog` only covers built-in visuals). Mapping a friendly name
> like *"Aquarium"* to `Aquarium1442671919391` is unverified recall — by a human
> or an agent — and `validate` cannot catch a wrong GUID: an unregistered GUID is
> only a `PBIR_VISUAL_TYPE_UNKNOWN` warning, and a *registered but wrong* GUID
> validates clean yet renders empty or as the wrong visual in Desktop. Always
> confirm the GUID from an authoritative source before relying on it:
> - **the visual's `package.json`** inside its `.pbiviz` — download the visual
>   from AppSource, then `unzip -p MyVisual.pbiviz package.json` and read
>   `visual.guid` (the AppSource *listing page* does not show this GUID; its URL
>   carries an unrelated offer ID); or
> - **a Desktop-authored instance** — add the visual in Desktop, save, and copy
>   the `visualType` / `publicCustomVisuals` GUID it persists to `report.json`.

## 1. AppSource (public) visual

Add the GUID to `publicCustomVisuals` in `report.json`. Desktop downloads the
package on open.

```jsonc
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
  "themeCollection": { /* ... */ },
  "publicCustomVisuals": [
    "Aquarium1442671919391"
  ]
}
```

### AppSource licensing and freemium data caps

A *"The publisher of … requires a license"* wall in Desktop is **not** a PBIR
authoring error and is **not** something you can fix in the files:

- The license entitlement is an **AppSource account/tenant** property, not stored
  in the report. `publicCustomVisuals` + a matching `visualType` is the complete
  and correct authoring; nothing more can be added to the PBIR to grant a license.
- **Freemium visuals show the license wall when the bound data exceeds their free
  tier.** Several free/certified visuals (e.g. Enlighten Aquarium) render on the
  free tier only up to a **data-point cap**; binding high-cardinality fields (a
  large `Category`, an extra `Legend` that multiplies points, or many measures)
  pushes past the cap and triggers the wall — while the *same* visual with a small
  low-cardinality binding renders fine. If an AppSource visual shows the license
  wall, first **reduce data volume** (fewer categories, drop the `Legend`, fewer
  measures) before assuming it is a paid visual.

  > **Bind freemium custom visuals conservatively by default.** Choose a
  > **low-cardinality `Category` (≤ ~30 distinct values)** — e.g. a division,
  > region, or type column — **never a high-cardinality name/ID column** like
  > `Account_Name`, a customer name, or a date at day grain. Prefer **no `Legend`**
  > (it multiplies data points) and **a single measure**. Add richness only after
  > confirming the visual still renders. This is the single most common cause of a
  > custom visual "requiring a license" — it is a data-volume symptom, not a
  > licensing or registration bug.
- The registration and `visualType` are byte-for-byte identical whether or not
  the wall appears — so do not "fix" the license wall by editing the registration.

## 2. Organizational (org store) visual

Org-store visuals are the most error-prone kind. **Two rules decide whether they
render:**

1. **Register with a `resourcePackages` package of type
   `OrganizationalStoreCustomVisual`** — *not* the root `organizationCustomVisuals`
   array. The `organizationCustomVisuals: [{ name, path }]` form is part of the
   PBIR schema and `validate` accepts it, but Desktop does **not** register the
   plugin from it, so the visual renders as an empty/grey placeholder. This is the
   single most common org-visual authoring mistake.
2. **Use the `_OrgStore` suffix everywhere.** The package `name` **and** the
   container `visual.visualType` must both be `<GUID>_OrgStore`. A bare `<GUID>`
   `visualType` (without the suffix) renders the generic empty placeholder even
   when the package is present.

```jsonc
// report.json
{
  "resourcePackages": [
    { "name": "SharedResources", "type": "SharedResources", "items": [ /* base theme ... */ ] },
    {
      "name": "<GUID>_OrgStore",
      "type": "OrganizationalStoreCustomVisual",
      "items": [
        {
          "name": "resources/<GUID>_OrgStore.pbiviz.json",
          "path": "",
          "type": "CustomVisualMetadata"
        }
      ]
    }
  ]
}
```

```jsonc
// the visual container (visual.json) on the page
{ "visual": { "visualType": "<GUID>_OrgStore" } }
```

- **`name`** — `<GUID>_OrgStore`, matching the container `visualType` exactly.
- **item `path`** — leave it empty (`""`). The user provides only the GUID;
  Desktop resolves the tenant blob path from the GUID on reload.
- **No local files are required.** You do **not** need a `CustomVisuals/<GUID>_OrgStore/`
  folder or a `.rp` file — Desktop resolves the package from the tenant store at
  load time. Registration + a matching container is enough to render.
- **Do not also add** the same visual to the root `organizationCustomVisuals`
  array; keep only the `resourcePackages` entry.
- **`validate` suppresses `PBIR_VISUAL_TYPE_UNKNOWN`** for this visual only when
  the container `visualType` exactly matches the `_OrgStore` package `name`. A
  bare `<GUID>`, a root-`organizationCustomVisuals`-only registration, or no
  registration keeps warning — treat that warning as *"won't render."*

## 3. Private (`.pbiviz`) visual

A private visual needs **both** of the following. The `CustomVisuals/` folder
alone is *not* enough — without the `resourcePackages` entry the visual renders
as *"add it to this report first"*.

### Part A — unpack the `.pbiviz` into `CustomVisuals/<GUID>/`

The on-disk layout mirrors the unzipped `.pbiviz`:

```text
<Report>.Report/
└── CustomVisuals/
    └── <GUID>/
        ├── package.json                       # from the .pbiviz (visual.guid, resources map)
        └── resources/
            └── <GUID>.pbiviz.json             # the bundled visual payload
```

### Part B — register it in `report.json` → `resourcePackages`

Append a package with `type: "CustomVisual"` whose single item is the
`.pbiviz.json` metadata file (do **not** add private visuals to
`publicCustomVisuals`):

```jsonc
{
  "resourcePackages": [
    { "name": "SharedResources", "type": "SharedResources", "items": [ /* base theme ... */ ] },
    {
      "name": "<GUID>",
      "type": "CustomVisual",
      "items": [
        {
          "name": "<GUID>.pbiviz.json",
          "path": "<GUID>.pbiviz.json",
          "type": "CustomVisualMetadata"
        }
      ]
    }
  ]
}
```

The item `path` is the bare `<GUID>.pbiviz.json` filename (resolved against the
package's `CustomVisuals/<GUID>/resources/` folder), not a `resources/…` path.

## Binding data to a custom visual

Custom visuals define their own roles in `capabilities.dataRoles` inside the
`.pbiviz`'s `<GUID>.pbiviz.json` (nested under `resources/`). Read that file to
get the role **`name`** (used as the `queryState` key) and `kind`
(`Grouping` → bind a `Column`; `Measure` → bind a `Measure`). Honor the
`dataViewMappings.conditions` (min/max per role). Example role lookup:

```bash
# roles live at capabilities.dataRoles in the nested resource, not package.json
unzip -p MyVisual.pbiviz "resources/*.pbiviz.json" | jq '.capabilities.dataRoles'
```

Then build `visual.query.queryState` keyed by each role `name`, exactly like a
built-in visual (see `authoring-workflows.md` (see `authoring-workflows.md`) and
expressions.md § Visual Query Projection (see `expressions.md`, section `visual-query-projection`)
for the authoritative projection shape). A custom visual with no bound fields is
valid but renders empty.

> **⚠️ `queryRef` and `nativeQueryRef` are siblings of `field`**, not properties
> inside it. Nesting them inside `field` fails the container schema and the
> visual silently does not render. `powerbi-report-author validate` may not
> catch this when the online schema is unreachable (`PBIR_SCHEMA_UNREACHABLE`);
> Desktop enforces it on load.
>
> ```json
> "projections": [
>   {
>     "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "Metrics" } }, "Property": "Revenue" } },
>     "queryRef": "Metrics.Revenue",
>     "nativeQueryRef": "Revenue"
>   }
> ]
> ```

## Desktop verification

- After adding the registration and (for private visuals) the `CustomVisuals/`
  package, `powerbi-desktop reload` picks up the visual — a full close/reopen is
  **not** required, including for a brand-new custom visual added to an
  already-open report. If a private visual still shows *"add it to this report
  first"* after reload, the missing piece is almost always the
  `resourcePackages` entry (Part B), not the reload mechanism.
- **Org visuals load lazily from the tenant store.** The first reload/screenshot
  can come back blank while the tenant blob is still resolving. Wait ~15–20s and,
  if still blank, **reload a second time** before concluding it is broken.
- `PBIR_VISUAL_TYPE_UNKNOWN` fires for **any** `visualType` the CLI does not
  recognize — a mistyped built-in visual, or a custom visual that is unregistered
  or registered only in a non-rendering way. For a custom visual, clear it by
  adding the matching **rendering** registration: `publicCustomVisuals`
  (AppSource), a `CustomVisual` `resourcePackages` package (private), or an
  `OrganizationalStoreCustomVisual` `_OrgStore` package (organizational) — the
  root `organizationCustomVisuals` array does **not** suppress the warning because
  it does not render. Also re-check the GUID/type for typos. Suppression is
  registration-only: it proves the entry exists, not that the visual resolves —
  always verify org visuals by rendering in Desktop, since `validate` cannot reach
  the tenant store.

> **⚠️ Custom-visual clobber symptom.** If a correct
> `OrganizationalStoreCustomVisual` package reverts to the non-rendering
> `organizationCustomVisuals` array, or `publicCustomVisuals` entries vanish after
> a reload, Desktop's unsaved in-memory model overwrote your disk edits on
> save/reload. Follow the general rule in `SKILL.md` (the Desktop reload workflow):
> only edit `report.json` when `powerbi-desktop status` reports
> `hasUnsavedChanges: false`, otherwise have the user save or close/reopen first.
