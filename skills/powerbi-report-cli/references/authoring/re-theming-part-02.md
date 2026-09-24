# Re-theming & Dark Mode — Workflow Reference - Part 2

## Contents

- [Re-theming an Existing Report](#re-theming-an-existing-report)
  - [Why Theme Changes Don't Fully Propagate](#why-theme-changes-dont-fully-propagate)
  - [Re-theming Workflow](#re-theming-workflow)
  - [Preventive Authoring: Theme-Adaptive Visuals](#preventive-authoring-theme-adaptive-visuals)


Continuation of `re-theming.md`. Open this file directly from the skill reference index.

## Re-theming an Existing Report

When switching a report to a new theme (especially light → dark or dark → light),
changing `theme.json` alone is **not sufficient** if visuals have per-visual
`objects` or `visualContainerObjects` color properties. Those per-visual colors
override the theme cascade and remain unchanged.

### Why Theme Changes Don't Fully Propagate

The formatting cascade (formatting-overview.md) resolves as:

```
Priority 1: Conditional formatting        ← highest, always wins
Priority 2: Per-visual objects             ← overrides theme
Priority 3: Visual container objects (VCO) ← overrides theme
Priority 4: Page objects
Priority 5: Theme visualStyles[type]       ← only applies if no per-visual override
Priority 6: Theme visualStyles["*"]
Priority 7: Base theme
Priority 8: System defaults
```

If a visual has **any** explicit `objects` or `visualContainerObjects` color
properties, those win over the new theme. The visual appears unchanged
despite the theme switch.

**Key insight**: If an `objects` group has even ONE explicit property (e.g.,
`columnAdjustment: 'growToFit'`), ALL color properties in that same group
stop inheriting from the theme. You must add/update explicit colors for
every property in that group.

### Re-theming Workflow

> **⚠️ POLARITY CHANGE GATE — Read this FIRST:**
> Determine whether the theme switch changes polarity (dark → light or
> light → dark). A polarity change means foreground/text colors that were
> designed for contrast against the old background MUST flip too:
>
> - **Dark → Light**: Light text (`#F9FAFB`, `#E6EDF3`, `#FFFFFF`) → dark
>   text (`#1F2937`, `#252423`, `#333333`)
> - **Light → Dark**: Dark text (`#1F2937`, `#252423`, `#333333`) → light
>   text (`#F9FAFB`, `#E6EDF3`, `#FFFFFF`)
>
> These foreground colors are hardcoded as `Literal` values on shapes,
> textboxes, slicer items/headers, card values, and nav buttons. The theme
> cascade does NOT override them. **If you omit foreground colors from your
> color mapping and sweep, text becomes invisible** — light-on-light or
> dark-on-dark.
>
> Same-polarity switches (dark → dark, light → light) may share foreground
> values, but include them in the mapping when they differ — different text
> shades produce a more cohesive result. The sweep of accent/background colors
> is always needed — shapes, nav buttons, accent bars, and chart borders
> commonly hardcode `dataColors[0]` and other accent hex values as Literal
> fills/outlines that do not auto-resolve via the theme cascade.

#### Step 0: Build a color mapping table

Before touching any files, extract all hex colors from the **old** theme JSON
and map each to its replacement in the **new** theme. Include ALL categories:

- **Foreground/text colors** (`foreground`, `firstLevelElements`,
  `secondLevelElements`, `textClasses` colors) — critical for polarity changes
  (visibility), but also include for same-polarity changes when the new theme
  uses different text shades for a more cohesive result
- Structural colors (`background`, `secondaryBackground`, `thirdLevelElements`)
- `dataColors` array (index-by-index) — **CRITICAL even for same-polarity
  changes.** Shapes, nav buttons, accent bars, and chart borders commonly
  hardcode `dataColors[0..N]` hex values as Literal fills/outlines. These do
  NOT auto-resolve via `ThemeDataColor` or the theme cascade. Grep `definition/`
  for every old `dataColors` value.
- `tableAccent`, `good`/`neutral`/`bad`, `maximum`/`center`/`minimum`
- `visualStyles` colors (borders, gridlines, accent colors, backgrounds)
- **⚠️ Page-level background/outspace colors** — these are NOT in the theme
  file but are hardcoded in `page.json` files. For polarity switches in either
  direction, the page background retains the old theme's color (e.g., dark→light:
  a dark hex like `#1A1A2E` remains; light→dark: a light hex like `#FFFFFF`
  remains). **Grep all `page.json` files for their current `background` and
  `outspace` color values and include them in the mapping.** This is the second
  most commonly missed category after foreground text.
- **⚠️ Slicer `items.background` and `header.background`** — on polarity
  changes, slicer dropdown backgrounds are hardcoded Literal values at
  Priority 2. Light→dark: set dark. Dark→light: set light/white.
  **⚠️ Slicer header.background requires SEMANTIC mapping, not accent mapping:**
  In dark themes, slicer headers typically use a colored/accent background bar
  (e.g., `#3730A3`) with white text. In light themes, slicer headers
  conventionally have a **white or transparent background** with dark text —
  NOT the new accent color. If you naively map the old dark header background
  to the new theme's accent color, you get a heavy colored bar that looks
  wrong in a light context. Map dark-theme slicer `header.background` to
  `#FFFFFF` (or remove the property to inherit) for dark→light changes.
- **⚠️ Azure Map basemap style** — `azureMap.objects.mapControls.defaultStyle`
  is a hardcoded enum, not a hex color, so bulk color replacement will never
  update it. For polarity switches: light→dark use `night`, `grayscale_dark`,
  or `high_contrast_dark`; dark→light use `road` or `grayscale_light`.

```
Old hex    → New hex    Category
#1F2937    → #F9FAFB    FOREGROUND
#0F172A    → #FFFFFF    BACKGROUND
#1E293B    → #F8FAFC    SECONDARY BG
#3B82F6    → #2563EB    ACCENT (dataColors[0])
#312E81    → #FFFFFF    VISUAL CARD BG (semantic: cards are white in light themes)
#3730A3    → #FFFFFF    SLICER HEADER BG (semantic: no colored bar in light themes)
#6366F1    → #BBF7D0    BORDER (semantic: soft/muted border for light themes)
```

Extract actual hex values from the old and new theme JSON files. Every color
that differs needs a row — including foreground colors when they differ between
old and new themes.

> **⚠️ SEMANTIC ROLE AWARENESS — critical for polarity changes:**
> Not every color maps 1:1 from old theme to new theme. Some colors serve a
> structural role that changes meaning across polarities:
>
> - **Colored header/accent backgrounds** (slicer headers, table column headers
>   with solid fills): In dark themes these are typically mid-tone accent bars
>   for visual separation. In light themes, the same role is usually served by
>   white/transparent backgrounds — the accent color moves to borders or text
>   instead. Map these to `#FFFFFF` for dark→light.
> - **Visual card backgrounds**: Dark themes use dark card fills. Light themes
>   use white (`#FFFFFF`), not the new theme's background color (which is for
>   the page canvas, not cards).
> - **Border/accent colors**: Dark themes use bright borders for contrast.
>   Light themes typically use soft/muted borders (e.g., light green `#BBF7D0`
>   instead of saturated `#16A34A`).
>
> Build a two-column mapping where the **target** color reflects the
> **semantic role** in the new polarity, not just index-matching from old→new
> theme properties.

#### Step 1: Update theme JSON AND bulk-replace all old colors (single atomic step)

> **Do NOT preview until this entire step is complete.**

**1a. Update the custom theme JSON by writing a new GUID-suffixed file** —
any change to the active
`StaticResources/RegisteredResources/<CustomThemeName>-<guid>.json` file
requires a new GUID, regardless of what changed (colors, fonts,
`visualStyles`, metadata, schema, whitespace, or any other content). Do not edit
the existing GUID-suffixed theme file in place and keep the same filename.
**Keep the same `<CustomThemeName>`** — only rotate the GUID suffix per the
GUID convention in theming.md (see `theming.md`, section `theme-name-guid-convention-cache-busting`).
Do NOT rename `<CustomThemeName>` (e.g., `DarkCoral` stays `DarkCoral` even if
the new palette is light green) unless the user explicitly asks to rename it.
Update all `report.json` references to match the new GUID. For dark themes,
update ALL structural colors together (see § Structural Colors above).

**1b. Bulk-replace old-theme hex values across the entire `definition/`
directory** using the color mapping from Step 0.

**Sweep category checklist — include ALL applicable rows from Step 0:**

- [ ] Background colors (page canvas, card/VCO backgrounds)
- [ ] Secondary/tertiary background colors
- [ ] Border/divider/gridline colors
- [ ] Accent/data colors
- [ ] **Foreground/text colors** — MANDATORY for polarity changes (dark↔light).
      These are the inline `fontColor`, `text.fontColor`, `labelColor`,
      `textRuns[].textStyle.color` values on shapes, slicers, cards, textboxes,
      and nav buttons. Omitting this category guarantees invisible text.
- [ ] **Slicer `items.background` and `header.background`** — MANDATORY for
      polarity changes. Dropdown backgrounds are hardcoded Literal values that
      don't inherit from theme. Light→dark: set dark. Dark→light: set light.
      **For `header.background` specifically**: dark→light should map to
      `#FFFFFF` (not the new accent), because light-theme slicers use
      transparent/white headers. See § Semantic Role Awareness above.
- [ ] **`#FFFFFF` VCO backgrounds on all visuals** — MANDATORY for light→dark.
      `#FFFFFF` has dual meaning in light themes (card backgrounds AND text on
      colored shapes). Exclude it from the bulk sweep; instead scan all
      `visual.json` for `#FFFFFF` in `visualContainerObjects.background.color`
      and replace with the dark card color. Leave `#FFFFFF` in text contexts
      (shape `fontColor`, textbox `textRuns` color). See § 1b-extra-2 below.
- [ ] **Azure Map `mapControls.defaultStyle`** — MANDATORY for polarity
      changes. The basemap style is an enum (`night`, `road`,
      `grayscale_dark`, etc.), not a color, so it is missed by hex sweeps.

**1b-extra. Pages without explicit `objects.background` (polarity changes):**

During polarity changes, pages that have **no** `objects.background` property
at all will default to white (system default) regardless of the theme's
`background` value. The bulk hex-sweep cannot fix these because there is no
color value to replace. After the bulk sweep, scan all `page.json` files for
pages missing `objects.background` entirely and add one with the new theme's
`background` value. See formatting-overview.md § Page Objects (see `formatting-overview.md`)
for the JSON structure.

**1b-extra-2. Remaining `#FFFFFF` VCO backgrounds (light→dark):**

In light themes, `#FFFFFF` is used for **both** visual card/VCO backgrounds
(which must become dark) **and** text colors on colored shapes/title bars
(which must stay white for contrast). The bulk hex-sweep cannot distinguish
these two roles, so `#FFFFFF` must be excluded from the main sweep and handled
separately.

After the bulk sweep, scan all `visual.json` files for `#FFFFFF` inside
`visualContainerObjects.background.color` properties and replace with the new
theme's card background color (e.g., `#312E81`). This applies to **all** visual
types — charts (donut, bar, column, line, pie, area), cards, tables, maps, and
any other visual with an explicit white VCO background.

Do **NOT** replace `#FFFFFF` in these text contexts — they need white for
contrast against colored fills:
- `objects.text.fontColor` (shape visuals)
- `objects.general.paragraphs[].textRuns[].textStyle.color` (textboxes)
- `visualContainerObjects.title.fontColor` (when title sits on a colored bar)

> **Why this is commonly missed:** The theme wildcard `visualStyles["*"]["*"].background`
> sets card backgrounds for visuals that inherit from theme. But visuals with
> **any** explicit `visualContainerObjects.background` property (even just
> `show: true` or `transparency`) stop inheriting — they retain whatever `color`
> value they have. In light themes that value is almost always `#FFFFFF`.

```bash
# Grep the report definition tree for ALL old-theme hex values (including foreground!)
grep -rn "<old.background>\|<old.secondaryBg>\|<old.border>\|<old.accent>\|<old.foreground>" <report>.Report/definition/

# Replace systematically (prefer JSON-aware tooling or edit tool over regex):
# For each old_hex → new_hex pair in the mapping, replace across all JSON files
# in definition/ — this covers pages, visuals, and VCOs in one sweep.
```

**1c. Confirm zero old-theme colors remain:**

```bash
grep -rn "#EDE9FE\|#F5F3FF\|..." <report>.Report/definition/
# Expected: no matches
```

Only after confirming zero matches should you proceed to Step 2.

#### Step 2: Audit per-visual formatting for gaps

This step catches cases the bulk sweep cannot fix — visuals that **lack** a
color property entirely (relying on theme inheritance that may now produce wrong
results) or that need new properties added.

> **Bulk hex-replacement is insufficient** when a visual *lacks* a color
> property entirely. Shape `text` objects commonly omit `fontColor` (relying on
> theme inheritance), so a find-and-replace pass won't touch them. After bulk
> replacement, scan for shapes with `text.show: true` that have no explicit
> `fontColor` and add one.

**Quick-reference — properties to audit per visual type:**

| Visual Type | Key color properties to check | Details |
|---|---|---|
| `tableEx` / `pivotTable` | `columnHeaders.fontColor/backColor`, `values.fontColorPrimary/Secondary`, `values.backColorPrimary/Secondary`, `rowTotal.fontColor/backColor`, `columnTotal.fontColor/backColor` | table.md (see `table.md`) |
| `cardVisual` | `value.fontColor`, `label.fontColor`, `fillCustom` (all need `{ id: "default" }`) | card.md (see `card.md`) |
| Bar/column/line charts | `categoryAxis.labelColor`, `valueAxis.labelColor`, `labels.color`, `gridlineColor` | cartesian.md (see `cartesian.md`) |
| `azureMap` | `mapControls.defaultStyle` (enum), marker/bubble colors | map.md (see `map.md`) |
| `slicer` / `filterSlicer` / `advancedSlicerVisual` | `header.fontColor/background`, `items.fontColor/background` | slicers.md (see `slicers.md`) |
| `textbox` | `textRuns[].textStyle.color` inside `paragraphs` array | textbox.md (see `textbox.md`) |
| `shape` | `fill.color`, `line.color`, `text.fontColor` (**must be explicit** if `text.show: true`) | shape.md (see `shape.md`) |

**VCO properties to check on every visual** (regardless of type):
`background.color`, `border.color`, `title.fontColor`, `title.background`,
`subTitle.fontColor`, `divider.color`, `dropShadow.color`,
`visualHeader.background/foreground`.

**CLI commands for discovery:**

```bash
powerbi-report-author formatting list-objects <visualType>
powerbi-report-author formatting describe-object <visualType> <objectName>
```

Properties with `type: "fill"` are the ones that need color adjustment.

> **Critical for tables/matrices**: If you set custom row colors, you MUST also
> set `stylePreset` to `'None'` — otherwise the default preset overrides your
> colors. See table.md § Style Presets (see `table.md`, section `style-presets-for-tables`).

#### Step 3: Ensure contrast and visibility

For every visual with explicit formatting, verify foreground/background contrast:

- Dark background → light text; light background → dark text
- Chart axis labels/legend must contrast with VCO background (or page canvas)
- Slicer items must contrast with slicer body background
- Chart series colors (`dataPoint.fill` or `dataColors`) must be saturated/vivid —
  dark/muted colors blend into dark backgrounds making bars/lines invisible

#### Step 4: Validate and verify

Follow the standard edit -> validate -> preview -> screenshot review loop in
preview.md (see `preview.md`).

### Preventive Authoring: Theme-Adaptive Visuals

To minimize re-theming effort when building new reports:

1. **Minimize explicit color properties** — let the theme cascade handle defaults.
2. **Use `ThemeDataColor` references** for adaptive colors:
   `{ "ThemeDataColor": { "ColorId": 0, "Percent": 0.4 } }`
3. **Set table/chart colors via theme `visualStyles`** when possible.
4. **Document your color mapping** for systematic future switches.

> **Use `ThemeDataColor`** for: VCO `background`, `border`, `title.fontColor`,
> `values.backColorPrimary/Secondary`, `columnHeaders.backColor/fontColor`.
>
> **Use `Literal` hex** for: `dataPoint.fill` with `metadata` selectors,
> `FillRule` gradient stops (ThemeDataColor silently breaks these).

> **Key insight**: If an `objects` group exists on a visual (even for a non-color
> property like `columnAdjustment`), color properties in that same group will NOT
> inherit from the theme — you must add explicit color properties to any group
> that already has explicit entries. Use `ThemeDataColor` so they stay adaptive.
