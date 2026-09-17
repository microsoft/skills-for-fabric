# Pre-Flight Checklist

Walk through this before handing off the report spec/design contract to
the `authoring` mode. Fix any failures first — the authoring skill will
faithfully implement what you give it, including its flaws.

For brownfield mode, also walk
[`brownfield.md`](brownfield.md) §
*Brownfield-specific Pre-Flight items*.

## Identity (Step 1)

- [ ] **Single source of truth** — if writing files, `_brief/report-spec.md`
      contains the user-readable report spec and exactly one fenced `yaml`
      block beginning with `Design Brief:`.
- [ ] **Markdown/YAML alignment** — every page, core visual, design identity,
      model requirement, and delivery boundary promised in Markdown is present
      in the embedded YAML. If they conflict, fix the spec before authoring.
- [ ] **Implementation authority clear** — prose provides context; the embedded
      `Design Brief:` YAML is the canonical implementation contract.

- [ ] **Tone committed** — the brief's `design_identity.tone` is a
      named catalog entry from
      [`tone-catalog.md`](tone-catalog.md), OR a short elaboration
      that pins down the feel. One-word tones like "modern" or
      "professional" are not enough; replace.
- [ ] **Signature committed** — the brief's `design_identity.signature`
      names a single concrete move from
      [`signatures.md`](signatures.md) or an authored equivalent. The
      signature recurs on every page (or every relevant page).
- [ ] **Tone and signature are coherent** — the signature pick fits
      the tone (see signatures.md § Composing tone + signature). If the
      feel and visual move point in different directions, re-pick.
- [ ] **Brownfield two-value form** — if `mode: brownfield`, both
      `current_tone` and `current_signature` are filled in (or
      explicitly "indistinct" / "none"). The redesign delta is
      reasoned about in the brief.

## Routing (Steps 2–3)

- [ ] **Vague prompt handled** — if the original request was missing
      audience, purpose, page count, or filtering depth, the design
      brief shows that 2–3 named options were offered to the user and
      one was confirmed (or, after two rounds, an assumption was
      documented in `variant_rationale`). Do NOT silently guess on a
      vague prompt and ship a brief.
- [ ] **Per-page archetype routing** — every page's archetype was
      chosen from its own audience/purpose/cadence — not inherited
      from page 1. Multi-page reports covering distinct subject areas
      should mix archetypes. 3+ pages all sharing one archetype is a
      smell — re-route each page independently.
- [ ] **Layout variant per page** — every page declares
      `layout_variant` (A/B/C) AND a one-sentence `variant_rationale`
      citing the data signal that drove the pick. Same-archetype
      pages should rotate variants where data signals support it
      (see [`archetype-composition.md`](archetype-composition.md) §
      Cross-page variant rotation).

## Theme & propagation (Step 1 → Step 5)

- [ ] **Theme handoff is explicit** — if a custom theme is needed, the
      brief states the intended theme name, palette/text changes, and
      asks the `authoring` mode to handle registration mechanics.
- [ ] **Theme/per-visual boundary captured** — properties that may need
      per-visual treatment (border radius, padding, page background
      transparency, gradient stops, card accent bar) are called out in
      the brief for the `authoring` mode.
- [ ] **Generated-report theme safeguards preserved** — if creating/adapting a
      custom theme, preserve `references/design/assets/base.json` per-type safeguards: textbox
      zero padding/background/border, `cardVisual` zero padding/card spacing,
      table grow-to-fit styling, hidden visual headers, and chart defaults.
- [ ] **Tone propagated to typography** — if the tone called for a
      display serif (Editorial), the brief's theme has serif
      `textClasses.title.fontFace` set. Tone declared without
      typography change reads as accidental.
- [ ] **Tone propagated to color** — the `dataColors` palette
      reflects the tone-catalog row's accent guidance, not the base
      Okabe-Ito as-is.
- [ ] **Measure color map complete** — every measure used in a color-bearing
      card/chart/map/table has a `color_map` entry or a documented reason to use
      category/semantic colors instead.
- [ ] **Tone propagated to iconography** — if iconography is part of
      the signature, the icon style (filled/outline/duotone) matches
      the tone and stays consistent across the report.

## Page-level layout (Step 6)

- [ ] **Page background set** (`#F3F2F1` or similar off-white, OR the
      tone-aligned tinted surface from the tone-catalog) on every
      page with explicit `transparency: 0D`.
- [ ] **Descriptive insight titles** on every page — not "Overview"
      or "Dashboard" but "Language Courses Drive 45% of All
      Enrollment".
- [ ] **Every chart has explicit VCO `title.text`** and intentional subtitle
      behavior — use a subtitle for time window, active filter, units,
      comparison baseline, or caveat; omit/disable it when it repeats the title,
      obvious measure, or raw field name.
- [ ] **KPI cards show context** (`referenceLabel` or subtitle) — no
       bare numbers.
