# Formatting & Theming Overview

> **Read this first** before editing any visual appearance in a PBIR report.
> It explains the cascade model, value encoding rules, and which file to read next.

## Formatting Cascade

Power BI resolves formatting in a layered cascade (highest priority wins):

| Priority | Layer | File | Encoding | Instructions |
|----------|-------|------|----------|--------------|
| 1 (highest) | Conditional formatting (FillRule, rules) | `visual.json` objects | PBIR expressions | conditional-formatting.md (see `conditional-formatting.md`) |
| 2 | Per-visual objects (chart colors, labels, axes, data points, row banding) | `visual.json → visual.objects` | PBIR expressions | formatting.md (see `formatting.md`) |
| 3 | Visual container objects | `visual.json → visual.visualContainerObjects` | PBIR expressions | formatting.md (see `formatting.md`, section `visual-container-objects-vco`) |
| 4 | Page objects (canvas background, wallpaper, page background images, filter pane (`outspacePane`), filter cards (`filterCard`)) | `page.json → objects` | PBIR expressions | page-formatting.md (see `page-formatting.md`); filter-pane.md (see `filter-pane.md`) |
| 5 | Custom theme (visualStyles - type-specific; dataColors; textClasses; style presets) | `theme.json → visualStyles[type]["*"][obj]` | Theme encoding | theming.md (see `theming.md`, section `6-visual-styles-visualstyles`) |
| 6 | Custom theme (visualStyles - wildcard) | `theme.json → visualStyles["*"]["*"][obj]` | Theme encoding | theming.md (see `theming.md`, section `6-visual-styles-visualstyles`) |
| 7 | Base theme | `SharedResources/BaseThemes/` | Theme encoding | theming.md (see `theming.md`) |
| 8 (lowest) | System defaults | Built into PBI Desktop | — | No skill-side file; verify rendered defaults in Desktop |

A property set at layer 2 overrides the same property at layers 3–8.
When a cascade result matters visually, verify it through
the host-specific workflow in preview.md (see `preview.md`).

> **⚠️ Theme changes require sweeping all cascade layers.** The theme file
> only controls layers 5–6. Hardcoded colors in `page.json` (layer 4) and
> `visual.json` (layers 2–3) override the theme and must be updated in the
> same operation. See
> re-theming.md § Re-theming an Existing Report (see `re-theming.md`, section `re-theming-an-existing-report`).

## Static Property Value Encoding — Three Formats

**Critical**: Theme files and PBIR files encode the same properties differently.
Using the wrong encoding is the #1 formatting error.

| Value | Theme JSON (plain) | Theme visualStyles (hybrid) | PBIR (expression-wrapped) |
|-------|--------------------|-----------------------------|---------------------------|
| Boolean | `true` | `true` | `{"expr":{"Literal":{"Value":"true"}}}` |
| Number | `12` | `12` | `{"expr":{"Literal":{"Value":"12D"}}}` |
| Integer | `3` | `3` | `{"expr":{"Literal":{"Value":"3L"}}}` |
| String | `"dotted"` | `"dotted"` | `{"expr":{"Literal":{"Value":"'dotted'"}}}` |
| Color | `"#118DFF"` | `"#118DFF"` or `{"solid":{"color":"#118DFF"}}` | `{"solid":{"color":{"expr":{"Literal":{"Value":"'#118DFF'"}}}}}` |
| Theme color | — | — | `{"solid":{"color":{"expr":{"ThemeDataColor":{"ColorId":0,"Percent":0}}}}}` |

**Rules:**
- **theme.json** top-level keys (dataColors, good/bad, structural): plain JSON
- **theme.json** `visualStyles` properties: plain JSON, but some color props require `{"solid":{"color":"#hex"}}`
- **visual.json** and **page.json** objects: always PBIR expression wrappers
- Use `powerbi-report-author expr encode --kind <t> <v>` to generate PBIR
  expression encodings; use `powerbi-report-author theme encode --kind <t> <v>`
  for theme-style values
- Use `powerbi-report-author expr decode '<json>'` to inspect existing values
- Use `powerbi-report-author formatting describe-property <type> <object> <property>`
  to look up the expected `type`/`kind` (or
  `powerbi-report-author formatting search <type> <regex>` to find a property
  across all objects on a visual)

## Selector Types (Quick Reference)

Selectors control which data a formatting entry targets. Five types exist,
in descending priority:

| Type | Syntax | Use Case |
|------|--------|----------|
| **data** (scope identity) | `"data": [{"scopeId": {...}}]` | Color a specific category value (e.g., "Electronics") |
| **data** (wildcard) | `"data": [{"dataViewWildcard": {"matchingOption": N}}]` | All instances (0), instances only (1), totals only (2) |
| **metadata** | `"metadata": "Table.Field"` | Target a specific measure/column |
| **id** | `"id": "default"` | User-defined instance (cards, filter cards) |
| **none** (static) | *(no selector)* | Base formatting — lowest priority |

Within each priority row, **first match in array order wins**.

See `references/authoring/formatting.md` for full selector patterns and examples.
