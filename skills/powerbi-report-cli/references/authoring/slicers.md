# Slicer Authoring Guide

> **Always read first** when adding/modifying slicers or slicer selections.
> For expression reference, see **references/authoring/expressions.md**

Slicers provide interactive filtering. This guide covers creation,
formatting defaults, and selection configuration for all slicer types.

- [Slicer Authoring Guide](#slicer-authoring-guide)
  - [Recommended Defaults](#recommended-defaults)
    - [Slicer Template](#slicer-template)
    - [Sizing](#sizing)
    - [Fill variant](#fill-variant)
    - [Date Between Slicer Template](#date-between-slicer-template)
  - [Add/Modify a Slicer](#addmodify-a-slicer)
    - [Slicer types](#slicer-types)
    - [Setting slicer selections](#setting-slicer-selections)
  - [Slicer Sync Groups](#slicer-sync-groups)
  - [Theme Approach](#theme-approach)
  - [Discovering Properties](#discovering-properties)

<a id="per-visual-vco-override-caveat"></a>
> ⚠️ **Per-visual VCO override caveat**: As soon as a slicer declares **any**
> `visualContainerObjects` entry (background, border, title, visualHeader,
> etc.), Power BI stops inheriting the theme's `*.*.padding` cascade for that
> visual and resets its inner padding to **0**. The chrome (header label +
> dropdown box) then sits flush against the visual border — no breathing
> room — and the bottom row of an inline slicer can visibly clip even though
> the height formula said it would fit.
>
> **Fix**: every slicer that sets *any* per-visual VCO must also **declare a
> `padding` VCO explicitly** — the bug is *omitting* `padding`, not the value
> itself. Use the theme's `8/8/8/8` for normal slicers, or `0/0/0/0` for the
> [fill variant](#fill-variant) (where the white background must reach the
> container edges). Recompute `h` via the [Sizing](#sizing) formula whenever
> the value changes. The base template below already includes `padding` — keep
> it even if you remove other VCOs.

---

## Recommended Defaults

Three slicer visual types exist in PBIR, each with different query roles
and capabilities:

- `slicer` — supports `data.mode` (Dropdown, Basic, Between, Single, etc.)
- `listSlicer` — scrollable list with tooltips and hierarchy support
- `advancedSlicerVisual` — tile/button layout, single field only

Before changing a slicer's `data.mode`, `position.height`, font size, padding,
background/border VCO, or theme chrome, re-run the sizing rules in this file.
Do not fix clipping by shrinking to `h=48` or 8pt text; resize the slicer and
its reserved band/rail instead.

### Slicer Template

All slicer types share this base structure. Adapt `visualType`, query
roles, and `data.mode` per type (see [Slicer types](#slicer-types) below).

> **`height` value below**: derived from `60 + top_padding + bottom_padding`
> snapped to 8px (see [Sizing](#sizing)). The `80` shown matches the skill's
> default theme padding (`*.*.padding = 8/8`). If your theme uses zero
> padding, drop to `64`; if it uses `10/10` (common in dark/card forks),
> keep `80` (still fits, since 60+20=80 lands on the grid).

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<unique-id>",
  "position": { "x": 24, "y": 72, "z": 1000, "height": 80, "width": 160, "tabOrder": 1000 },
  "visual": {
    "visualType": "slicer",
    "query": {
      "queryState": {
        "Values": {
          "projections": [{
            "field": { "Column": { "Expression": { "SourceRef": { "Entity": "<table>" } }, "Property": "<column>" } },
            "queryRef": "<table>.<column>",
            "nativeQueryRef": "<column>"
          }]
        }
      }
    },
    "objects": {
      "data": [{ "properties": { "mode": { "expr": { "Literal": { "Value": "'Dropdown'" } } } } }],
      "header": [{ "properties": {
        "show": { "expr": { "Literal": { "Value": "true" } } },
        "text": { "expr": { "Literal": { "Value": "'<Display Name>'" } } }
      }}]
    },
    "visualContainerObjects": {
      "padding": [{ "properties": {
        "top":    { "expr": { "Literal": { "Value": "8D" } } },
        "bottom": { "expr": { "Literal": { "Value": "8D" } } },
        "left":   { "expr": { "Literal": { "Value": "8D" } } },
        "right":  { "expr": { "Literal": { "Value": "8D" } } }
      }}]
    }
  }
}
```

> **Why `padding` is in the template even though no other VCOs are set yet**:
> the moment you add **any** VCO (background, border, title.show=false,
> visualHeader.show=false, etc.) Power BI drops the theme `*.*.padding`
> cascade for that visual and zeros it. Keeping `padding` always-on makes
> the template safe to extend without re-introducing the bug. If your theme
> uses a different default (e.g. `10/10/10/10` in dark forks), match that
> value here and resize `h` per the formula in [Sizing](#sizing).

Rules applied to ListSlicer (default for **list slicer** requests):
1. visualType is listSlicer.
2. ONLY "Values" and "Tooltips" allowed under queryState. "Values" only allow Column or Hierarchy Expressions. "Tooltips" only allow Measure or Aggregation Expressions.

Rules applied to ButtonSlicer (default for **tile slicer** requests):
1. visualType is advancedSlicerVisual.
2. "Values" only allow one field with Column Expression. "Label" only allow one field with Measure or Aggregation Expression. "Tooltips" can have multiple fields with Aggregation Expressions.

Rules applied to Slicer (classic — default for **all other slicer** requests):
1. visualType is slicer. To make it a list slicer, set the Value inside of the mode as 'Basic'. To make it a dropdown slicer, set it to 'Dropdown'.
2. ONLY "Values" allowed under queryState and "Values" only allow Column/Hierarchy Expressions.
3. "data" under "objects" only available for slicer.

General rules applied to all slicers:
1. Only slicer with Basic/Dropdown mode and listSlicer can be hierarchy slicers.
2. The filter property under general in objects describes value selections.
3. The expansionStates only available for hierarchy slicers and only needed when the slicer is expanded.
4. identityKeys only defined on the first level of the hierarchy (the level whose nodes can be expanded to reveal children). Not defined on leaf levels.  identityValues defined inside root.children[] only when a specific node has been toggled open (expanded)
5. Adding a field to the `Tooltips` queryState role is **necessary but not sufficient** to show tooltips. You must **also** set `visualContainerObjects.visualTooltip.show = true` — the tooltip panel is off by default and the user will see nothing on hover without it:
   ```json
   "visualContainerObjects": {
     "visualTooltip": [
       { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } }
     ]
   }
   ```

With the theme applied, this template is complete for the **light variant**
(border from theme, no fill). The theme handles header font, items font,
border, and visual header.

> **Check `header.text`** — if the field name from the model is already
> human-readable (e.g., "Weight Class"), no override needed. If it's raw
> like "weight_class_name", set `header.text` to a clean display name.

### Sizing

Slicer height depends on the selected `data.mode` (or the visual type for
`listSlicer` / `advancedSlicerVisual`). The wrong height is the most common
cause of clipped items at the bottom of the visual — Power BI does **not**
auto-grow the container and refuses to render partial rows, so the last
item silently disappears when the math is off.

**Width** (mode-independent): 160px standard, 120px for short labels
(Year, Stance), 216px for `'Between'` date pickers (side-by-side dates).

> **No height/font shortcuts**: if a slicer collides with the next row or clips
> on a dark/fill theme, increase the reserved band/rail and recompute `h`.
> Do not lower header/items/date text below 9pt or force `h=48` to make the
> layout fit.

**Height by mode:**

| Mode / `visualType` | Height | Notes |
|---|---|---|
| `slicer` mode `'Dropdown'` | **`h = 60 + top_padding + bottom_padding`**, snap up to the next 8px. Worked values: zero padding → **h=64**; theme default `8/8` → **h=80**; dark-card `10/10` → **h=80**. The 60px chrome = `header (~28px at 10pt Semibold) + dropdown selector field (~32px)`. | Items render in a popup, not inline, so item count doesn't affect height. The padding stays *outside* the visible chrome — every padding pixel must be added to `h`. **Verify the layout below the slicer leaves room for the new height** (e.g. if a fork bumps padding from 8 to 10, recompute and shift the next-row visuals). |
| `slicer` mode `'Between'` / `'Before'` / `'After'` | **`h = 60 + top + bottom`** side-by-side (same chrome as Dropdown — two date pickers fit on one row). Stacked vertical = **`h = 84 + top + bottom`** (two date pickers on two rows). | See [Date Between Slicer Template](#date-between-slicer-template). |
| `slicer` mode `'Basic'` / `'Single'` | **Use the formula below** | Items render inline; height must cover header + search box + every visible row. |
| `listSlicer` | **Use the formula below** | Same inline-list behavior as Basic mode. Scrolls when items exceed available area, but the bottom row still clips if height < `chrome + 1 row`. |
| `advancedSlicerVisual` | **≥ 56px per tile row** (add padding the same way) | ≤10 tiles; size by number of tile rows × tile height. |

**Inline-list height formula** (Basic / Single / `listSlicer`):

```text
height = top_padding + bottom_padding
       + header_height          (≈ 32px when header.show = true; 0 when hidden)
       + search_box_height      (≈ 32px when items > ~10; 0 otherwise)
       + (visible_items × row_height)
       + 8                      (safety margin — PBI rounds row heights and
                                  hides any partial row at the bottom)
```

Defaults you can plug in:

| Term | Default value |
|---|---|
| `top_padding` + `bottom_padding` | **20px** total when VCO padding is 10/10 (the value used by most fill/dark themes); **16px** when VCO padding is left at the theme's `*` default of 8/8. |
| `header_height` | **32px** at `header.textSize = 10pt` (the skill default). Add 4px per +1pt above 10pt. |
| `row_height` | **24px** at `items.textSize = 9pt` with `items.padding = 2`. Add 4px per +1pt of items text size, and add `2 × items.padding` per row for any padding above 2. |
| `search_box_height` | **32px** when shown. Set `searchBox.show = false` to recover this space if the slicer has few items. |

> **Worked example:** any 5-item slicer with skill defaults (`header` 10pt,
> `items` 9pt, `padding` 2), VCO padding 10/10, header visible, search box
> visible →
> `20 + 32 + 32 + (5 × 24) + 8` = **212px**. Round up to the 8px grid → **216px**.
> The same slicer at h=56 (the chrome-only Dropdown minimum, before
> padding) **will clip every item but the first**.

> ⚠️ **VCO padding eats item area, not chrome.** Setting
> `visualContainerObjects.padding` to anything > 0 (common when adding a
> `background` or `border`) shrinks the inner content rect *before* PBI
> lays out the header/search/items. Always re-run the formula after
> changing padding. Any non-zero VCO `padding` (e.g. 10/10/10/10 used by
> many fill/dark themes) subtracts directly from the available item area.

> ⚠️ **Theme-level `*.*` padding cascades to slicers.** The most common
> source of slicer clipping is a theme that sets
> `visualStyles."*"."*".padding` (e.g. the skill's default base theme uses
> `8/8/8/8`; many fork themes bump this to `10/10/10/10` for a more dramatic
> dark-card aesthetic). Every visual — including slicers — inherits it via
> the formatting cascade. **Always size slicer `h` to match the theme
> padding**: with theme padding `8/8`, use `h=80`; with `10/10`, use `h=80`
> (snapped); with `0/0`, use `h=64`. Re-run the formula above whenever you
> fork the base theme and change the global padding. Don't strip the
> padding from slicers as an escape — the breathing room around the header
> is part of the visual frame.

> ⚠️ **Don't switch `data.mode` from `'Dropdown'` to `'Basic'` without
> resizing.** The default 56px dropdown height fits exactly one inline
> row's worth of chrome — every row of data will be clipped. Always
> recalculate height when changing mode.
>
> `powerbi-report-author validate` flags slicers whose
> `position.height` is below the per-mode floor with
> `PBIR_SLICER_HEIGHT_BELOW_FLOOR` (warning). To inventory every slicer's mode
> and current height before resizing, run
> `powerbi-report-author preview-visuals <path>` and filter on
> `visualType` ∈ `slicer` / `listSlicer` / `advancedSlicerVisual` (both
> `visualType` and `position` are in the default output; `--with-derived`
> only adds `hasFilters`, `hasFormatting`, `hasVCOs`).

- Snap all coordinates to the 8px grid (round the formula result *up*).

### Fill variant

For the card-like white background (top strip placement), add VCO to
the template. The explicit `padding = 0/0/0/0` below is **deliberate**: the
white `background` fill is only painted *inside* the VCO padding rect, so
any non-zero padding leaves a transparent ring around the fill and the page
background bleeds through, breaking the solid-card look. This `0` override
is **not** a violation of the
[VCO override caveat](#per-visual-vco-override-caveat) — the caveat
requires `padding` to be *declared explicitly*, not to match any specific
value. When you use this variant, drop the dropdown template's `h=80` to
**`h=64`** (`60 + 0 + 0`, snapped) so the chrome still fits.

```json
"visualContainerObjects": {
  "background": [{ "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } },
    "transparency": { "expr": { "Literal": { "Value": "0D" } } }
  }}],
  "padding": [{ "properties": {
    "top": { "expr": { "Literal": { "Value": "0D" } } },
    "bottom": { "expr": { "Literal": { "Value": "0D" } } },
    "left": { "expr": { "Literal": { "Value": "0D" } } },
    "right": { "expr": { "Literal": { "Value": "0D" } } }
  }}]
}
```

---

### Date Between Slicer Template

For temporal filtering, use the `slicer` visual in `Between` mode only when
users need arbitrary date-range exploration and the bound field is a renderable
Date/DateTime column. For executive dashboards or annual/quarterly grain,
prefer a compact Year/Period dropdown or tile.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<unique-id>",
  "position": { "x": 1040, "y": 8, "z": 1000, "height": 80, "width": 216, "tabOrder": 1000 },
  "visual": {
    "visualType": "slicer",
    "query": {
      "queryState": {
        "Values": {
          "projections": [{
            "field": { "Column": { "Expression": { "SourceRef": { "Entity": "<table>" } }, "Property": "<date_column>" } },
            "queryRef": "<table>.<date_column>",
            "nativeQueryRef": "<date_column>"
          }]
        }
      }
    },
    "objects": {
      "data": [{ "properties": { "mode": { "expr": { "Literal": { "Value": "'Between'" } } } } }],
      "header": [{ "properties": {
        "show": { "expr": { "Literal": { "Value": "true" } } },
        "text": { "expr": { "Literal": { "Value": "'Date Range'" } } }
      }}]
    },
    "visualContainerObjects": {
      "padding": [{ "properties": {
        "top":    { "expr": { "Literal": { "Value": "8D" } } },
        "bottom": { "expr": { "Literal": { "Value": "8D" } } },
        "left":   { "expr": { "Literal": { "Value": "8D" } } },
        "right":  { "expr": { "Literal": { "Value": "8D" } } }
      }}]
    }
  }
}
```

**Sizing**:
- Inline with title: **`w=216, h = 60 + top + bottom`** — dates render
  side-by-side. With theme default `8/8` padding that's `h=80`; with zero
  padding `h=64`. This is the minimum width for side-by-side dates.
- Vertical rail: **`w=200, h = 84 + top + bottom`** — dates stack vertically
  at narrow widths.

Fill and light variants are the same as the dropdown slicer (see above).

---

## Add/Modify a Slicer

### Slicer types

| Type | `visualType` | Query roles | `data.mode` | Notes |
|------|-------------|-------------|-------------|-------|
| **Dropdown** | `slicer` | `Values` only (Column/Hierarchy) | `'Dropdown'` | Any cardinality, compact; default for executive Year/Period filters |
| **Date range** | `slicer` | `Values` only (Date/DateTime column) | `'Between'` | Date picker with range; use only for arbitrary date-range exploration |
| **Single** | `slicer` | `Values` only (Column) | `'Single'` | Single-select |
| **Before** | `slicer` | `Values` only (Date/Numeric) | `'Before'` | Upper bound only (≤) |
| **After** | `slicer` | `Values` only (Date/Numeric) | `'After'` | Lower bound only (≥) |
| **Relative date** | `slicer` | `Values` only (Date column) | `'Relative'` | "Last N days/months/years" — needs `data.relativeRange`, `relativePeriod`, `relativeDuration` + `dateRange.includeToday` + `general.filter` with DateSpan/DateAdd |
| **Relative time** | `slicer` | `Values` only (DateTime column) | `'RelativeTime'` | "Last N minutes/hours" — uses `data.relativeTimePeriod` instead of `relativePeriod` |
| **Scrollable list** | `listSlicer` | `Values` (Column/Hierarchy), `Tooltips` (Measure/Aggregation) | — | Default for list-style slicers. `data.mode` not available. |
| **Button/tile** | `advancedSlicerVisual` | `Values` (1 Column only), `Label` (1 Measure, optional), `Tooltips` (Aggregations) | — | ≤10 values, tile layout. `data.mode` not available. |

**Temporal decision matrix:**

| Signal | Use |
|---|---|
| Executive page, annual grain, ≤10 years | Year dropdown or year tile |
| Discrete period comparison (e.g., 2020 vs 2023) | Year/month dropdown with multi-select |
| Month/quarter reporting with 12-36 periods | Period dropdown or relative date |
| Arbitrary day/month range exploration on Date/DateTime field | Full-date `Between` |
| Integer/text date key or date picker does not render | Year/Period dropdown |

**Constraints:**
- `data.mode` is only available on the classic `slicer` visual — not on
  `listSlicer` or `advancedSlicerVisual`.
- `advancedSlicerVisual` allows only **one field** in `Values`.
- Hierarchy slicers: only `slicer` (mode: Basic/Dropdown) and `listSlicer`
  support hierarchies. Add `expansionStates` for expanded nodes (see
  expressions.md).
- A full-date column does not automatically mean `Between`. Choose by grain:
  Year/Period dropdown or tile for annual/quarterly executive pages; `Between`
  only when the field renders as Date/DateTime and users need arbitrary ranges.

### Setting slicer selections

The `general.filter` property in `objects` controls which values are
selected. This is only needed when pre-selecting specific values — omit
it entirely for the default "All" state.

```json
"general": [{
  "properties": {
    "orientation": { "expr": { "Literal": { "Value": "0D" } } },
    "filter": {
      "filter": {
        "Version": 2,
        "From": [
          { "Name": "d", "Entity": "dim_company", "Type": 0 }
        ],
        "Where": [{
          "Condition": { /* filter expression — see expressions.md */ },
          "Annotations": {
            "filterExpressionMetadata": {
              "expressions": [{ /* Column Expression for the filtered field */ }],
              "decomposedIdentities": {
                "values": [[
                  { "0": [{ "Literal": { "Value": "'A. Datum'" } }] },
                  { "1": [{ "Literal": { "Value": "'N'" } }] },
                  { "2": [{ "Literal": { "Value": "5L" } }] },
                  { "3": [{ "Literal": { "Value": "'A. Datum'" } }] }
                ]],
                "columns": [{ "value": { /* Column Expression — grouping key */ } }]
              },
              "valueMap": [{ "0": "A. Datum", "1": "N", "2": "5", "3": "A. Datum" }]
            }
          }
        }]
      }
    }
  }
}]
```

- `decomposedIdentities.values` — the actual selected values as literals
- `decomposedIdentities.columns` — the grouping key columns
- `valueMap` — maps indices in `decomposedIdentities` to queryRef values
- `expansionStates` — only needed for hierarchy slicers when nodes are expanded;
  `identityKeys` defined on the first level only, `identityValues` inside
  `root.children[]` only when a specific node has been toggled open
- **Literal format**: strings use single quotes inside double quotes
  (`"Value": "'A. Datum'"`); numbers use type suffixes (`"Value": "5L"`).

---

## Slicer Sync Groups

Slicers can be synced across pages so that changing a selection on one page
applies to all other pages with slicers in the same sync group. Add `syncGroup`
inside the `visual` object (sibling of `visualType`, `query`, `objects`):

```json
{
  "visual": {
    "visualType": "slicer",
    "syncGroup": {
      "groupName": "DateSync",
      "fieldChanges": true,
      "filterChanges": true
    },
    "query": { /* ... */ },
    "objects": { /* ... */ }
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `groupName` | string | Unique name for the sync group. Slicers with the same `groupName` across pages are synced. |
| `fieldChanges` | boolean | When `true`, field/projection changes propagate to all group members. |
| `filterChanges` | boolean | When `true`, filter/selection changes propagate to all group members. |

**Rules:**
- All slicers in the same sync group must have the same `visualType` and bound column.
  Slicers of the same type that produce the same filter expressions can be in the
  same group — e.g. two `slicer` visuals both bound to `Date.Date` with mode `'Between'`.
- Set the same `groupName` on each slicer you want synced (e.g. `"DateSync"`; any unique string works).
- Typically set both `fieldChanges: true` and `filterChanges: true`.

> **Note:** The published PBIR JSON schemas (`visualContainer/2.5.0–2.9.0`) do
> not list `syncGroup`. However, the internal schema (`visualConfiguration/9999.0.0`)
> does include it with full type definition. Desktop reads and writes it correctly.

---

## Theme Approach

These slicer defaults are applied report-wide via theme `visualStyles`
(plain JSON, not PBIR `expr` wrappers):

```json
"slicer": {
  "*": {
    "header": [{
      "fontFamily": "Segoe UI Semibold",
      "textSize": 10,
      "fontColor": { "solid": { "color": "#252423" } },
      "outlineStyle": 0
    }],
    "items": [{
      "fontFamily": "Segoe UI Variable, Segoe UI, sans-serif",
      "textSize": 9,
      "fontColor": { "solid": { "color": "#252423" } },
      "outlineStyle": 0,
      "padding": 2
    }]
  }
}
```

The global `*.*` wildcard also provides: border (#E8E8E8, radius=8),
hidden visual header, and VCO padding (8px). Per the
[VCO override caveat](#per-visual-vco-override-caveat), this `*.*.padding`
cascade is **dropped** the moment a slicer sets any per-visual VCO, so every
slicer template must redeclare `padding` explicitly — `8/8/8/8` to match the
theme for normal slicers, or `0/0/0/0` for the [fill variant](#fill-variant)
(so the white fill reaches the container edges).

> `header.text` does **NOT** usefully cascade from theme — it would set
> the same name on every slicer. Always set per-visual.

---

## Discovering Properties

```bash
# List all formatting objects for a slicer type
powerbi-report-author formatting list-objects slicer
powerbi-report-author formatting list-objects advancedSlicerVisual
powerbi-report-author formatting list-objects listSlicer

# Inspect specific objects
powerbi-report-author formatting describe-object slicer header
powerbi-report-author formatting describe-object slicer items
powerbi-report-author formatting describe-object slicer data
powerbi-report-author formatting describe-object slicer selection

# Search across all objects
powerbi-report-author formatting search slicer "font|text|padding"
```
