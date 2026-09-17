# Typography for Data

## Core Principles

1. **Sans-serif for screens** — Segoe UI is the PBI default; it renders cleanly at small sizes.
2. **3–4 tiers maximum** — More tiers create visual noise, not hierarchy.
3. **Data-ink over label-ink** — Numbers and chart marks dominate; text supports, never competes.
4. **Align numbers when comparison matters** — Use tabular-looking digits or right alignment for KPI rows, tables, axes, and labels where readers compare magnitudes.
5. **Consistency across pages** — Same role = same size, weight, and color everywhere.
6. **WCAG floors** — Use 9pt as the normal minimum for visible text; 8pt is only acceptable for non-critical captions/footnotes with strong contrast. Maintain 4.5:1 contrast ratio on background.
7. **Weight before size** — Differentiate tiers with weight changes first; increase size only when weight alone is insufficient.

---

## Type Ramp

The 6-tier system below names *conceptual roles* (not theme keys). Power BI's
primary `textClasses` are `callout`, `title`, `header`, and `label`; secondary
classes derive from those primaries. Visual titles use the documented secondary
class `largeTitle`, which derives from `title`. The other tiers (`body-lg`,
`body`, `caption`) are sizing conventions the agent applies inline via
`fontSize` overrides; they do NOT correspond to theme keys.

| Tier | Role | Size (pt) | Weight | Line Height | Use | Theme key |
|---|---|---|---|---|---|---|
| **H1** | Page title | 20 | SemiBold 600 | 1.2× | Report header, page banner | `textClasses.title` |
| **H2** | Visual title | 14 | SemiBold 600 | 1.2× | Chart and table titles | `textClasses.largeTitle` |
| **H3** | KPI value | 28–36 | Bold 700 | 1.0× | Card callout numbers | `textClasses.callout` |
| **body-lg** | KPI label | 11 | Regular 400 | 1.3× | Card subtitle, section label | (none — set inline) |
| **body** | Axis, legend, labels | 9–10 | Regular 400 | 1.3× | Default body text in visuals | `textClasses.label` |
| **caption** | Footnote, timestamp | 8–9 | Regular 400 | 1.3× | Below visual, page footer | (none — set inline) |

**Scaling rule**: each step ≈ 1.25–1.5× the previous. Never exceed 4 distinct sizes on one page.

---

## Tone / Signature Overrides

The type ramp is the baseline. Tone and signature may override it when the
identity depends on typography, but the override must be explicit in the
`Design Brief:` and remain authorable in Power BI.

| Override | Allowed scope | Guardrail |
|---|---|---|
| Serif display typography | Page titles, section headers, narrative annotations | Do not use serif for axis labels, data labels, matrix cells, or dense numeric text |
| Oversized editorial/display titles | H1/page banner or one hero text element | Treat 28–48pt as a tone-driven exception, not the default ramp |
| Monospace/tabular number treatment | KPI values, comparison tables, aligned numeric labels | Use only where alignment improves reading; do not make body text monospace unless that is the signature |
| All-caps headings | Page title, section label, or short chip text | Do not all-caps body copy, table values, or long chart titles |
| Caption-style annotations | Subtitles/annotations under visuals | Keep captions 8–9pt only when non-critical and high contrast; otherwise use 9–10pt |

Power BI does not expose every CSS typography control. Treat requests like
tabular-figure features, letter-spacing, and optical sizing as design intent;
the `authoring` mode chooses the closest PBIR-authorable implementation.

---

## Font Family Guidance

PBI's safest default is Segoe UI — it ships with the platform, renders
consistently across Desktop / Service / mobile / embedded, and has wide
glyph coverage. Use it as the baseline unless brand requirements or the
design identity justify a display font.

| Scenario | Font | Reason |
|---|---|---|
| Default — all text | Segoe UI | PBI native; good hinting; wide glyph coverage |
| Brand alternative | Brand sans-serif | Only when the brand standard mandates it; test at 9pt |
| Tight tabular columns | Segoe UI (or any tabular-numeral monospace fallback) | Avoid serif fonts — serifs collide in narrow cells |
| Monospace fallback | Consolas, Cascadia Code | Only when normal font digits do not align reliably |

### Custom font fallback caveat

Custom fonts can render differently across Desktop, Service, Mobile, and
embedded reports. When using a custom font, provide a fallback chain such as
`'BrandName, "Segoe UI", sans-serif'`; for mission-critical reports, prefer
Segoe UI to avoid silent font substitution.

**Never** use decorative or serif fonts for axis labels, data labels, or matrix cells.

---

## Tabular Numerals & Number Formatting

