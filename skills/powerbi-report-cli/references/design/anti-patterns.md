# Anti-Patterns — The Dashboard Slop Catalog

## Why This Catalog Exists

LLMs producing dashboard layouts gravitate toward a set of attractor states —
generic, cluttered, misleading designs that _look_ complete but fail users.
This is the **refusal list**: when the agent detects these patterns in its own
output, it must stop and fix before emitting.

This catalog is advisory. It assigns severity levels but **never blocks** output.
Strong warnings surface to the user for explicit confirmation.

---

## Cluster 1 — Visual Noise (Chartjunk)

| Anti-Pattern | Why It Fails | Do Instead | PBI Tell |
|---|---|---|---|
| **3D effects** | Perspective distortion destroys precision; occludes data | Flat 2D equivalent | Any `3D` visual type selected |
| **Drop shadows on visuals** | Pure decoration; adds visual weight without information | Remove all shadows; rely on whitespace for separation | `shadow` enabled in visual formatting |
| **Saturated background fills** | Competes with data ink; reduces text contrast | White or near-white canvas (`#FFFFFF`, `#F9F9F9`) | `background.color` is a saturated hue |

---

## Cluster 2 — Misleading Encoding

| Anti-Pattern | Why It Fails | Do Instead | PBI Tell |
|---|---|---|---|
| **Truncated bar baseline** | Bars starting at non-zero exaggerate differences by 2-10× | Always start bars at zero; use dot plot if range is narrow | `valueAxis.start` ≠ 0 on bar chart |
| **Dual y-axis chart** | Implies correlation by scale manipulation; easy to lie with | Two separate charts, shared x-axis, stacked vertically | `secondaryYAxis` enabled |
| **Pie chart >5 slices** | Angle encoding is imprecise; small slices become invisible | Sorted horizontal bar chart | Pie/donut with >5 data points |
| **Stacked bar for mid-stack comparison** | Only bottom and top segments have a common baseline | Grouped bar or small multiples | Stacked bar with >2 segments compared across categories |
| **Unshared small-multiple axes** | Different scales make comparison impossible — defeats the purpose | Force identical axis range on all multiples | Auto-scale per tile |
| **Gauge / speedometer** | Uses large area for one number; no trend; arbitrary dial range | Card + sparkline or bullet graph | Gauge visual type |
| **Radar / spider chart** | Area distortion; axis order changes shape; unreadable | Grouped bar or parallel coordinates | Radar visual type |
| **Area chart for non-stacked data** | Fill implies volume/accumulation that may not exist | Line chart for trends; area only for stacked composition | `areaChart` for single series |

---

## Cluster 3 — Cognitive Overload

