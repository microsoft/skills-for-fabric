# Theme Authoring — theme.json Reference

> Referenced from SKILL.md. Read [formatting-overview.md](formatting-overview.md) first for the cascade model.
> Read this when creating or editing a Power BI custom theme JSON file.
> Theme files live in `StaticResources/RegisteredResources/` within the report.

## Table of Contents

- [Registering a Custom Theme](#registering-a-custom-theme)
  - [Theme Name GUID Convention (Cache-Busting)](#theme-name-guid-convention-cache-busting)
- [Schema Version](#schema-version)
- [Theme JSON Anatomy](#theme-json-anatomy)
- [1. Data Colors (`dataColors`)](#1-data-colors-datacolors)
- [2. Sentiment Colors](#2-sentiment-colors)
- [3. Gradient Defaults](#3-gradient-defaults)
- [4. Structural Colors](#4-structural-colors)
- [5. Text Classes (`textClasses`)](#5-text-classes-textclasses)
- [6. Visual Styles (`visualStyles`)](#6-visual-styles-visualstyles)
- [7. Style Presets](#7-style-presets)
- [8. ThemeDataColor Resolution](#8-themedatacolor-resolution)
- [9. Theme Defaults for Page Objects](#9-theme-defaults-for-page-objects)
- [10. Custom Icons](#10-custom-icons)
- [Re-theming & Dark Mode](#re-theming--dark-mode)
- [Theme Authoring Best Practices](#theme-authoring-best-practices)
- [Common Pitfalls](#common-pitfalls)

## Registering a Custom Theme

A custom theme requires two entries in `report.json`:

1. **`themeCollection.customTheme`** — references the theme by name and type:
```json
"customTheme": {
  "name": "MyTheme-a1b2c3d4.json",
  "reportVersionAtImport": { "visual": "...", "report": "...", "page": "..." },
  "type": "RegisteredResources"
}
```

2. **`resourcePackages[]`** — registers the file so Desktop can locate it:
```json
{
  "name": "RegisteredResources",
  "type": "RegisteredResources",
  "items": [{
    "name": "MyTheme-a1b2c3d4.json",
    "path": "MyTheme-a1b2c3d4.json",
    "type": "CustomTheme"
  }]
}
```

### Theme Name GUID Convention (Cache-Busting)

Power BI Desktop caches themes by name. To guarantee that every theme edit
is picked up on reload, **append a short GUID suffix** to the theme filename:

```
<CustomThemeName>-<guid>.json
```

- **`<CustomThemeName>`** — the user-provided name (e.g., `DarkCoralTheme`) or
  the name you choose if the user doesn't specify one. Once established, the
  `<CustomThemeName>` is **stable** — it does NOT change when the theme content
  is updated (even if the palette changes entirely). Only change
  `<CustomThemeName>` if the user explicitly asks to rename the theme.
- **`<guid>`** — a freshly generated short GUID (8–12 hex chars is sufficient,
  e.g., `a1b2c3d4`). Use a full UUID without dashes truncated to 8+ chars, or
  any unique random hex string.

**Examples:**
- User says "call it DarkCoralTheme" → `DarkCoralTheme-f7e2a91c.json`
- You choose the name → `ExecutiveDark-3bc04d8e.json`
- User later says "change to light green palette" → keep the same
  `<CustomThemeName>`, only rotate the GUID: `DarkCoralTheme-e4f5a6b7.json`
  (content changes, `<CustomThemeName>` stays)
- User says "change the theme to dark orange" → this is a palette/style change,
  NOT a rename. Keep the same `<CustomThemeName>`, only rotate the GUID and
  update content. Phrases like "change the theme to X" or "apply a X theme"
  describe the desired appearance — they are NOT rename requests.
- User says "rename the theme to LightGreen" → now change
  `<CustomThemeName>`: `LightGreen-e4f5a6b7.json`

**On every custom theme file update** — any change to
`StaticResources/RegisteredResources/<CustomThemeName>-<guid>.json`, regardless
of what changed (colors, fonts, `visualStyles`, metadata, schema, whitespace, or
any other content):

1. Generate a **new GUID**. **Keep the same `<CustomThemeName>`** — do NOT
   change it unless the user explicitly requests a rename.
2. **Edit the theme file content** in place — update colors, fonts,
   `visualStyles`, and update the `"name"` field inside the JSON to match the
   new filename (e.g., `"DarkCoralTheme-e4f5a6b7.json"`).
3. **Rename the file** from `<CustomThemeName>-<oldGUID>.json` to
   `<CustomThemeName>-<newGUID>.json` using a filesystem rename (`Rename-Item`
   / `mv`) — do NOT create a new file and delete the old one; rename is
   equivalent and avoids a redundant write + delete.
4. **Update all references** in `report.json`:
   - `themeCollection.customTheme.name`
   - `resourcePackages[].items[].name`
   - `resourcePackages[].items[].path`
5. Reload Desktop — the new filename guarantees cache invalidation.

> **Why?** Desktop's theme engine caches by filename. Editing a file in place
> with the same name can leave stale theme state even after reload. Changing
> the filename on every update forces a fresh load every time.

> **Important:** Inside `report.json`, both `customTheme.name` and the
> matching `resourcePackages[].items[].name` MUST include the `.json`
> extension (e.g., `"MyTheme-a1b2c3d4.json"`) and MUST equal the item's `path`.
> Using the bare theme name (e.g., `"MyTheme-a1b2c3d4"`) causes the published
> report on the Power BI service to incorrectly apply the theme because the resource
> mapping never matches the file under `StaticResources/RegisteredResources/`.
>
> The `path` must be the **filename only** (e.g., `"MyTheme-a1b2c3d4.json"`)
> with the `.json` extension. Do NOT include directory prefixes like
> `"RegisteredResources/MyTheme-a1b2c3d4.json"` — this causes Desktop to silently
> ignore the theme.
>
> The `name` field **inside the theme JSON file itself** MUST match
> `customTheme.name` / `resourcePackages[].items[].name` exactly, including the
> `.json` extension (e.g., `"MyTheme-a1b2c3d4.json"`). Using a bare name such as
> `"MyTheme-a1b2c3d4"` causes validation failure and can break Desktop theme
> loading.
>
> Run `powerbi-report-author validate <path-to-.Report-dir>` after
> registering or editing a theme to catch registration and theme JSON issues
> before reloading Desktop.

## Schema Version

Set `"$schema"` to a published `reportThemeSchema-<major>.<minor>.json` from the
[powerbi-desktop-samples repo](https://github.com/microsoft/powerbi-desktop-samples/tree/main/Report%20Theme%20JSON%20Schema/).

How to choose the version:

1. **Check Microsoft's base themes first.** Scan
   `<Report>/StaticResources/SharedResources/BaseThemes/*.json` for any file
   that carries a `"$schema"`. If found, **reuse the same version** — those
   files are shipped by Power BI Desktop and represent the version it
   currently understands.
2. **No `"$schema"` in any base theme** (the common case today, since the
   shipped base themes don't pin one) — use the **latest published**
   `reportThemeSchema-<version>.json` from the samples repo above.

Reference the schema as a full published HTTPS URL or as a local
`reportThemeSchema-<version>.json` placed beside the theme JSON.

## Theme JSON Anatomy

A custom theme has 7 sections. All use **plain JSON encoding** (no PBIR expression wrappers):

```json
{
  "name": "MyTheme-a1b2c3d4.json",

  "dataColors": ["#118DFF", "#12239E", "#E66C37", ...],

  "good": "#1AAB40",
  "neutral": "#D9B300",
  "bad": "#D64554",

  "maximum": "#118DFF",
  "center": "#D9B300",
  "minimum": "#DEEFFF",
  "null": "#FF7F48",

  "foreground": "#252423",
  "background": "#FFFFFF",
  "tableAccent": "#118DFF",

  "textClasses": { ... },
  "visualStyles": { ... },
  "icons": { ... }
}
```

## 1. Data Colors (`dataColors`)

An array of hex strings defining the categorical color palette:

```json
"dataColors": [
  "#118DFF", "#12239E", "#E66C37", "#6B007B", "#E044A7",
  "#744EC2", "#D9B300", "#D64550", "#197278", "#1AAB40"
]
```

- Indexed by `ThemeDataColor.ColorId` (0-based) in PBIR formatting
- The default base theme has **41 colors**
- Custom `dataColors` **fully replaces** the base theme array (no merge)
- When exhausted, PBI generates unique colors via saturation/hue shifts

## 2. Sentiment Colors

Used by waterfall charts and KPI visuals:

| Key | Purpose | Default |
|-----|---------|---------|
| `good` | Positive values | `#1AAB40` (green) |
| `neutral` | Neutral values | `#D9B300` (yellow) |
| `bad` | Negative values | `#D64554` (red) |

## 3. Gradient Defaults

Default colors for the conditional formatting color-scale dialog:

| Key | Purpose | Default |
|-----|---------|---------|
| `maximum` | Highest value | `#118DFF` |
| `center` | Middle value (diverging) | `#D9B300` |
| `minimum` | Lowest value | `#DEEFFF` |
| `null` | Null values | `#FF7F48` |

These keys only seed/default the color-scale picker. Custom theme JSON does not
author conditional formatting rules; apply rules on the target visual.

## 4. Structural Colors

Foundational UI colors. The 7 classes (with legacy aliases):

| Preferred Name | Alias | What It Formats |
|---------------|-------|-----------------|
| `firstLevelElements` | `foreground` | Labels, trend lines, textbox defaults, card data labels, slicer item color |
| `secondLevelElements` | `foregroundNeutralSecondary` | Legend labels, axis labels, table headers, gauge target |
| `thirdLevelElements` | `backgroundLight` | Gridlines, table grid, slicer header background, shape fill |
| `fourthLevelElements` | `foregroundNeutralTertiary` | Legend dimmed, card category labels, funnel conversion rate |
| `background` | — | Label background, slicer dropdown, donut stroke, button fill, tooltip bg |
| `secondaryBackground` | `backgroundNeutral` | Table grid outline, shape map default, ribbon fill, disabled button |
| `tableAccent` | — | Table and matrix grid outline |

**⚠️ Dark themes**: ALL structural colors must be adjusted together.
Setting `background` to dark without adjusting `firstLevelElements` makes text invisible.
Additionally, the **filter pane** does NOT inherit from structural colors —
you must always explicitly set `outspacePane` and `filterCard` in
`visualStyles["*"]["*"]` when changing themes. See [re-theming.md § Dark Mode Authoring Checklist](re-theming.md#dark-mode-authoring-checklist)
for the complete checklist (filter pane, stylePreset override, fillCustom+id selector, objects vs VCO).

## 5. Text Classes (`textClasses`)

**4 primary classes** (editable in Customize Theme dialog):

| Class | Key | Default Font | Default Size | Used By |
|-------|-----|-------------|-------------|---------|
| General | `label` | Segoe UI | 10pt | Table/matrix values, slicer items |
| Title | `title` | DIN | 12pt | Axis titles, multi-row card title |
| Cards & KPIs | `callout` | DIN | 45pt | Card data labels, KPI indicators |
| Tab headers | `header` | Segoe UI Semibold | 12pt | Key influencers headers |

**8 documented derived classes** (auto-derived from primaries):

| Key | Derives From | Modification |
|-----|-------------|-------------|
| `largeTitle` | `title` | 14pt — visual title |
| `semiboldLabel` | `label` | Segoe UI Semibold — key influencers profile |
| `largeLabel` | `label` | 12pt — multi-row card data |
| `smallLabel` | `label` | 9pt — reference lines, slicer date range |
| `lightLabel` | `label` | Color from `secondLevelElements` — legend, button text, axis labels |
| `boldLabel` | `label` | Segoe UI Bold — matrix subtotals, table totals |
| `largeLightLabel` | `label` | `secondLevelElements` color, 12pt — card category, gauge labels |
| `smallLightLabel` | `label` | `secondLevelElements` color, 9pt — data labels, value axis labels |

Other `textClasses` names may appear in exported PBIR or undocumented schema
variants, but they are not documented in Microsoft's theme guidance. Do not
author them unless you have validated the current `reportThemeSchema.json` for
the target Desktop version.

**Format:**
```json
"textClasses": {
  "callout": { "fontSize": 45, "fontFace": "DIN", "color": "#252423" },
  "title":   { "fontSize": 12, "fontFace": "DIN", "color": "#252423" },
  "header":  { "fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#252423" },
  "label":   { "fontSize": 10, "fontFace": "Segoe UI", "color": "#252423" }
}
```

Properties: `fontFace` (string), `fontSize` (number, pt), `color` (hex string).
Optional: `"bold": true`.

## 6. Visual Styles (`visualStyles`)

Sets default formatting for any visual type — the central mechanism for
theme-driven appearance.

### Three-Level Hierarchy

```
visualStyles[Level 1: visual type][Level 2: style preset][Level 3: object name] → properties
```

| Level | Examples | Wildcard |
|-------|----------|----------|
| 1 — Visual type | `"barChart"`, `"tableEx"`, `"pivotTable"` | `"*"` = all types |
| 2 — Style preset | `"Bold"`, `"Minimal"`, `"Corporate"` | `"*"` = default (no preset) |
| 3 — Object name | `"legend"`, `"dataPoint"`, `"border"` | `"*"` = all objects |

**Resolution order** (first match wins):
1. `customTheme.visualStyles[exactType][activePreset][object]`
2. `customTheme.visualStyles[exactType]["*"][object]`
3. `customTheme.visualStyles["*"][activePreset][object]`
4. `customTheme.visualStyles["*"]["*"][object]`
5. `baseTheme.visualStyles[exactType]["*"][object]`
6. `baseTheme.visualStyles["*"]["*"][object]`
7. System defaults

Type-specific entries override wildcard entries at each level.

### Example — Universal + Type-Specific

```json
"visualStyles": {
  "*": {
    "*": {
      "title": [{
        "show": true,
        "fontFamily": "'Segoe UI Semibold'",
        "fontSize": 12,
        "fontColor": { "solid": { "color": "#333333" } }
      }],
      "background": [{
        "show": true,
        "color": { "solid": { "color": "#FFFFFF" } },
        "transparency": 0
      }],
      "border": [{
        "show": true,
        "color": { "solid": { "color": "#E0E0E0" } },
        "radius": 4,
        "width": 1
      }]
    }
  },
  "barChart": {
    "*": {
      "border": [{ "radius": 8 }],
      "legend": [{ "position": "Top" }]
    }
  }
}
```

### Encoding in visualStyles

Values use **theme encoding** (plain JSON), not PBIR expression wrappers:

```json
"show": true,
"fontSize": 12,
"position": "Top",
"fontColor": "#252423",
"gridlineColor": { "solid": { "color": "#E0E0E0" } }
```

**Color properties**: Some accept plain hex strings, others require
`{ "solid": { "color": "#hex" } }`. When in doubt, use the structured format.

### Object Names for visualStyles

Common objects available under `"*"` (all types):
`title`, `subTitle`, `background`, `border`, `dropShadow`, `visualHeader`,
`visualTooltip`, `lockAspect`, `general`, `padding`, `divider`, `spacing`

Per-visual-type objects (examples):
| Visual Type | Objects |
|-------------|---------|
| Column/Bar | `categoryAxis`, `valueAxis`, `legend`, `dataPoint`, `labels` |
| Line/Area | `categoryAxis`, `valueAxis`, `legend`, `dataPoint`, `labels`, `lineStyles`, `markers` |
| Table (`tableEx`) | `grid`, `columnHeaders`, `values`, `total`, `columnFormatting`, `stylePreset` |
| Matrix (`pivotTable`) | `grid`, `columnHeaders`, `rowHeaders`, `values`, `subTotals`, `grandTotal` |
| Slicer | `data`, `selection`, `header`, `items`, `slider` |
| Card | `labels`, `categoryLabels`, `wordWrap` |

Use `powerbi-report-author formatting list-objects <type>` for the full list per visual.

### The `$id` Property — Instance Discrimination

Some objects have multiple instances discriminated by `$id`:

```json
"filterCard": [
  { "$id": "Applied", "backgroundColor": { "solid": { "color": "#E8F0FE" } } },
  { "$id": "Available", "backgroundColor": { "solid": { "color": "#FFFFFF" } } }
]
```

This is the theme-level equivalent of PBIR's `"selector": { "id": "..." }`.
Both use PascalCase values (`"Applied"`, `"Available"`).

## 7. Style Presets

Style presets are named formatting bundles selectable per-visual.

### Theme-Side: Registration

Register presets in `visualStyles` at level 2:

```json
"visualStyles": {
  "columnChart": {
    "*": {
      "stylePreset": [{ "name": "Corporate Blue" }],
      "legend": [{ "position": "BottomCenter" }]
    },
    "Corporate Blue": {
      "legend": [{ "position": "Right", "fontColor": { "solid": { "color": "#003366" } } }]
    },
    "Minimal": {
      "legend": [{ "show": false }],
      "border": [{ "show": false }]
    }
  }
}
```

### Visual-Side: Selection

Each visual selects its preset via the `stylePreset` VCO (PBIR encoding):

```json
"visualContainerObjects": {
  "stylePreset": [{
    "properties": {
      "name": { "expr": { "Literal": { "Value": "'Corporate Blue'" } } }
    }
  }]
}
```

If no `stylePreset` VCO is present, the `"*"` (default) preset applies.

### Limitations
- Per-visual-type only — presets can't span visual types
- No UI dropdown for custom presets yet (built-in presets only)
- Preset names are arbitrary strings (title-case convention: `"Bold"`, `"Minimal"`)

## 8. ThemeDataColor Resolution

PBIR formatting can reference theme palette colors dynamically:

```json
{ "ThemeDataColor": { "ColorId": 0, "Percent": 0.4 } }
```

### Resolution Algorithm

1. Look up `dataColors[ColorId]` from the effective theme
2. Apply `shadeColor(baseColor, Percent)` in RGB space:

```
if Percent > 0 (tint toward white):
    channel = channel + (255 - channel) × Percent

if Percent < 0 (shade toward black):
    channel = channel × (1 + Percent)
```

Use `powerbi-report-author theme shade-color <hex> <percent>` to compute this:

```bash
powerbi-report-author theme shade-color "#118DFF" 0.4   # → #70BBFF (lighter)
powerbi-report-author theme shade-color "#118DFF" -0.4  # → #0A5599 (darker)
```

### Common Percent Values

| Percent | Use |
|---------|-----|
| `0` | Primary data colors (series, fills) |
| `0.4` | Container backgrounds from palette |
| `0.6` | Subtle backgrounds, secondary text |
| `0.8` | Very light pastel backgrounds |
| `-0.2` | Slightly darker text, emphasis borders |
| `-0.4` | Darker headers, stronger contrast |

### When to Use ThemeDataColor vs Literal

| Scenario | Use | Why |
|----------|-----|-----|
| Data series colors | `ThemeDataColor(N, 0)` | Auto-updates with theme |
| Backgrounds from palette | `ThemeDataColor(N, 0.4)` | Consistent, theme-adaptive |
| Brand colors that must NOT change | Literal `"'#FF6B35'"` | Theme-independent |
| Semantic colors (red=bad) | Literal hex | Meaning is absolute |
| Explicit per-measure `dataPoint.fill` with a `metadata` selector | Literal hex | `ThemeDataColor` in this position silently resolves to white or black — see [authoring.md Anti-Patterns](../authoring.md#anti-patterns-and-pitfalls) |

## 9. Theme Defaults for Page Objects

Themes can set defaults for page-level formatting objects via `visualStyles`.
The property names and structure are the same as described in
[page-formatting.md](page-formatting.md); the encoding differs (theme encoding,
not PBIR):

```json
"visualStyles": {
  "*": {
    "*": {
      "outspacePane": [{
        "backgroundColor": { "solid": { "color": "#FFFFFF" } },
        "foregroundColor": { "solid": { "color": "#252423" } },
        "titleSize": 12,
        "border": true,
        "borderColor": { "solid": { "color": "#E0E0E0" } },
        "checkboxAndApplyColor": { "solid": { "color": "#118DFF" } },
        "inputBoxColor": { "solid": { "color": "#FFFFFF" } }
      }],
      "filterCard": [
        { "$id": "Applied", "backgroundColor": { "solid": { "color": "#E8F0FE" } } },
        { "$id": "Available", "backgroundColor": { "solid": { "color": "#FFFFFF" } } }
      ],
      "background": [{
        "color": { "solid": { "color": "#FFFFFF" } },
        "transparency": 0
      }],
      "outspace": [{
        "color": { "solid": { "color": "#F3F2F1" } },
        "transparency": 0
      }]
    }
  }
}
```

See [page-formatting.md](page-formatting.md) for the full property lists of
these objects and PBIR examples.

## 10. Custom Icons

Define custom icons for icon-set conditional formatting:

```json
"icons": {
  "customFire": { "url": "https://example.com/fire.png", "description": "Fire indicator" },
  "customStar": { "url": "https://example.com/star.svg", "description": "Star rating" }
}
```

These become available in the conditional formatting dialog icon set picker.


## Re-theming & Dark Mode

See [re-theming.md](re-theming.md) for the re-theming workflow (color mapping,
bulk hex sweep, polarity gate), dark mode authoring checklist, and preventive
authoring patterns.

## Theme Authoring Best Practices

1. **Always set ALL structural colors together** for dark themes — partial changes
   create invisible text or clashing chrome
2. **Use `visualStyles["*"]["*"]`** for universal defaults, type-specific keys for overrides
3. **Test with multiple visual types** — wildcard `"*"` applies to all, including
   visuals you may not expect (e.g., `"values"` banding applies to any visual with
   a `values` object, not just tables)
4. **Use `{ "solid": { "color": "#hex" } }`** for color properties in visualStyles
   when unsure — it always works
5. **Validate with schema** — see [Schema Version](#schema-version) above for
   how to pick and reference the right `reportThemeSchema-<version>.json`.
   `powerbi-report-author validate` does not infer a schema version or expand bare filenames
   to GitHub URLs; if you want schema validation, set `"$schema"` to a full
   published HTTPS URL or a local schema file beside the theme JSON.
6. **Row banding via theme** — set `tableEx` and `pivotTable` specific values, not `"*"`,
   to avoid unexpected banding on non-table visuals (see
   [table.md § Row Banding](table.md#row-banding-table--matrix))

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Using PBIR expression wrappers in theme JSON | Theme uses plain JSON: `true`, `12`, `"#hex"` |
| Setting only `background` for dark theme | Also set `foreground`/`firstLevelElements` for text contrast |
| Wildcard `"*"."*"."values"` for row banding | Use `"tableEx"` / `"pivotTable"` to avoid affecting non-table visuals |
| Lowercase `"applied"` for filter card $id | Must be PascalCase: `"Applied"`, `"Available"` |
| Assuming dataColors merge with base theme | Custom `dataColors` fully replaces the base array |
| Forgetting `reportVersionAtImport` | Preserve as-is — PBI Desktop manages this field |
| Putting conditional formatting rules in theme JSON | Apply conditional formatting separately on individual visuals |
| Dark theme but table/matrix rows still white | See [§ Style Presets](#7-style-presets) and [re-theming.md § Dark Mode Checklist](re-theming.md#dark-mode-authoring-checklist) |
| Setting `visualStyles["slicer"]` for dark slicer text | Modern slicers use `filterSlicer` / `advancedSlicerVisual` — the legacy `"slicer"` key has no effect. Add type-specific entries for both modern types |
| Shape text invisible after dark theme switch | Shapes relying on inherited foreground have no explicit `fontColor` — the bulk hex sweep can't add a property that didn't exist. Add explicit `text.fontColor` to every shape with `text.show: true` |
