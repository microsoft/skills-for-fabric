# Power BI Performance Analyzer Diagnostics Guidelines

This document describes the guidelines that should be applied when analyzing a
Power BI Performance Analyzer JSON export. The review must identify what is
slow, distinguish observed evidence from hypotheses, and provide specific next
steps without modifying the report or semantic model.

## Core Principles

- **Evidence first** - Base findings on the exported capture before applying
  thresholds or general guidance.
- **Actionable time first** - Rank work that can be investigated directly. Keep
  `Other` visible, but do not treat queueing or synchronization time as proof
  that one visual is defective.
- **No double counting** - DAX and DirectQuery timings can overlap. Use their
  maximum as query time unless the export proves they are non-overlapping.
- **Identity matters** - Preserve exact visual types, page identity quality,
  query text, and source fields. Do not collapse `card` and `cardVisual`.
- **Measured claims only** - Label text-pattern findings as candidates and do
  not claim that a rewrite or design change is faster without validation.
- **Preserve the source** - Keep analysis local and write only derived report
  artifacts.

## Inputs And Output Location

Required input:

- A readable local Power BI Performance Analyzer `.json` export.

Optional context:

- Report name, capture scenario, expected page names, storage mode, and known
  user complaint.
- A PBIP/PBIX report or report metadata for resolving visual IDs and page names.
- User-provided bottleneck definitions or report-performance documentation.

Set the output directory to `./powerbi_performance_report`, resolved against the
working directory from which the skill is executed. Do not place outputs beside
an input file from another directory and do not ask the user to choose a
different output directory.

Before analysis begins, tell the user the resolved output directory. Repeat it
in the completion message and link to the generated HTML and Markdown reports.

## Privacy And Safety

**DO:**

- Treat DAX, SQL/KQL, table names, measure names, filters, report names, and
  visual titles as potentially sensitive.
- Keep analysis local unless the user explicitly requests an upload or remote
  workflow.
- Preserve the source file and write derived artifacts only to the output
  directory.
- Sanitize spreadsheet-formula prefixes in CSV text fields: `'='`, `'+'`, `'-'`,
  and `'@'`.

**DON'T:**

- Print access tokens, connection strings, credentials, or full sensitive
  queries in chat.
- Change DAX, report layout, model objects, data sources, or capacity settings
  from this diagnostic workflow.

## Source Authority

When sources disagree, use this order:

1. The actual Performance Analyzer JSON evidence.
2. Current Microsoft Learn documentation and the official export-format
   specification.
3. User-provided internal documentation, when accessible.
4. Microsoft `semantic-model-authoring` Analyze Best Practices and Optimize DAX
   Performance workflows.
5. SQLBI and Report Analyzer as supplementary interpretation and tooling
   references.
6. Community discussions as anecdotal context only.

Never let a community claim override Microsoft documentation or the observed
capture.

## Analysis Workflow

Use this workflow in order. Do not rank findings before validating and
normalizing the capture.

### 1. Validate The Request

1. Resolve the input path and confirm it is a readable file with a `.json`
   extension.
2. Parse it with a structured JSON parser. Never parse JSON with regular
   expressions.
3. Record the file name, capture version, session ID when present, file size,
   and analysis timestamp.
4. Reject an empty, malformed, or unsupported file with a specific error and
   the detected top-level shape.
5. Resolve and create `./powerbi_performance_report` without overwriting the
   source.

If the user provides a directory, list candidate JSON files and select the only
candidate. If multiple candidates exist, ask which capture to analyze.

### 2. Discover And Parse The Schema

Support both:

- Official event-tree exports, typically containing `version`, `events`, and
  `sessionId`.
- Flattened or transformed exports containing visual records and timing fields
  in arrays or nested objects.

Normalize keys for comparison by removing punctuation and whitespace and using
lowercase. Recognize reasonable aliases for:

- Visual ID, visual name/title, visual type, page name/section, and event
  name/type.