| Anti-Pattern | Why It Fails | Do Instead | PBI Tell |
|---|---|---|---|
| **KPI carpet-bombing** | 8+ cards in a row; nothing stands out; reader skips all | 3–4 KPIs max; pick the ones that drive decisions | >6 card visuals on one page |
| **12+ visuals on a page** | Exceeds working memory; user scans nothing carefully | 5–7 visual groups; use drill-through for depth | Visual count >12 on single page |
| **Alert fatigue** | Everything highlighted = nothing highlighted | Reserve red/amber for actionable exceptions only | >3 conditional-format rules using red |
| **Embedded detail matrix on exec page** | Executives scan, not read; a 50-row matrix wastes their time | Summary KPIs on exec page; matrix on drill-through detail page | Matrix with >10 rows on a page with cards |
| **Wall of slicers** | 5+ slicers consume space and paralyze with choice | 2–3 key slicers visible; rest in filter pane or collapsible panel | >4 slicer visuals on one page |
| **Wrong date slicer grain** | Full-date `Between` picker used for yearly executive filtering; control may not render and adds precision users do not need | Match slicer to grain: Year/Period dropdown or tile for annual/quarterly executive pages; full-date `Between` only for renderable Date/DateTime range exploration | Executive page with yearly data but `slicer_type: between` on full-date key |
| **Slicer sizing shortcut** | Shrinking slicer height/font hides clipping instead of solving layout; dropdown/date chrome still needs space | Follow the slicer sizing formula from the `authoring` mode and enlarge the reserved band/rail | Slicer height near 48px, 8pt text, or clipped lower row |
| **Multi-page report without navigation** | Users don't discover pages beyond the first | Add page navigator or button-based navigation | >3 pages with no navigator or nav buttons |
| **Variant default-bias / uniform-variant pages** | Picking layout variant **A** on every page — or any single variant uniformly across same-archetype pages — without consulting the selection table. Produces interchangeable, templatized reports that ignore each page's data shape | Walk the `Layout Variants` selection table in the archetype file *per page*, using each page's own data signals (KPI count, slicer count, viewing distance, comparison shape, narrative structure). Record `variant_rationale` per page. Same-archetype reports should rotate variants where data supports it; use `references/design/archetype-composition.md` for cross-page rotation guidance | Every page in a multi-page report has the same `layout_variant`; or `variant_rationale` is missing / generic across pages |
| **Mono-archetype report** | Copy-pasting page 1's archetype to pages 2-N instead of routing each page independently. A 4-page report covering distinct subject areas gets shipped with all 4 pages using the same archetype because the agent never re-walked the router after page 1. Pages all look the same regardless of audience/purpose differences | Re-walk the archetype decision for **every** page using *that page's* audience, purpose, and cadence. Multi-domain "cover everything" requests almost always decompose into 3-4 different archetypes (Executive landing + Comparative ranking + Analytical exploration + Narrative timeline). Use `references/design/archetype-composition.md` for common multi-archetype compositions | 3+ pages all share one archetype; or every page's `archetype` field equals page 1's |
| **Silent-guess on a vague prompt** | Receiving a prompt that's missing audience, purpose, page count, or filtering depth — and producing a design brief anyway based on a default assumption. The user gets a templatized "make a report about X" output that doesn't match their actual need | Treat missing audience, purpose, page count, or filtering depth as vagueness. Stop and offer 2–3 named, concrete options (each referencing a specific archetype + variant combination, in user-facing language). Only after the user picks, or after two clarification rounds with a documented assumption, proceed to design | Brief has no record of clarification; prompt was 1-line broad ("build a dashboard for X") and brief jumps straight to layout |
| **Mandatory archetype component fill** | Treating every box in an archetype wireframe as required creates redundant cards/callouts that do not answer a new question | Treat variant zones as advisory; drop or repurpose any component without `insight_basis` / `callout_value_basis` | Callout repeats the same absolute measure as the adjacent chart |

---

## Cluster 4 — Color Misuse

| Anti-Pattern | Why It Fails | Do Instead | PBI Tell |
|---|---|---|---|
| **Rainbow categorical** on ordered data | No perceptual order; readers can't decode high vs low | Sequential single-hue ramp (Blues, viridis) | `dataColors` with rainbow hues on a sorted dimension |
| **Categorical palette on ordinal data** | Distinct hues imply no order; misleads on ranked data | Sequential or diverging palette | Categorical colors assigned to ordered field |
| **Red/green as sole signal** | 8% of males are red-green CVD; information invisible | Add icon + text label alongside color | Red and green used without secondary channel |
| **Low-contrast labels** | <4.5:1 body-text ratio; unreadable on projectors and low-quality screens | Minimum `#767676` on white for body text | Text color with contrast ratio <4.5:1 |
| **Semantic color flip** | Green=bad violates universal convention; confuses everyone | Respect standard semantics; never invert | `good` theme color mapped to a negative outcome |
| **Pastel for critical status** | Light pink doesn't signal urgency; fails to grab attention | Saturated red for critical; pastel only for context/background | Conditional format using pastel for "critical" threshold |
| **>8 categorical hues** | Colors become indistinguishable; cognitive overload | Group tail categories into "Other"; limit to 7–8 | `dataColors` with >8 entries actively used |

---

## Cluster 5 — Interactivity Theater

| Anti-Pattern | Why It Fails | Do Instead | PBI Tell |
|---|---|---|---|
| **Headline behind a click** | Primary insight invisible until interaction | Show insight on page load; interactions reveal depth | Key metric visible only via drill-through or bookmark |
| **Invisible slicer state** | User can't tell what's filtered; data appears wrong/incomplete | Show active filter indicators; use slicer headers | Slicers with hidden headers or no default label |
| **Drill without breadcrumb** | User gets lost; can't return to overview | Always add back button; show drill path in page subtitle | Drill-through page without back button |
| **Bookmark overload** | >10 bookmarks become unmanageable; states conflict | 5–8 bookmarks max; clear, descriptive names | >10 bookmarks defined |
| **Slicer in prime real estate** | Top-left position wasted on controls, not insight | Slicers in filter strip, right rail, or collapsible panel | Slicer visual at position x<200, y<100 |
| **Auto-cycling carousel** | Users can't control pace; miss data; a11y violation | Static views with manual next/prev buttons | Timer-driven bookmark cycling |

