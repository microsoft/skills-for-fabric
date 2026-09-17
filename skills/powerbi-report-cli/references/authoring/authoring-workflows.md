# Authoring Workflows & Examples

Read this for concrete PBIR authoring workflows: pages, visuals, layout
templates, themes, drillthrough, interactions, and visual-type routing.

Related references:

- [formatting.md](formatting.md) — value encoding, colors, selectors, VCOs, and formatting properties.
- [expressions.md](expressions.md) — field expressions, filters, and sort definitions.

> **Before editing existing reports:** inventory the report with
> `powerbi-report-author preview-pages <path-to-.Report-dir>` and
> `powerbi-report-author preview-visuals <path-to-.Report-dir>`.
> Add `--with-derived` when you need counts or cheap computed flags.
>
> **Examples are structural patterns.** Property names may vary by visual type.
> Always confirm exact properties with
> `powerbi-report-author formatting describe-object <type> <object>` before
> applying formatting.

## Contents

- [Names & Format Versions](#names--format-versions)
- [Add a New Page](#add-a-new-page)
- [Add a Visual to a Page](#add-a-visual-to-a-page)
- [Common Layout Templates](#common-layout-templates)
- [Change Theme](#change-theme)
- [Visual Type References](#visual-type-references)
- [Drillthrough Page](#drillthrough-page)
- [Visual Interactions](#visual-interactions)

## Names & Format Versions

### ID Generation

| Element | Format | Scope |
|---|---|---|
| Visual `name` | 20 lowercase hex chars (e.g. `f4214b297bb2c1e49dfe`) | Unique within a page |
| Page `name` | Modern: bare 20 hex chars. Traditional: `ReportSection` + 24 hex chars. The first page may be just `ReportSection` (no suffix). | Unique across the report |
| Filter `name` | `Filter` + 24 lowercase hex chars (e.g. `Filter1a2b3c4d5e6f7890a1b2c3d4`) | Unique across the entire report definition — `powerbi-report-author validate` flags duplicates with `PBIR_FILTER_NAME_DUPLICATE_*` |

```javascript
// Node.js
const crypto = require('crypto');
const visualId = crypto.randomBytes(10).toString('hex');                  // 20 hex chars
const pageId   = 'ReportSection' + crypto.randomBytes(12).toString('hex'); // ReportSection + 24 hex
const filterId = 'Filter'        + crypto.randomBytes(12).toString('hex'); // Filter + 24 hex
```

### Format Versions

These are file-content versions (not `$schema` URLs) and are constants for the
current PBIR format:

- `version.json` → `"version": "2.0.0"`
- `definition.pbir` → `"version": "4.0"`

For `$schema` URL versioning rules and the file layout, see
[authoring.md § PBIR File Layout](../authoring.md#pbir-file-layout). When creating a
new file of any type, copy the `$schema` URL from an existing file of the same
type in the same report.

## Add a New Page

1. Generate a unique page name (e.g. `ReportSection` + 24 hex chars)
2. Create the directory: `definition/pages/<pageName>/`
3. Create `page.json`:
   ```json
   {
     "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
     "name": "<pageName>",
     "displayName": "My New Page",
     "displayOption": "FitToPage",
     "height": 720,
     "width": 1280
   }
   ```
4. Create `visuals/` subdirectory (can be empty initially)
5. Add the page name to `pages.json` → `pageOrder` array at the desired position

**Note**: For the `$schema` URL, copy from an existing `page.json` in the same report.

## Add a Visual to a Page

1. Generate a unique visual name (20 hex chars)
2. Create `definition/pages/<pageName>/visuals/<visualName>/visual.json`
3. Populate with the visual definition:
   ```json
   {
     "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
     "name": "<visualName>",
     "position": {
       "x": 0, "y": 0, "z": 1000,
       "height": 300, "width": 400,
       "tabOrder": 1000
     },
     "visual": {
       "visualType": "<type>",
       "query": {
         "queryState": {
           "<RoleName>": {
             "projections": [
               {
                 "field": { /* expression — see references/authoring/expressions.md */ },
                 "queryRef": "<Entity>.<Property>",
                 "nativeQueryRef": "<Property>"
               }
             ]
           }
         }
       }
     }
   }
   ```

**⚠️ All role projections (Rows, Columns, Values, etc.) must be inside `queryState`, not directly under `query`.** Placing them under `query` causes a schema validation error.

**Position guidelines** (1280×720 canvas):
- `z`: Stacking order. Higher = on top. Increment by 1000 for each visual.
- `tabOrder`: Keyboard navigation order. Usually matches `z`.
- Keep visuals within canvas bounds: `x + width ≤ 1280`, `y + height ≤ 720`.

## Common Layout Templates

**Full-width KPI row + detail chart:**
```text
KPI Card 1:  x=20,  y=20,  w=290, h=120
KPI Card 2:  x=330, y=20,  w=290, h=120
KPI Card 3:  x=640, y=20,  w=290, h=120
KPI Card 4:  x=950, y=20,  w=290, h=120
Main Chart:  x=20,  y=160, w=1240, h=540
```
**2×2 Grid:**
```text
Top-Left:     x=20,  y=20,  w=610, h=340
Top-Right:    x=650, y=20,  w=610, h=340
Bottom-Left:  x=20,  y=380, w=610, h=320
Bottom-Right: x=650, y=380, w=610, h=320
```

**Header + sidebar + main:**
```text
Header:   x=0,   y=0,   w=1280, h=80
Sidebar:  x=0,   y=80,  w=280,  h=640
Main:     x=300, y=80,  w=960,  h=640
```

## Change Theme

In `report.json`, update the `themeCollection.customTheme`:
```json
{
  "customTheme": {
    "name": "<CustomThemeName>-<guid>.json",
    "reportVersionAtImport": {
      "visual": "2.6.0",
      "report": "3.1.0",
      "page": "2.3.0"
    },
    "type": "RegisteredResources"
  }
}
```
Also ensure the theme file exists in `StaticResources/RegisteredResources/`
and is listed in the `resourcePackages` array with matching `name` and `path`.

On every theme edit, follow the [GUID cache-busting procedure in theming.md](theming.md#theme-name-guid-convention-cache-busting)
— rotate the GUID suffix (keep `<CustomThemeName>` stable), update all
`report.json` references, and reload Desktop. Only change `<CustomThemeName>`
if the user explicitly requests a rename.

> ⚠️ **`type` must be `"RegisteredResources"`** — not `"SharedResources"`.
> Using the wrong type causes the theme to silently fail.
>
> Inside `report.json`, both `customTheme.name` and the matching
> `resourcePackages[].items[].name` MUST include the `.json` extension and
> equal the item's `path` (e.g., all three are `"<ThemeName>.json"`). Using
> the bare theme name causes the published report to incorrectly apply the theme
> on Power BI service. The `name` field **inside the theme JSON file itself**
> stays as the bare theme name (no `.json` suffix). See `theming.md` for
> details.

## Visual Type References

Use these focused references for visual-specific templates, formatting rules,
and known rendering pitfalls.

| Intent | Read |
|---|---|
| Bar, column, and line charts | [cartesian.md](cartesian.md) |
| Cards and KPI callouts | [card.md](card.md) |
| Tables and matrices | [table.md](table.md) |
| Slicers and slicer selections | [slicers.md](slicers.md) |
| Image visuals | [image.md](image.md) |
| Shapes, dividers, and containers | [shape.md](shape.md) |
| Maps | [map.md](map.md) |
| Static or dynamic textboxes | [textbox.md](textbox.md) |

## Drillthrough Page
A drillthrough page adds `pageBinding` and drillthrough filters to `page.json`:
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
  "name": "<pageName>",
  "displayName": "Detail Drillthrough",
  "displayOption": "FitToPage",
  "height": 720,
  "width": 1280,
  "filterConfig": {
    "filters": [
      {
        "name": "Filter<24hex>",
        "field": {
          "Column": {
            "Expression": { "SourceRef": { "Entity": "<Table>" } },
            "Property": "<DrillthroughColumn>"
          }
        },
        "type": "Categorical",
        "howCreated": "Drillthrough"
      }
    ]
  },
  "pageBinding": {
    "name": "Pod",
    "type": "Drillthrough",
    "parameters": [
      {
        "name": "Param_Filter<24hex>",
        "boundFilter": "Filter<24hex>",
        "fieldExpr": {
          "Column": {
            "Expression": { "SourceRef": { "Entity": "<Table>" } },
            "Property": "<DrillthroughColumn>"
          }
        }
      }
    ]
  }
}
```
**Key points**:
- Each drillthrough field needs both a filter entry (with `"howCreated": "Drillthrough"`)
  and a matching `pageBinding.parameters` entry with `boundFilter` referencing the filter name.
- The `pageBinding.name` is typically `"Pod"`.
- `pageBinding.type` is `"Drillthrough"` (or `"Tooltip"` for tooltip pages).

## Visual Interactions
Control how visuals cross-filter/highlight each other on a page.
Add `visualInteractions` array to `page.json`:
```json
{
  "visualInteractions": [
    {
      "source": "<sourceVisualName>",
      "target": "<targetVisualName>",
      "type": "NoFilter"
    }
  ]
}
```
| Type | Effect |
|------|--------|
| `"NoFilter"` | Source visual does NOT filter target |
| `"DataFilter"` | Source cross-filters target (shows subset) |
| `"HighlightFilter"` | Source highlights matching data in target |

By default (no entry), visuals cross-filter each other. Only add entries to
**override** the default behavior.