- Start timestamp, end timestamp, and duration.
- DAX query, DirectQuery query, visual display/rendering, `Other`, and
  evaluated-parameter timing.
- Parent/child event relationships and interaction events.

For event-tree exports:

1. Traverse every event recursively.
2. Classify timing events by normalized event names and metadata.
3. Associate child timing events with their visual root.
4. Prefer an explicit duration; otherwise calculate duration from valid start
   and end timestamps.
5. Preserve unknown event types for schema diagnostics.

For flattened exports:

1. Locate candidate visual records by identity plus one or more timing or query
   fields.
2. Map aliases into the canonical output schema.
3. Avoid double counting timing events repeated at multiple nesting levels.

If no visual records are found, report observed top-level keys, event names, and
candidate timing keys. Do not return an empty success report.

### 3. Resolve Page Groups

Use explicit page names when present.

When page names are absent but page-change events and timestamps exist:

1. Sort page-change events and visual executions by timestamp.
2. Assign each visual to the latest preceding page-change event.
3. Label the group `Page transition N (name unavailable)`.
4. State that this is an inferred transition group, not a recovered page name.

Use `Unknown page` only when neither explicit identity nor a defensible
transition group exists. Do not make page-density or page-level design claims
for generic unknown groups.

### 4. Build Canonical Visual Metrics

For every visual execution, retain:

- Page group and whether it is explicit, inferred, or unknown.
- Visual ID, title/name, and visual type.
- Interaction or event group.
- DAX query text and DirectQuery text when exported.
- `dax_ms`, `direct_query_ms`, `render_ms`, `other_ms`, and `parameter_ms`.
- Source total duration and timestamps when present.
- Parse warnings and source fields used.

Calculate:

```text
query_ms = max(dax_ms, direct_query_ms)
actionable_ms = query_ms + render_ms + parameter_ms
observed_ms = actionable_ms + other_ms
```

Do not add DAX and DirectQuery durations by default. Preserve both values and
use their maximum for ranking unless the export proves they are non-overlapping
for that record.

For page groups, calculate:

```text
other_share_pct = total_other_ms / (total_actionable_ms + total_other_ms) * 100
```

Use `0` when the denominator is zero.

### 5. Interpret Timing Categories

Apply the current Microsoft definitions:

| Category | Interpretation |
| --- | --- |
| DAX query | Time from the visual sending a DAX query until the semantic model or Analysis Services model returns results. |
| Direct query | Time for an external DirectQuery request to return results. |
| Visual display | Client-side drawing time, including web images or geocoding where applicable. |
| Other | Query preparation, waiting for other visuals, queueing on the shared UI thread, or background processing. |
| Evaluated parameters | Time evaluating field parameters for the visual. |

Show `Other` prominently, but exclude it from the primary actionable ranking
and from automatic DAX or rendering severity. Performance Analyzer durations
are elapsed timestamp differences and can include queue time. Label page
aggregates as summed visual time, never page wall-clock duration.

### 6. Rank And Categorize Bottlenecks

Rank visuals by `actionable_ms`, then `query_ms`, then `render_ms`. Include
relative outliers within the capture even when fixed thresholds are not crossed.

Assign one primary category and any supporting categories:

| Category | Evidence | Recommended direction |
| --- | --- | --- |
| DAX/semantic model | High `dax_ms` or `query_ms`; exported DAX is present | Validate with server timings and query plan, then use the DAX optimization handoff. |
| DirectQuery/source | High `direct_query_ms`; source query is present | Inspect source query, folding, indexes, gateway, network, concurrency, and source capacity. |
| Visual rendering | High `render_ms` | Reduce data points, conditional formatting, image/geocoding work, or visual complexity; compare native alternatives. |
| Parameter evaluation | High `parameter_ms` | Simplify field parameter use and test without parameter switching. |
| Synchronization/page pressure | High `other_ms` or page `other_share_pct` | Reduce concurrent visual work and retest; do not blame one visual automatically. |
| Page density | More than seven visuals in a reportable page group | Remove, combine, defer, or move visuals to drillthrough, tooltip, bookmark, or detail pages. |
| Visual design | Multiple legacy single-value Cards in a reportable page group | Evaluate one new multi-value Card visual. |
| Capture/environment | First-load-only slowness, high variance, unknown page, missing query text, or incomplete events | Re-capture under a controlled protocol. |

