# Visual Design Cookbook - Part 2

## Contents

  - [Slicers](#slicers)
  - [Temporal slicer decision matrix](#temporal-slicer-decision-matrix)
  - [Textbox (page titles, annotations)](#textbox-page-titles-annotations)
  - [Shape (`shape`)](#shape-shape)
  - [Scatter (`scatterChart`)](#scatter-scatterchart)
  - [Waterfall (`waterfallChart`)](#waterfall-waterfallchart)
  - [Treemap (`treemap`)](#treemap-treemap)
  - [Conditional Formatting — MANDATORY](#conditional-formatting--mandatory)


Continuation of `visual-cookbook.md`. Open this file directly from the skill reference index.

### Slicers

2-3 slicers per page maximum. Pick dimensions that control the most visuals
on the page — if 3 charts use Weight Class and 2 use Year, those are your
slicers. Avoid slicing by the same field on a chart's category axis.

**Type selection:**

| Data | Type | `visualType` |
|------|------|-------------|
| Categorical ≤10 values | Button/tile | `advancedSlicerVisual` |
| Categorical 10-50 | List | `listSlicer` |
| Categorical >50 | Dropdown | `slicer` (mode: Dropdown) |
| Annual or period selector | Dropdown or tile | `slicer` (mode: Dropdown) or `advancedSlicerVisual` |
| True date range | Date picker | `slicer` (mode: Between) |
| Hierarchy | Tree | `listSlicer` |

### Temporal slicer decision matrix

Choose the slicer from the page question and data grain, not from the mere
presence of a full-date column.

| Signal | Recommended slicer | Rationale |
|---|---|---|
| Executive page, annual grain, ≤10 years | Year dropdown or year tile | Compact, reliable, and matches scan-first behavior |
| User needs to compare discrete periods (e.g., 2020 vs 2023) | Year/month dropdown with multi-select | `Between` implies continuous ranges, not discrete comparisons |
| Month/quarter reporting with 12-36 periods | Period dropdown or relative date | Keeps the header compact while exposing current period |
| Analyst needs arbitrary day/month range exploration | Full-date `Between` | Range selection is the task |
| Date column is an integer key/text key or did not render as a date picker | Dropdown on Year/Period | `Between` requires a renderable Date/DateTime field |
| Many dates but no need for arbitrary ranges | Relative date or period dropdown | Avoids oversized controls for low-value precision |

**Placement** (choose by slicer count — see `references/design/layout.md`):

| Count | Position | Layout impact |
|---|---|---|
| 1–3 | Inline with title row (right side) | No width penalty — full chart width preserved |
| 4+ | Vertical filter rail (200–240px left) | F-pattern, justified when slicers fill the column |

Never use a vertical rail for ≤3 slicers — it wastes 70%+ of the
column height as dead space and unnecessarily narrows all content.
Never place slicers in the top-left corner — that's for the page title.

#### Dropdown Slicer (`slicer`, mode: Dropdown)

The default choice — compact, searchable, handles any cardinality.

**Sizing** (proportional to canvas):
- Height: follow the slicer sizing guidance in the `authoring` mode exactly; default dropdown is
  `60 + top_padding + bottom_padding`, snapped to the 8px grid. Do not shrink
  to 48px or 8pt to make a tight layout work.
- Width: ~12% of page width (about 230px on FHD, 160px on 1280×720). Use ~10%
  for short labels like "Year" or "Stance".

**Two styling variants:**

| | **Standard (fill)** | **Light (no fill)** |
|---|---|---|
| Background | White `#FFFFFF` | None |
| Border | `#E8E8E8`, radius=8 | `#E8E8E8`, radius=8 |
| Use for | Top strip, inline with cards | Sidebar rail |

Both share border radius=8 and color=#E8E8E8, matching card visuals.

**Theme handles** (via `visualStyles.slicer` in base.json):
- `header`: body-lg font (10pt Semibold), outlineStyle=0 (no header border)
- `items`: body font (9pt Regular), outlineStyle=0, padding=2

**Per-visual must set:**
- `header.text` — display name ("Weight Class" not "weight_class_name")
- `data.mode` — "Dropdown" (or Basic, Between, etc.)
- VCO `background`, `border`, `padding` — for fill vs light variant

#### Date Between Slicer (`slicer`, mode: Between)

Use for temporal filtering only when arbitrary date-range exploration is part
of the page question and the bound field is a renderable Date/DateTime column.
For executive dashboards with yearly or quarterly grain, prefer a compact
Year/Period dropdown or tile.

**Sizing**:
- Inline with title: w=216; height is `60 + top_padding + bottom_padding`,
  snapped to the 8px grid. Dates render side-by-side at this width.
- Vertical rail: w=200; height is `84 + top_padding + bottom_padding` because
  dates stack vertically at this width.
- Authoring must use the exact slicer sizing formula from the `authoring` mode
  after theme/VCO padding is known.

**Styling variants**: same Fill and Light as Dropdown Slicer (see table above).

**Theme handles** (via `visualStyles.slicer` in base.json — shared with dropdown):
- `header`: 10pt Semibold, outlineStyle=0
- `date`: 9pt font for date picker text

**Per-visual must set:**
- `data.mode` — "Between"
- `header.text` — "Date Range" or similar
- VCO `background`, `border`, `padding` — for fill vs light variant

**When to prefer Dropdown/Tile over Between:**
- Executive or scan-first page with annual/quarterly grain
- Integer/text year-month key or date picker did not render
- User expects multi-select (e.g., compare 2020 vs 2023)
- ≤30 distinct values where a list is scannable

### Textbox (page titles, annotations)

**When to use**: Descriptive titles, section labels, body prose in narrative, footnotes.

**Design rules**:
- Page title (H1): 20pt SemiBold, dark navy (#252423), top-left, width ≥600px
- Section dividers: use `shape` (rectangle) not textbox — textbox has a ~24px minimum height
- Annotations: 10-11pt Regular, positioned near the chart element they reference
- Rich text: use `paragraphs[].textRuns[]` for inline bold, color, sizing
- Dynamic text: bind to a measure for data-driven titles ("Revenue is {[Revenue]} this quarter")
- Footer text: 8-9pt, muted grey (#605E5C), bottom of page, source + refresh timestamp

**⚠️ Textbox height — avoid scrollbar**: A scrollbar appears when the
textbox height is too small for the font size. Use this formula:

```text
h_min = max(18, ⌈fontSize_pt × 25/16⌉) + padding_top + padding_bottom
```

| Font Size | Min Height (no padding) | With 8+8 padding |
|-----------|------------------------|------------------|
| 10pt | 18px | 34px |
| 14pt | 22px | 38px |
| 20pt | 32px | 48px |
| 24pt | 38px | 54px |
| 28pt | 44px | 60px |

- Floor of 18px regardless of font size
- VCO border adds ZERO pixels (rendered outside bounds)
- Font family and bold/regular do NOT change the threshold
- Set VCO padding to 0 if you want the tightest possible fit

**PBIR note**: `paragraphs` is a native JSON array — never stringify it

### Shape (`shape`)

**When to use**: Decorative dividers, section backgrounds, annotation arrows, call-out boxes.

**Design rules**:
- Divider line: rectangle, h=2, w=full page width, fill=#E0E0E0 — separates page sections
- Section background: rounded rectangle, low opacity fill (#F5F5F5), z-ordered BEHIND the visuals it groups
- Annotation arrow: use arrowhead geometry, point at the chart element being called out
- Decorative shapes are acceptable when they support the report's tone; keep data-bearing areas legible
- Shapes don't have a 24px minimum like textboxes — use them for thin dividers

**Formatting notes**: Shape visual uses `id` selectors (not metadata/scope). `fill`, `outline`, `text`, `shadow`, `glow` MUST have `"selector": { "id": "default" }`. The `shape` object (tileShape/geometry) needs NO selector.

### Scatter (`scatterChart`)

**When to use**: Relationship between two continuous variables. Correlation, clusters, outliers.

**Design rules**:
- X and Y axes: always labeled with measure name and unit
- Bubble size role: use sparingly (3rd variable) — area encodes poorly (Stevens' law)
- Data labels: show on outlier points only, not all (visual clutter)
- Quadrant reference lines: add horizontal + vertical `referenceLine` to divide into performance quadrants
- Color by category: use legend for identity, not for magnitude
- Play axis: enable for time-lapse animation when a date dimension exists

### Waterfall (`waterfallChart`)

**When to use**: Sequential additive contribution — how does a total build up from
components? Variance bridges (start → adjustments → end).

**Design rules**:
- Use the theme's sentiment colors for increase (good=#1AAB40) and decrease (bad=#D64554)
- Total bar: distinct color (neutral blue #0072B2 or grey)
- Data labels: always on — the reader needs the exact numbers
- Category labels: name each step clearly
- Connector lines: show to maintain the visual bridge

### Treemap (`treemap`)

**When to use**: Part-to-whole when there are >10 categories. NOT for comparison (use bar chart).

**Design rules**:
- Limit to 1 grouping level unless the hierarchy is the point
- Color: use the categorical palette so each rectangle is distinct
- Data labels: show category name + value/percentage inside each rectangle
- Size encodes magnitude — the biggest rectangle is the dominant category

### Conditional Formatting — MANDATORY

Use conditional formatting when it reinforces the page's main comparison,
threshold, or exception pattern.

| Technique            | Use on                 | Effect                                                                                                                                                |
| -------------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Per-series color** | Bar/column charts      | Each category bar gets a distinct color when category identity matters |
| **Threshold color**  | KPI cards              | Background or font color changes based on good/neutral/bad thresholds                                                                                 |
| **Data bars**        | Table numeric columns  | In-cell horizontal bars show magnitude at a glance                                                                                                    |
| **Icon sets**        | Table status columns   | Pass/fail or good/warn/bad status becomes scannable                                                                                                   |
| **Color gradient**   | Matrix cells, heatmaps | Min→mid→max color scale reveals patterns                                                                                                             |
| **Highlight + grey** | Any chart              | One series in accent color, rest in #BDBDBD — draws the eye to the insight                                                                            |

**The "all bars same color" problem**: single-series bar charts can render
every bar with the same default color. If category contrast matters, specify
per-category colors or a sequential gradient in the design brief and let
authoring handle the mechanics.
