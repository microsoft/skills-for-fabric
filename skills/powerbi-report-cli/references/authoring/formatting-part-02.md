# Formatting Patterns - Part 2

Continuation of `formatting.md`. Open this file directly from the skill reference index.

## Shape Visual Formatting

For shape-object discovery, available shapes, and formatting, see
`shape.md` § Available Shapes and Formatting (see `shape.md`, section `available-shapes-and-formatting`).

## Line & Marker Formatting (lineStyles / markers)

For line stroke properties (width, style, dash cap, line join, interpolation),
marker properties (shape, size, border, rotation), and the per-series metadata
selector pattern for line/area/scatter charts, see
`cartesian.md` § lineStyles (see `cartesian.md`, section `linestyles--line-specific`) and
`cartesian.md` § markers (see `cartesian.md`, section `markers--marker-styling`).

## Row Banding (Table & Matrix)

For row banding (`backColorPrimary` / `backColorSecondary`), the full
table/matrix region map (`values`, `columnHeaders`, `rowHeaders`, `total`,
`subTotals`), the **critical style preset rule** (`stylePreset` must be set to
`'None'` for custom row colors to render), and the `backColor` vs
`backColorPrimary` distinction, see
`table.md` § Row Banding (see `table.md`, section `row-banding-table--matrix`).

## Page-Level Formatting (`page.json` objects)

For canvas background, wallpaper (`outspace`), and page-level background
images, see `page-formatting.md` (see `page-formatting.md`). For filter pane
(`outspacePane`) and filter card states (Applied / Available), see
`filter-pane.md` (see `filter-pane.md`).

## Background Images — Routing

When the user requests a "background image," route based on the target:

| User says | Target | Reference |
|-----------|--------|-----------|
| "background image" while creating/modifying a chart visual | `visual.objects.plotArea.image` | `image.md` § Plot Area Background Image (see `image.md`, section `plot-area-background-image-plotareaimage`) |
| "page background image" / "canvas background" | `page.json → objects.background.image` | `page-formatting.md` § Background Images (see `page-formatting.md`, section `background-images`) |
| "background image" with no visual context | Ask the user to clarify — page canvas or visual plot area | — |

**⚠️ Both visual plot areas and page backgrounds use the nested `image.image` structure** (`image.image.name`, `image.image.url`, `image.image.scaling`). A flat `image.name/url/scaling` will silently fail to render.

For the `image` object on image visuals themselves (border, background,
corner-radius routing between `objects.image` and VCOs), see
`image.md` § Image Formatting (see `image.md`, section `image-formatting-objectsimage`).

## References

- `formatting-overview.md` (see `formatting-overview.md`) — cascade resolution order (visual → VCO → page → custom theme → base theme → defaults), encoding rules, and the Theme JSON vs PBIR encoding comparison table.
- `theming.md` (see `theming.md`) — `theme.json` authoring: dataColors, textClasses, visualStyles, dark-mode checklist.
- `conditional-formatting.md` (see `conditional-formatting.md`) — gradients, rules, field values, and the six conditional formatting types.
- `table.md` (see `table.md`), `shape.md` (see `shape.md`), `cartesian.md` (see `cartesian.md`), `image.md` (see `image.md`), `card.md` (see `card.md`) — visual-type-specific formatting details.
