# Visual Narrative Answer Format

Use this format for returned or explicitly supplied rows after selection,
evidence validation and query-scope checks are complete.

## Contents

- [Default structure](#default-structure)
- [Table rules](#table-rules)
- [Numeric precision](#numeric-precision)
- [Cross-visual synthesis](#cross-visual-synthesis)
- [Observation versus interpretation](#observation-versus-interpretation)
- [Final check](#final-check)

## Default structure

Write insights rather than a chart inventory or spoken version of every row.
Use plain business language, descriptive visual names and **bold key findings**;
keep API names, raw IDs, aggregation-level terminology, column roles, bucket
IDs, flag-column names and debugging details out of the narrative itself. Put a
requested test/debug report separately so technical success does not substitute
for the answer. Match the auto-generated style of Power BI's own Narrative
visual: short paragraphs labeled by dimension, a plain-text headline,
bullets for loss/exception lists and explicitly labeled derived figures — not
a flat, unlabeled wall of prose.

Bold key values, field and category names (for example `**North**` and
`**$80**`), and notable highs, lows and outliers using returned formatting;
never bold a whole sentence. Use labels exactly as supplied. Report shares or
percentages only when supplied or returned as evidence, never merely because
totals make them computable.

For each successful selected visual, use this structure by default. Honor an
explicit prose-only, brief-answer or different-format request without losing
factual scope. When a plain-text opening is requested, the first paragraph has
no bold, heading or label prefix -- not even the Plan, sheet or visual name.
Start directly with the narrative: no lead-in such as "Here's the narrative",
and no total, sum or other figure that was not supplied, even in one line.
No fixed word limit: length follows fetched coverage.

1. **Visual heading:** verified chart type plus title or field label. Do not
   replace distinct visuals with one generic sheet narrative.
2. **Headline:** one plain-text sentence, with no bold or other Markdown,
   stating the most important supported contrast using only supplied or
   returned figures, for example "North leads Regional Sales at $80, with
   South at $20." Use a total only when the evidence itself returns one;
   never add members up to create one.
   Higher cost is not inherently better performance. State retrieval
   coverage here when relevant (for example "All four visuals were
   retrieved in full"). If the evidence supplies no currency/unit symbol,
   say so once here (for example "Currency units weren't returned, so the
   $ sign is left off below") instead of inventing one or silently
   dropping it.
3. **Findings:** carry figures in prose, naming each metric in business language
   and giving its value per member. Cover every fetched metric; do not drop one
   because it is secondary. Lead each distinct breakdown with a short label
   naming what follows (for example "Profit concentration:" or "By segment,"),
   one label per paragraph, rather than one continuous unlabeled paragraph.
   Explain informative gaps, near ties or ranking contrasts. Do not
   render box-drawing or ASCII-art grids.
4. **Contributors:** give each primary member a concise finding with its figures
   for every fetched metric. If nested children were fetched, name its highest
   and lowest children with their figures and interpret only meaningful
   comparisons. Group each member's metrics rather than mechanically restating
   every returned cell.
5. **Other fetched dimensions:** explain the key breakdown with verified
   figures, relating it to the primary view only when contexts align. Label
   each with its dimension (for example "By country," or "By category,").
   Cover every fetched dimension and depth; do not silently collapse a
   detailed grid to a grand total. Compare parent/child totals without
   counting either twice.
6. **Negatives and unusual values:** name material negative amounts, zeros,
   missing members and exceptional differences with figures. Use a bulleted
   list, one member per bullet, for three or more loss/exception members (for
   example several loss-making countries); use inline prose for one or two.
   Do not hide negative signs or label a value a statistical outlier without
   a basis.
7. **Next question:** include at most one useful investigative question when
   supported by missing evidence. It does not authorize another query, auth
   retry, model refresh or write. Omit it when no material uncertainty remains.

Do not add a closing takeaway, recap or "In short, ..." paragraph unless the
user asks for one; each figure is stated once in the findings above.

## Table rules

Add a primary-level Markdown table only when the user asks for a table;
otherwise state each figure once in short paragraphs. Preserve its labels, row order and
rendered values. Honor an explicit prose-only or different-format request
without losing factual scope. Keep one comparable set of rows, with a verified
grand total or subtotal outside it. Quote a verified total in the headline or
separately. Empty or failed results get no fabricated figures.

When a table is useful, shape the answer like this skeleton; drop a line only
when its rule does not apply, and do not expand it into a second table:

```text
<plain-text headline — top-line figure + the supported contrast>

| <primary dimension> | <measure 1> | <measure 2> |
|---|---|---|
| <member> | <figure> | <figure> |

- **<member>** — <figures>, <supplied derived ratio> — <best child>, <worst child>.
- **<member>** — <figures> — <supported finding>.
- By <secondary dimension>: <member> <figure>, <member> <figure>.

<one useful evidence-based question, when warranted>
```

**Bound the table; never print every returned row.** Show only the members
needed to judge the headline claim, such as the top few by the primary measure
plus any material outlier. Name the omission (for example, "top 5 of 18 regions
by Sales") instead of silently truncating or implying exhaustiveness. A response
bounded at 1000 rows is not itself grounds for printing every row.

**Derived ratios** are quoted only when supplied or returned as evidence with
verified provenance and compatible aggregation; do not compute new ones. Label
them as derived inline where they appear, for example "about 23% of total
profit (a supplied derived figure)" on first use, or "(derived)" for a later,
shorter mention — never present a derived share as if it were a raw value.
Never use a grand-total denominator against a per-member numerator. Quote one
aggregation level per table; never mix a subtotal or grand total with its
children in the same grid.

## Numeric precision

A visual's read result may supply only a raw native number for a measure, with
no separate formatted display string — a label such as `Revenue ($)` or
`Share (fraction, 1 = 100%)` describes the unit, not a ready-made display
format. Round a raw monetary value to 2 decimal places (or to whole currency
units for a brief requested length) before reporting it; never surface binary
floating-point remainder digits (report `662,978.26`, not
`662,978.2593800002`). Round a raw percentage/fraction to one or two decimal
places after converting using the stated unit. This rounding corrects display
precision only; it is not a new calculated value and needs no disclosure as an
estimate.

## Cross-visual synthesis

For several visuals, close with a short cross-visual paragraph. State differing
filters, date scopes or units before comparing. If contexts are incompatible,
say the findings describe separate views rather than forcing a relationship.
Never join key values to costs or unit-price sums to realized profit without
evidence.

List every skipped, unsupported or failed selected visual with its reason. State
shared truncation, omitted display rows and freshness qualifications once, with
per-visual exceptions beside the affected finding. If a full table or contributor
list cannot fit, disclose the presentation limit, name what is omitted, offer
explicit batches, and do not call the answer complete. Keep useful detail;
avoid methodology padding and duplicate disclaimers.

## Observation versus interpretation

- Margin differences prove neither operational efficiency nor an improvement
  opportunity. State the comparison, not an unsupported business conclusion.
- Investigate gaps without asserting causes, prescribing actions or promising
  improvement. Questions about pricing, discounts or mix require relevant
  evidence, not generic recommendations.
- Trends require comparable observations over time. Category line charts and
  display order do not prove a time trend. Quarter/month numbers without a
  verified year/date scope may pool years; describe their distribution, not
  sequential or current-year growth.

Name differing filters, time ranges, source refresh times or granularity in
plain language. Avoid internal bucket/flag terminology unless requested, but
never conceal uncertainty.

Keep raw validated results available to the invoking host for same-context
follow-ups, with their origin/freshness. New scopes need new data; no invented
extrapolation. For an explicit model-only question, use the Model context
workflow indexed in `SKILL.md`.

## Final check

Every reported number must be a supplied or returned cell, including derived
figures supplied with verified provenance; do not calculate new values. Check
attribution to each scoped visual, metric meaning, units, aggregation level,
coverage and requested answer shape. Remove invented values, causes, trends
and recommendations before responding.

For bold names and values, inspect each category paragraph: both the exact
label and the entire formatted value must be inside bold spans. For example,
`**West** reported **$35**.` satisfies both; `**West** reported $35.` does
not. Keep a requested plain-text opening unformatted. Check the draft
silently; do not run a tool or append a validation note.