---

## Cluster 6 — Archetype Mismatch

| Anti-Pattern | Why It Fails | Do Instead | PBI Tell |
|---|---|---|---|
| **Executive page with 30 visuals** | Executives scan for 15 seconds; 30 visuals need 15 minutes | 4–6 visual groups; cards + 1 hero chart | Archetype=exec + visual count >10 |
| **Operational without timestamp** | Users can't assess data freshness; stale data = wrong decisions | Show "Last refreshed: {time}" in footer on every ops page | No timestamp or refresh indicator on operational page |
| **Analytical without export/drill** | Analysts need to dig; no drill-through = dead end | Enable drill-through, export, personalize visuals | Archetype=analytical + no drill-through pages |
| **Narrative without thesis** | Story pages without a headline are just data dumps | Every narrative page leads with a finding statement | Narrative page without text visual stating insight |
| **Default "All" on large model** | Loads millions of rows on first view; slow, meaningless overview | Pre-filter to recent period or top-N by default | No default slicer selection + large dataset |
| **Comparative with unsynchronized slicers** | Comparing A vs B but slicers don't apply equally | Use sync slicers across all compared pages/visuals | Comparative layout with independent slicer states |

---

## LLM-Specific Failure Modes

Common mistakes LLMs make when generating PBI report definitions:

| Failure Mode | Description | Fix |
|---|---|---|
| **Clustered bar for everything** | Default chart choice regardless of question type | Consult the chart selection decision matrix |
| **Ignoring small multiples** | Uses multi-series line or stacked bar instead of small multiples for comparison | Use small multiples when comparing >3 categories |
| **One line chart per measure** | Every KPI gets its own line chart; no hierarchy or grouping | Combine related measures; use cards for single values |
| **Missing sortBy** | Bar charts left in alphabetical order | Apply descending sort on the value measure |
| **Ignoring numeric alignment** | Proportional-looking figures or left-aligned numbers in comparison tables/matrices | Use tabular-looking fonts where available, right-align numeric columns, and apply consistent number formatting |
| **Skipping alt text** | Alt text field left empty on every visual | Write insight-driven alt text for every visual |
| **Hardcoding hex colors** | Inline `#FF0000` instead of theme reference | Use theme `dataColors` and sentiment keys |
| **Six font sizes** | Each visual gets a different type size | Follow the 4-tier type ramp |
| **Pixel drift** | Positions not on 8px grid; edges misaligned | Snap all x, y, width, height to multiples of 8 |
| **Title as chart type** | "Bar Chart" or "Line Chart" as visual title | Title states the insight: "Sales declined 8% in Q4" |

---

## Detection Heuristics

Automated and semi-automated checks to catch anti-patterns:

| # | Check | What to Look For | Severity |
|---|---|---|---|
| 1 | **Hue count** | >8 distinct hues in `dataColors` actively rendered | warn |
| 2 | **Dual axis** | `secondaryYAxis` enabled on any visual | strong-warn |
| 3 | **Card count** | >6 card visuals on a single page | warn |
| 4 | **Bar baseline** | `valueAxis.start` ≠ 0 on bar or column chart | strong-warn |
| 5 | **Pie slice count** | Pie or donut with >5 data points in field | warn |
| 6 | **Visual density** | >12 visuals on a single page | warn |
| 7 | **Pixel grid** | Any `position.x`, `y`, `width`, `height` not divisible by 8 | info |
| 8 | **Contrast ratio** | Any text/background pair below 4.5:1 | strong-warn |
| 9 | **Alt text** | Alt text field empty on any non-decorative visual | warn |
| 10 | **Inline hex** | Hardcoded hex color not referencing theme | info |
| 11 | **Freshness indicator** | Operational page missing refresh timestamp | warn |
| 12 | **Ramp bloat** | >4 distinct `fontSize` values across visual titles/labels | info |

---

## Severity Model

| Level | Label | Meaning | Agent Behavior |
|---|---|---|---|
| `info` | Informational | Stylistic concern; may be intentional | Log internally; do not surface unless asked |
| `warn` | Warning | Likely unintentional; surface to user | Surface in review summary; suggest fix |
| `strong-warn` | Strong Warning | High risk of misleading or inaccessible output | Recommend explicit user confirmation before proceeding |