Threshold rules must be configurable and disclosed. Thresholds prioritize
investigation; they do not prove root cause.

Use `5000 ms` as the DirectQuery end-user review threshold. Apply it to
`direct_query_ms`, not total or actionable duration. Flag a DirectQuery
execution only when `direct_query_ms > 5000`; exactly `5000 ms` is not over the
threshold.

### 7. Apply Report-Design Checks

#### Page Density

**DO:**

- Allow up to seven visuals in a reportable page group and flag only groups with
  more than seven.
- Count hidden, decorative, and non-query visuals when the export records them.
- Report visual count, threshold, summed `Other` milliseconds, and
  `other_share_pct`.

**DON'T:**

- Present seven visuals as a Microsoft hard limit. It is this skill's review
  threshold, aligned with Microsoft's guidance to limit visuals to what is
  necessary.

#### Legacy Cards

- Preserve exact semantic identity while normalizing the visual type.
- Treat exact normalized type `card` as the legacy single-value Card.
- Treat `cardVisual` as the newer multi-value Card, never as legacy.
- When a reportable page group has multiple legacy Cards, recommend evaluating
  one new Card visual with multiple values.
- Keep this as a design recommendation. Do not raise timing severity solely
  because Cards are present.

#### Visual Rendering

For expensive visual display time, recommend only evidence-relevant actions:

- Reduce displayed rows, points, categories, or map locations.
- Apply restrictive filters and sensible Top N limits.
- Compare custom visuals with native visuals.
- Reduce expensive conditional formatting, images, or geocoding.
- Split detail from overview with drillthrough or report page tooltips.

### 8. Inspect DAX As Candidate Evidence

Inspect exported DAX for candidate patterns such as broad table filters,
high-cardinality grouping, iterators with context transition, repeated
expressions, measure-value filters, forced zero/blank suppression, large key-set
filters, and repeated sibling scans.

For every text-only DAX finding:

- Label it `candidate`, `hypothesis`, or `needs trace validation`.
- Quote only the smallest useful query excerpt.
- Explain why the pattern might matter.
- Do not claim a rewrite is faster without measured evidence.
- Do not automatically rewrite a semantic model measure from generated visual
  query text.

Generated visual DAX does not identify the slow measure, Formula Engine/Storage
Engine split, callbacks, materialization, fusion, data layout, or source latency
without trace evidence.

### 9. Surface Slow DirectQuery Queries

Treat the capture as DirectQuery when storage-mode metadata identifies
DirectQuery or any visual contains a DirectQuery timing or source-query event.

For every visual execution where `direct_query_ms > 5000`:

- Mark it as requiring end-user review, even when DAX duration overlaps it.
- Report page group, visual ID, title, type, `direct_query_ms`, `dax_ms`,
  `query_ms`, and total/actionable timing context.
- Include the complete captured SQL, KQL, M/native, or other source query in a
  dedicated **DirectQuery queries over 5 seconds** section in HTML and Markdown.
- Use an expandable query block in HTML and a fenced code block in Markdown.
- Preserve complete query text without truncation in `analysis_report.json` and
  `direct_query_queries.csv`.
- Recommend reviewing source execution, query folding, indexes or partition
  pruning, gateway and network latency, concurrency, and source capacity.
- Label recommendations as investigation steps until source plans or telemetry
  validate them.

If the source query is missing, still flag the execution and state
`DirectQuery text was not captured`. Never substitute generated DAX for missing
source query text.

### 10. Route Validated DAX Bottlenecks

Recommend the `semantic-model-authoring` **Optimize DAX Performance** workflow
only when all of these are true:

1. DAX query time materially contributes to actionable duration.
2. The exported DAX query or affected measure can be identified.
3. A trace-capable client and semantic model connection are available or can be
   established.
