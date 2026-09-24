# Theme Authoring — theme.json Reference - Part 2

## Contents

- [8. ThemeDataColor Resolution](#8-themedatacolor-resolution)
  - [Resolution Algorithm](#resolution-algorithm)
  - [Common Percent Values](#common-percent-values)
  - [When to Use ThemeDataColor vs Literal](#when-to-use-themedatacolor-vs-literal)
- [9. Theme Defaults for Page Objects](#9-theme-defaults-for-page-objects)
- [10. Custom Icons](#10-custom-icons)
- [Re-theming & Dark Mode](#re-theming--dark-mode)
- [Theme Authoring Best Practices](#theme-authoring-best-practices)
- [Common Pitfalls](#common-pitfalls)


Continuation of `theming.md`. Open this file directly from the skill reference index.

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
| Explicit per-measure `dataPoint.fill` with a `metadata` selector | Literal hex | `ThemeDataColor` in this position silently resolves to white or black — see SKILL.md Anti-Patterns (see `../authoring.md`, section `anti-patterns-and-pitfalls`) |

## 9. Theme Defaults for Page Objects

Themes can set defaults for page-level formatting objects via `visualStyles`.
The property names and structure are the same as described in
page-formatting.md (see `page-formatting.md`); the encoding differs (theme encoding,
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

See page-formatting.md (see `page-formatting.md`) for the full property lists of
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

See re-theming.md (see `re-theming.md`) for the re-theming workflow (color mapping,
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
5. **Validate with schema** — see Schema Version above for
   how to pick and reference the right `reportThemeSchema-<version>.json`.
   `powerbi-report-author validate` does not infer a schema version or expand bare filenames
   to GitHub URLs; if you want schema validation, set `"$schema"` to a full
   published HTTPS URL or a local schema file beside the theme JSON.
6. **Row banding via theme** — set `tableEx` and `pivotTable` specific values, not `"*"`,
   to avoid unexpected banding on non-table visuals (see
   table.md § Row Banding (see `table.md`, section `row-banding-table--matrix`))

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
| Dark theme but table/matrix rows still white | See § Style Presets and re-theming.md § Dark Mode Checklist (see `re-theming.md`, section `dark-mode-authoring-checklist`) |
| Setting `visualStyles["slicer"]` for dark slicer text | Modern slicers use `filterSlicer` / `advancedSlicerVisual` — the legacy `"slicer"` key has no effect. Add type-specific entries for both modern types |
| Shape text invisible after dark theme switch | Shapes relying on inherited foreground have no explicit `fontColor` — the bulk hex sweep can't add a property that didn't exist. Add explicit `text.fontColor` to every shape with `text.show: true` |
