# Slicer Authoring Guide

## Contents

- [Recommended Defaults](#recommended-defaults)
  - [Slicer Template](#slicer-template)
  - [`Values` projection count](#values-projection-count)
  - [Sizing](#sizing)
  - [Fill variant](#fill-variant)


> **Always read first** when adding/modifying slicers or slicer selections.
> For expression reference, see **references/authoring/expressions.md**

Slicers provide interactive filtering. This guide covers creation,
formatting defaults, and selection configuration for all slicer types.

- [Slicer Authoring Guide](#slicer-authoring-guide)
  - [Recommended Defaults](#recommended-defaults)
    - [Slicer Template](#slicer-template)
    - [Sizing](#sizing)
    - [Fill variant](#fill-variant)
    - Calendar Date Picker Templates (continued in `slicers-part-02.md`)
    - Date Between Slicer Template (continued in `slicers-part-02.md`)
  - Add/Modify a Slicer (continued in `slicers-part-02.md`)
    - Slicer types (continued in `slicers-part-02.md`)
    - Setting slicer selections (continued in `slicers-part-02.md`)
  - Slicer Sync Groups (continued in `slicers-part-02.md`)
  - Theme Approach (continued in `slicers-part-02.md`)
  - Discovering Properties (continued in `slicers-part-02.md`)

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
roles, and `data.mode` per type (see Slicer types (continued in `slicers-part-02.md`) below).

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

### `Values` projection count

The number of projections allowed in the `Values` role depends on the slicer type:

- **`slicer`, `filterSlicer` and `listSlicer`** may have **more than one** projection in `Values`.
  Multiple fields make it a **hierarchy slicer**.
- **All other slicers** (`advancedSlicerVisual`, `textSlicer`,
  and the single-field `slicer` modes `Single`, `Between`, `Before`, `After`,
  `Relative`, `RelativeTime`, `RelativeDatePicker`) must have **exactly one**
  projection in `Values`.

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
(Year, Stance), 216px for compact `'Between'` date pickers (stacked dates).

> **No height/font shortcuts**: if a slicer collides with the next row or clips
> on a dark/fill theme, increase the reserved band/rail and recompute `h`.
> Do not lower header/items/date text below 9pt or force `h=48` to make the
> layout fit.

**Height by mode:**

| Mode / `visualType` | Height | Notes |
|---|---|---|
| `slicer` mode `'Dropdown'` | **`h = 60 + top_padding + bottom_padding`**, snap up to the next 8px. Worked values: zero padding → **h=64**; theme default `8/8` → **h=80**; dark-card `10/10` → **h=80**. The 60px chrome = `header (~28px at 10pt Semibold) + dropdown selector field (~32px)`. | Items render in a popup, not inline, so item count doesn't affect height. The padding stays *outside* the visible chrome — every padding pixel must be added to `h`. **Verify the layout below the slicer leaves room for the new height** (e.g. if a fork bumps padding from 8 to 10, recompute and shift the next-row visuals). |
| `slicer` mode `'Between'` | At `w=216`, dates stack vertically: **`h = 84 + top + bottom`**, snapped up to the next 8px. With 8/8 padding, use **h=104**. | Desktop validation shows that `w=216, h=80` clips the lower date input. Use a wider container only after screenshot validation confirms both dates render side-by-side. |
| `slicer` mode `'Before'` / `'After'` | **`h = 60 + top + bottom`**, snapped up to the next 8px. | These modes render one date bound. |
| `slicer` mode `'RelativeDatePicker'` | **`w >= 280, h >= 240`**, plus any outer layout space required by titles. | Renders the calendar-style Date Picker. Use the same mode for default, fixed-range, and relative preselection. See Calendar Date Picker Templates (continued in `slicers-part-02.md`). |
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
> `powerbi-report-author validate` checks dropdown slicer height in two tiers:
> it emits `PBIR_SLICER_HEIGHT_BELOW_FLOOR` (**error**) when
> `position.height` is below the header-hidden floor (`selector 32 + padding`),
> where the selector itself would be clipped; and
> `PBIR_SLICER_HEADER_MAY_CLIP` (**warning**) when the height clears the
> selector floor but is below the full height that also reserves the header row
> (`header 28 + selector 32 + padding`), meaning Desktop may hide or clip the
> header. To inventory every slicer's mode
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