4. The user wants remediation beyond capture analysis.

Include in the handoff:

- Visual and page-group identity.
- Exported DAX query.
- Baseline Performance Analyzer timings.
- Suspected measures and candidate text patterns.
- Storage mode and known model context.
- A request to load the DAX performance decision guide, establish a controlled
  baseline, capture server timings/query plan, and test semantic equivalence.

> **Handoff:** DAX contributes materially to this visual's actionable duration.
> Continue with the `semantic-model-authoring` skill's **Optimize DAX
> Performance** workflow. Use the captured query as the baseline, resolve its
> measure dependencies, collect server-timing traces, test candidate patterns,
> and retain only changes that are semantically equivalent and faster beyond
> normal run variance.

For broader model concerns, recommend **Analyze Best Practices** as a
complementary follow-up. Do not substitute a model-wide audit for trace-based
DAX optimization.

### 11. Recommend A Controlled Re-Capture

Recommend another capture when evidence is incomplete or inconsistent:

1. Open the target report and Performance Analyzer.
2. Clear previous results and start recording.
3. Reproduce the exact page load or user interaction.
4. Use **Refresh visuals** to reduce first-load/model-allocation noise when
   comparing visuals.
5. Capture at least two comparable runs where practical.
6. Stop recording and export the JSON before clearing the pane.

Record whether each run is an initial page load, refresh visuals, slicer
interaction, bookmark, drillthrough, or navigation. Do not compare unlike
interactions as equivalent benchmarks.

## Reporting Contract

Create these artifacts under `./powerbi_performance_report`:

| File | Purpose |
| --- | --- |
| `analysis_report.html` | Primary readable report with summary, priorities, tables, and expandable evidence. |
| `analysis_report.md` | Portable narrative report. |
| `analysis_report.json` | Machine-readable findings, metrics, provenance, and assumptions. |
| `visual_diagnostics.csv` | One row per parsed visual execution. |
| `page_summary.csv` | Page-group counts and summed timing categories, including `other_share_pct`. |
| `dax_queries.csv` | Visual-to-query mapping with CSV-safe query text. |
| `dax_pattern_findings.csv` | Candidate DAX text-pattern findings and validation steps. |
| `direct_query_queries.csv` | DirectQuery executions over five seconds with identity, timings, and complete CSV-safe source query text. |

Start the HTML and Markdown reports with:

1. Executive summary.
2. Capture quality and limitations.
3. Top three to five prioritized actions.
4. Slowest actionable visuals.
5. Page-level findings.
6. Timing-category breakdown.
7. DAX candidates and optimization handoffs.
8. DirectQuery queries over 5 seconds for end-user review.
9. Methodology, thresholds, and references.

Every finding must include:

- Severity: `critical`, `high`, `medium`, `low`, or `informational`.
- Confidence: `high`, `medium`, or `low`.
- Scope: visual, page group, model/query, source, or capture.
- Evidence with exact metric values and units.
- Interpretation that distinguishes observation from hypothesis.
- One or more specific next actions.
- A validation step that can confirm improvement.

Keep recommendations short and ordered by expected impact.

## Validation Checklist

Before reporting success, verify:

- The input JSON parsed without unreported record loss.
- At least one visual exists, or the report clearly explains why none could be
  parsed.
- Numeric timings are finite, nonnegative, and consistently measured in
  milliseconds.
- `actionable_ms` excludes `Other`.
- DAX and DirectQuery are not double counted in `query_ms`.
- Every record with `direct_query_ms > 5000` appears in HTML, Markdown, JSON,
  and `direct_query_queries.csv`.
- Records with `direct_query_ms <= 5000` are excluded from the over-five-second
  DirectQuery section.
- Complete captured DirectQuery query text is preserved without truncation in
  detailed evidence and machine-readable outputs.