**Important**: This system is advisory only. It never blocks output or refuses to generate.
The agent surfaces findings and recommendations; the user decides.

---

## Remediation Quick-Reference

For each detected anti-pattern, the recommended fix action:

| Anti-Pattern Detected | Immediate Fix | Time to Fix |
|---|---|---|
| 3D visual | Replace with flat 2D equivalent | 1 min |
| Truncated baseline | Set `valueAxis.start: 0` | 30 sec |
| Dual axis | Split into two visuals, stack vertically | 5 min |
| Pie >5 slices | Replace with sorted horizontal bar | 3 min |
| >12 visuals | Move detail to drill-through page | 10 min |
| >8 colors | Group tail categories into "Other" | 5 min |
| Missing alt text | Write insight-driven text per template | 2 min/visual |
| Pixel drift | Snap x/y/w/h to multiples of 8 | 1 min/visual |
| Rainbow on sequential | Replace with single-hue sequential ramp | 3 min |
| Missing timestamp | Add "Last refreshed" text box in footer | 2 min |
| Hardcoded hex | Move colors to theme JSON | 5 min |
| Ramp bloat (>4 sizes) | Standardize to 4-tier type ramp | 5 min |
| Unsorted bars | Apply descending sort by value measure | 30 sec |
| Gauge | Replace with card + sparkline | 3 min |
| Slicer in top-left | Move to filter strip or right rail | 2 min |
| Bookmark overload | Consolidate to ≤8; delete redundant states | 10 min |
| No navigation | Add page navigator or button navigation | 5 min |
| Semantic color flip | Correct to standard green=good/red=bad | 2 min |

---

## Pre-Publish Review Workflow

Run these checks in order before delivering any report:

```text
1. LAYOUT CHECK
   □ Visual count ≤ 7 groups per page
   □ All positions on 8px grid
   □ Consistent gutters (16px or 24px)
   □ Page margins ≥ 24px all sides
   □ Title/header/breadcrumb height matches layout contract (~72px FHD / ~48px 1280x720)

2. COLOR CHECK
   □ ≤ 8 categorical hues
   □ No rainbow on ordered data
   □ All text passes WCAG contrast (4.5:1 body, 3:1 large)
   □ No red/green as sole signal
   □ CVD simulation passes
   □ All colors from theme (no inline hex)

3. TYPOGRAPHY CHECK
   □ ≤ 4 distinct font sizes
   □ Right-align numeric columns; use tabular-looking digits where comparison matters
   □ Consistent number formatting across pages
   □ No text below 8pt

4. CHART CHECK
   □ Every chart answers a stated question
   □ Bars start at 0
   □ No dual axes
   □ No pie with >5 slices
   □ All bar charts sorted by value (unless meaningful order)

5. INTERACTIVITY CHECK
   □ Primary insight visible on page load
   □ Slicer state visible
   □ Drill-through has back button
   □ ≤ 8 bookmarks
   □ All cross-filter interactions deliberately configured

6. ACCESSIBILITY CHECK
   □ Alt text on every non-decorative visual
   □ Tab order matches reading order
   □ Keyboard navigation works end-to-end
   □ Touch targets ≥ 24×24px
   □ High-contrast mode tested

7. ARCHETYPE CHECK
   □ Visual density matches archetype
   □ Interaction budget matches archetype
   □ Typography tier matches archetype
   □ Color palette matches archetype
```

---

## Cross-Reference to Other Documents

| Anti-Pattern Cluster | Primary Reference | Secondary Reference |
|---|---|---|
| Visual noise | `chart-selection.md` — Anti-patterns section | `layout.md` — Whitespace tiers |
| Misleading encoding | `chart-selection.md` — Decision matrix | `chart-selection.md` — Encoding accuracy |
| Cognitive overload | `layout.md` — Visual hierarchy, Templates | `interactivity.md` — Interaction budgets |
| Color misuse | `color.md` — Palette tables, CVD | `accessibility.md` — Contrast workflow |
| Interactivity theater | `interactivity.md` — Taxonomy, titles | `interactivity.md` — Bookmark rules |
| Archetype mismatch | `layout.md` — Composition templates | All reference documents' archetype sections |