| Rule | Example | Why |
|---|---|---|
| Use tabular-looking or right-aligned numbers | `1,234` aligns with `9,876` | Columns scan vertically |
| Decimal-align currency | `$1,234.56` / `$  987.00` | Right-align with consistent decimals |
| Thousands separators | `1,234,567` not `1234567` | Readability for 5+ digit numbers |
| Unit abbreviations | `$1.2M` not `$1,200,000` | Cards and axes; full precision in tooltips |
| Negative format | `(1,234)` or `−1,234` | Parentheses for finance; minus sign for general |
| Percentage decimals | `12.3%` (1 decimal) | 0 decimals if ≥10%; 1 decimal if <10% |
| Date axis labels | `Jan`, `Feb` or `Q1 '24` | Abbreviate; full dates only in detail tables |

---

## Density & Readability

| Guideline | Rule |
|---|---|
| **Axis label truncation** | Truncate with ellipsis (`…`) when label exceeds allocated width; full text in tooltip |
| **Tick density** | 5–8 ticks per axis; more clutters, fewer loses reference |
| **In-chart labels vs legend** | Label directly on chart when ≤4 series; legend when >4 |
| **Minimum legible size** | 9pt preferred; 8pt only for non-critical captions/footnotes with strong contrast |
| **Line spacing in cards** | KPI value and label should have ≥4px vertical gap |
| **Matrix row height** | Minimum 20px per row for touch; 16px for dense desktop |
| **Text wrapping** | Avoid wrapping in axis labels and card values; wrap only in text boxes |

---

## Power BI Formatting Keys

| Element | Key Path | Default |
|---|---|---|
| Visual title text | `title.fontSize` | 12 |
| Visual title weight | `title.bold` | true |
| Axis labels | `categoryAxis.fontSize` / `valueAxis.fontSize` | 10 |
| Data labels | `labels.fontSize` | 9 |
| Legend text | `legend.fontSize` | 9 |
| Card callout value | `calloutValue.fontSize` | 27 |
| Card category label | `categoryLabel.fontSize` | 12 |
| Table header | `columnHeaders.fontSize` | 10 |
| Table values | `values.fontSize` | 9 |
| Slicer header | `header.fontSize` | 10 |
| Slicer items | `items.fontSize` | 10 |
| Tooltip text | `default.fontSize` (tooltip visual) | 10 |

---

## Archetype Calibration

| Archetype | H1 | H2 | H3 (KPI) | body | Notes |
|---|---|---|---|---|---|
| **Executive** | 20pt SemiBold | 14pt SemiBold | 36pt Bold | 10pt | Large KPI callouts; minimal body text |
| **Operational** | 16pt SemiBold | 12pt SemiBold | 28pt Bold | 9pt | Dense; prioritize scan speed |
| **Analytical** | 16pt SemiBold | 12pt SemiBold | — | 9pt | No hero KPIs; axis labels matter most |
| **Narrative** | 20pt SemiBold | 14pt SemiBold | 28pt Bold | 11pt | More body text; slightly larger for reading |
| **Comparative** | 16pt SemiBold | 12pt SemiBold | — | 9pt | Uniform sizing for fair comparison |

---

> Anti-patterns: see references/design/anti-patterns.md

---

## Number Format Decision Table

| Data Type | Format | Example | When |
|---|---|---|---|
| Currency (large) | `$#.#M` / `$#.#B` | `$4.2M` | Cards, axes, tooltips for millions+ |
| Currency (exact) | `$#,##0.00` | `$1,234.56` | Tables, detail views |
| Percentage (large) | `#%` | `12%` | Cards, data labels when ≥1% |
| Percentage (small) | `#.#%` | `0.3%` | When precision matters, values <1% |
| Integer count | `#,##0` | `1,234` | Row counts, units sold |
| Decimal measure | `#,##0.0` | `98.7` | Scores, rates, indices |
| Date (axis) | `MMM 'YY` | `Jan '24` | Time axis labels |
| Date (detail) | `DD MMM YYYY` | `15 Jan 2024` | Table columns, tooltips |
| Duration | `#h #m` or `#.# hrs` | `2h 15m` | Time-based measures |

---

## Alignment Rules

| Element | Horizontal Alignment | Vertical Alignment |
|---|---|---|
| Visual titles | Left | Top |
| Numbers in tables | Right | Center |
| Text in tables | Left | Center |
| Card KPI values | Center or Left | Center |
| Card labels | Center or Left (match value) | Below value |
| Axis labels | Auto (axis-aligned) | Auto |
| Data labels | Centered on mark or end-aligned | Auto |
| Page titles | Left | Top |
| Footnotes | Left | Bottom |

**Rule**: Numbers always right-align so decimal points stack vertically. Text always left-aligns for readability.