- Explicit and inferred page identities are distinguishable.
- Generic unknown pages do not trigger page-density or Card claims.
- Seven visuals are allowed and eight are flagged.
- `card` and `cardVisual` remain distinct.
- `other_share_pct` uses summed visual timing and is labeled accordingly.
- CSV files open safely and preserve multiline query text.
- HTML, Markdown, JSON, and CSV totals agree.
- Missing optional references and capture limitations are disclosed.

When using the notebook, restart the kernel and run all cells. A warm-kernel
pass is not sufficient validation.

## Confidence Rules

- Use `high` confidence for direct facts in a well-formed export, such as a
  measured duration or exact visual count.
- Use `medium` confidence for defensible derived facts, such as timestamp-based
  page-transition grouping or a dominant timing category.
- Use `low` confidence for text-pattern hypotheses, incomplete captures,
  ambiguous visual identity, or likely environmental effects.

Never use causal language such as "caused by" when the export supports only
correlation. Prefer "observed," "contributes," "is consistent with," or
"requires validation."

## Failure Modes

| Condition | Required response |
| --- | --- |
| Malformed JSON | Report the parser error location and stop. |
| Unsupported schema | Report observed keys and event names; request the original unmodified export. |
| No timings | Explain whether records contain identity but no duration fields. |
| No page names | Infer transition groups only when timestamps support it; otherwise use `Unknown page`. |
| No DAX text | Diagnose timing categories but do not manufacture query-level advice. |
| Slow DirectQuery without source text | Flag each execution over 5000 ms and state that DirectQuery text was not captured. |
| Public PDF unavailable | Continue with Microsoft Learn, structured schema discovery, and observed evidence; disclose the limitation. |
| Notebook execution failure | Report the failing cell or dependency; do not publish stale artifacts as current. |
| High run variance | Recommend controlled re-capture before ranking marginal differences. |

## Completion Contract

Return:

- Input file and detected schema/version.
- Number of parsed visual executions and reportable page groups.
- Top actionable bottleneck and its evidence.
- Count of high/critical findings.
- Whether a DAX optimization handoff is recommended.
- Count of DirectQuery executions over five seconds and whether complete source
  query text was captured for each one.
- The resolved `./powerbi_performance_report` output directory, explicitly
  noting that it is relative to the execution working directory, plus links to
  the HTML and Markdown reports.
- Missing optional references or unresolved capture limitations.

## References

### Primary

- [Use Performance Analyzer to examine report performance](https://learn.microsoft.com/power-bi/create-reports/performance-analyzer)
- [Power BI Performance Analyzer Export File Format (PDF)](https://github.com/SoomroFarhanH/SemanticModelBPforAI/blob/main/Power%20BI%20Performance%20Analyzer%20Export%20File%20Format.pdf)
- [Optimization guide for Power BI](https://learn.microsoft.com/power-bi/guidance/power-bi-optimization)
- [Monitor report performance in Power BI](https://learn.microsoft.com/power-bi/guidance/monitor-report-performance)
- [Troubleshoot report performance in Power BI](https://learn.microsoft.com/power-bi/guidance/report-performance-troubleshoot)
- [Semantic model authoring: Analyze Best Practices](https://github.com/microsoft/skills-for-fabric/blob/main/skills/semantic-model-authoring/SKILL.md#workflow-analyze-best-practices)
- [Semantic model authoring: Optimize DAX Performance](https://github.com/microsoft/skills-for-fabric/blob/main/skills/semantic-model-authoring/SKILL.md#workflow-optimize-dax-performance)
- [DAX Performance Decision Guide](https://github.com/microsoft/skills-for-fabric/blob/main/skills/semantic-model-authoring/references/dax-perf-decision-guide.md)

### Supplementary

- [Introducing the Power BI Performance Analyzer](https://www.sqlbi.com/articles/introducing-the-power-bi-performance-analyzer/)
- [Report Analyzer](https://github.com/m-kovalsky/ReportAnalyzer)
- [Community discussion: Performance Analyzer in Power BI service](https://www.reddit.com/r/PowerBI/comments/1jwqep2/performance_analyzer_in_power_bi_service/)
