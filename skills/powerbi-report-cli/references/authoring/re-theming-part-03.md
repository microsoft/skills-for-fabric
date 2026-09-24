# Re-theming & Dark Mode — Workflow Reference - Part 3

Continuation of `re-theming.md`. Open this file directly from the skill reference index.

## Dark Mode Authoring Checklist

Dark mode triggers every formatting trap simultaneously. Follow this checklist
to avoid multiple iteration rounds debugging silent failures.

> **Existing report?** If applying dark mode to a report that already has
> visuals with per-visual formatting, you MUST also follow
> § Re-theming Workflow (Steps 0–4) to sweep hardcoded
> colors. The theme alone will NOT update per-visual overrides. After the
> sweep, verify these common symptoms are resolved:
>
> | Symptom | Cause | Fix |
> |---------|-------|-----|
> | Chart card stays white/light | VCO `background.color` set to light hex | Update to dark color or remove to inherit |
> | Page background white on dark theme | `page.json` has no `objects.background` (defaults to white) | Add explicit `objects.background` with dark color |
> | Shape retains old accent | `objects.fill.fillColor` hardcoded | Update to dark-appropriate color |
> | Slicer dropdown stays white | `objects.items.background` not set (defaults to white) | Set `items.background` to dark color |
> | Slicer text invisible | `objects.items.fontColor` dark on dark bg | Set to light color |
> | Card/textbox text invisible | `fontColor` or `textStyle.color` dark | Set to light color (with `{ id: "default" }` for cards) |
> | Axis labels invisible | `labelColor` set dark | Update to light color |
> | VCO title invisible | `title.fontColor` dark | Update to light color |

### Step 1: Theme structural colors

Set ALL structural colors together in `theme.json` (see theming.md § Structural Colors (see `theming.md`, section `4-structural-colors`)):
`background`, `foreground`, `firstLevelElements`, `secondLevelElements`,
`tableAccent`, `secondaryBackground`, `dataColors` array.

> Missing any one structural color creates invisible text or clashing chrome.

### Step 2: Page canvas backgrounds

Set `page.json → objects.background.color` on **every page** to the dark canvas
color. The page background does NOT inherit from the theme's `background`
structural color — it must be set explicitly per page.
See formatting-overview.md § Page Objects (see `formatting-overview.md`) for the JSON structure.

### Step 3: Filter pane + filter cards

The filter pane does **NOT** inherit from structural colors — set `outspacePane`
and `filterCard` (with `"$id": "Applied"` and `"$id": "Available"`) in
`visualStyles["*"]["*"]`. See filter-pane.md (see `filter-pane.md`).

### Step 4: Slicer entries in `visualStyles`

Modern slicers (`filterSlicer`, `advancedSlicerVisual`) do **NOT** inherit from
the legacy `"slicer"` key. Add entries for **all three** slicer types — set
`items.background`, `items.fontColor`, `header.background`, `header.fontColor`.

> Per-visual `objects` (Priority 2) override `visualStyles`. Include old slicer
> hex values in your Step 0 color mapping so the sweep updates them.

See slicers.md (see `slicers.md`) for full `visualStyles` slicer JSON templates.

### Step 5: Azure Map basemap style

`objects.mapControls.defaultStyle` is an enum, not a color — bulk sweeps miss it.
- Light theme: `road` or `grayscale_light`
- Dark theme: `night`, `grayscale_dark`, or `high_contrast_dark`

### Step 6: Table/matrix `stylePreset` = `'None'`

Style presets override explicit row/header colors with white/gray backgrounds.
Set `stylePreset` to `'None'` on every `tableEx`/`pivotTable` with custom colors.
See table.md § Style Presets (see `table.md`, section `style-presets-for-tables`).

### Step 7: Visual-specific dark mode properties

| Visual | What to set | Reference |
|--------|-------------|-----------|
| `tableEx` / `pivotTable` | `values.backColorPrimary/Secondary`, `values.fontColorPrimary/Secondary`, `columnHeaders.backColor/fontColor`, `rowTotal.fontColor/backColor`, `columnTotal.fontColor/backColor` | table.md (see `table.md`) |
| `cardVisual` | `fillCustom` with `{ id: "default" }` selector, `value.fontColor`, `label.fontColor` | card.md (see `card.md`) |
| `shape` | `text.fontColor` (explicit — shapes with `text.show: true` but no `fontColor` inherit wrong color after polarity switch) | shape.md (see `shape.md`) |
| `textbox` | `textRuns[].textStyle.color` per run | textbox.md (see `textbox.md`) |

### Step 8: Contrast audit

Verify all text-bearing properties have adequate contrast against their
backgrounds. Key properties per type:

| Visual Type | Properties to verify |
|---|---|
| `tableEx` / `pivotTable` | `values.fontColorPrimary/Secondary`, `columnHeaders.fontColor`, `rowTotal.fontColor`, `columnTotal.fontColor` |
| `cardVisual` | `value.fontColor`, `label.fontColor` (with `{ id: "default" }`) |
| Charts | `categoryAxis.labelColor`, `valueAxis.labelColor`, `legend.labelColor` |
| Slicers | `items.fontColor`, `header.fontColor` |

Also verify chart series colors are saturated/vivid — dark/muted `dataColors`
blend into dark backgrounds making bars and lines invisible.