- [ ] **Callouts earn their space** — every side callout/context tile or Smart Narrative has
      `insight_basis` or `callout_value_basis` tied to delta, variance %, rank
      shift, threshold, benchmark gap, anomaly, or dynamic narrative text. No
      callout repeats the same absolute measure already shown in an adjacent
      chart/table.
- [ ] **Bar/column charts sorted** by value descending.
- [ ] **No unintended monochrome bars** — if category contrast matters,
      specify value-gradient or per-category color intent.
- [ ] **Clean display names everywhere** — no raw field names
      (`subject_name`, `Count of fight_key`), no default aggregation
      labels (`Sum of X`).
- [ ] **Slicers on pages with 3+ data visuals** — right field, right
      type (dropdown/list/between), right position (top-bar/left-rail).
- [ ] **Date slicer matches grain** — executive/annual-grain pages use Year or
      Period dropdown/tile by default; full-date `between` is used only for
      renderable Date/DateTime fields when arbitrary date-range exploration is
      part of the page question.
- [ ] **Slicer/header band reserved** — top-bar slicers sit fully inside a
      reserved title/slicer band, with the page title as the left anchor and
      slicers aligned to the right. No chart/card/table starts under the slicer
      rectangle. Taller slicers increase the band height.
- [ ] **Geography routed by question** — if location/spatial distribution
      carries the message, consider `azureMap` first; if geography is only a
      ranked category, a sorted bar chart is acceptable and the rationale should
      say so.
- [ ] **No pie/donut with >5 slices** — use sorted horizontal bar.
- [ ] **No text month/quarter names on time-series axes** — use Date
      column.
- [ ] **Every coordinate on 8-px grid** (x, y, width, height all
      multiples of 8).
- [ ] **Greenfield canvas defaults to FHD** — new reports use `1920 x 1080`
      unless the user requested or approved a different size. Brownfield keeps
      the existing canvas unless resize is approved.
- [ ] **No unintended overlaps** — sibling visual bounding boxes do not overlap
      unless the overlap is intentional and non-data-bearing.
- [ ] **No unplaced regions** — every non-spacer region in `layout_contract`
      has at least one placement. Remove empty footer/callout/detail regions or
      put real content in them.
- [ ] **Space audit passes** — `space_audit` exists, `unplaced_regions` is empty,
      and `empty_cell_pct` stays within budget (`<=15` for analytical/
      operational/comparative, `<=20` for executive/narrative unless justified).
- [ ] **Visual balance intentional** — no single non-hero data region starves
       supporting visuals; supporting charts have at least 3x3 grid cells, tables
       at least 4 rows, and KPI/card strips 2 rows on standard pages.
- [ ] **No oversized bare card hero** — a single-value `cardVisual` is not the
      largest/dominant page region. If a KPI hero is intentional, it is a
      composite treatment with delta/reference label, sparkline/threshold context,
      annotation, or adjacent explanatory chart, and `balance_rationale` says why
      it deserves the space.
- [ ] **Textbox heights sufficient** — no scrollbars (height formula:
       `max(18, ⌈fontSize × 25/16⌉) + padding_top + padding_bottom`).
- [ ] **Per-visual formatting needs are explicit** — background,
      border/radius, padding, visualHeader, or card accent-bar
      requirements are stated in the brief when the design depends on them.
- [ ] **Card padding/gutters intentional** — card visuals use card-specific
      padding/background/spacing, not accidental wildcard theme padding that
      creates white gutters or clipped content.
- [ ] **Canvas filled** — no dead footer band or >20% whitespace gap; expand
      bottom-row visuals, add a real detail/footer placement, or rebalance rows
      if the canvas looks empty.

## Accessibility (Step 7)

- [ ] **WCAG contrast** verified on every text/background pair
      (page background ↔ axis labels; card background ↔ card values;
      chart plot ↔ legend; tooltips; CF cell colors).
- [ ] **Tab order matches reading order** — Selection pane reordered
      on every page.
- [ ] **Alt text per visual** — content-specific, not "Bar chart".
- [ ] **Color encoding has redundant cue** when color carries
      meaning (data labels, shape, or pattern).

## Final visual audit (after build)

- [ ] **Squint test** — a screenshot of each page makes one element
      jump out (the hero / signature). If nothing jumps, hierarchy
      is flat.
- [ ] **Sibling test** — pages laid out side-by-side read as part of
      the same family (border radius, type, accent usage all
      consistent).
- [ ] **Identity propagation visible** — a stranger looking at the
      report could describe the tone in a sentence (the test for
      whether tone is doing real work).
- [ ] **No clipped controls or scrollbars** — slicers, textboxes, cards, legends,
      and tables are fully visible in screenshots.
- [ ] **Color-map audit passes** — every visual using the same measure reuses
      that measure's color, and gradients use that measure's tint/base pair.
