# Archetype Composition & Variant Rotation

Use this file when a report has more than one page. Greenfield routing
(per-page archetype + variant) lives in `SKILL.md` Step 2; this file
covers the report-level composition patterns and the rule against
mono-archetype reports.

## Common multi-archetype compositions

| Report shape | Page 1 | Page 2 | Page 3+ | Notes |
|---|---|---|---|---|
| **Executive + Drill** | Executive Summary | Analytical Canvas | Comparative Benchmark for ranking pages | Most common; KPI landing → exploration → ranking |
| **Ops + Detail** | Operational Monitor | Analytical Canvas | Narrative Story for post-incident review | NOC board → incident drill → write-up |
| **Story + Evidence** | Narrative Story | Comparative Benchmark | Analytical Canvas for the appendix | Quarterly reviews, board presentations |
| **Multi-domain** ("cover everything" request) | Executive Summary as landing | Comparative Benchmark for entity rankings | Analytical Canvas for filterable exploration; Narrative for historical timeline | Default decomposition when one request spans multiple subject areas (entities + events + locations + actors) |

## Avoid mono-archetype reports

A 4-page report that is 4× Analytical Canvas (or 4× Executive Summary)
usually means each page wasn't routed independently — page 1's
archetype was copied to pages 2–4 by inertia.

When the same archetype is genuinely correct for multiple pages, those
pages must rotate **layout variants** (see *Cross-page variant
rotation* below). When even variant rotation can't differentiate the
pages, that's a signal the pages should be merged or split — not a
signal to ship 4 identical layouts.

## Cross-page variant rotation

When a report has 2+ pages of the **same archetype**, actively pick
**different variants** for each page where the data signals support
it. A 4-page Analytical report should not be 4× Filter-Rail; pick:

- **Filter-Rail** for the dense exploration page,
- **Inline-Slicers** for the focused-question page, and
- **Small-Multiples-Grid** for the cross-entity comparison page.

The selection tables in each archetype file are the mechanism — walk
them per page using *that page's* data shape, not the report's
overall shape. Only repeat a variant when two pages genuinely share
the same data signals AND serve distinct purposes.

| Same-archetype page count | Variant-rotation expectation |
|---|---|
| 1 page | Pick the variant the data calls for; no rotation needed |
| 2 pages | At least one page should differ from the other (≥1 of 2 variants) |
| 3 pages | Use at least 2 distinct variants; prefer all 3 if data supports it |
| 4+ pages | All available variants for that archetype should appear unless every page genuinely has identical data signals |

## Composition vs. tone

The composition pattern is independent of the design identity
(`tone` + `signature`) — an Executive + Drill report can be Editorial
Newsroom OR Industrial Cockpit OR Minimal Restrained. The tone
propagates uniformly across every page; the composition determines
which archetypes those pages occupy.

Pages within one report MUST share a tone and signature. A report
where page 1 is Editorial and page 2 is Industrial reads as two
reports stitched together. If the user requests genuinely different
tones for different audiences (e.g., "an exec page and an ops page"),
that's a signal to produce two reports, not one report with two
identities.
