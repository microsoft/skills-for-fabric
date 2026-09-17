# Signatures

A `signature` is the **one defining visual move** every page of a report
shares. It's what a user remembers about the report after closing it. Every
report should commit to exactly one — pick from the gallery below, remix a
gallery entry, or author a fresh one.

A signature should be:

- **Specific** — not "good typography" but "tabular-numeral KPI values
  set in monospace, vertically center-aligned in cards"
- **Recurring** — appears on every page (or every relevant page), not
  one hero element somewhere
- **Coherent with the tone** — `Editorial Newsroom` doesn't pair with
  "neon glow KPIs"; pick something the tone supports

This gallery is a pattern library, not an enum. Pick a listed signature only
when it fits the report's audience, data shape, tone, and implementation
constraints. Otherwise author a custom signature using the same rules:
specific, recurring, authorable, and coherent. The goal is a memorable design
identity, not compliance with the gallery.

**Font guardrail:** font names in this gallery are design direction. Prefer
Power BI-supported fonts or provide built-in fallbacks (Segoe UI, DIN, Georgia,
Consolas, Arial, Calibri, Tahoma, Verdana) so Desktop, Service, mobile, and
embedded rendering do not silently diverge.

---

## Typographic signatures

### S1. Tabular numerals throughout

> Every number in the report — KPI values, axis labels, table cells,
> data labels — uses tabular (monospaced-digit) numbers. Columns of
> numbers align cleanly. The eye reads patterns instantly.

**When**: Editorial, FT-style financial, scholarly, anything heavy on
quantitative comparison.

**How**:
- Treat tabular numerals as design intent; Power BI does not expose reliable
  theme-level tabular-figure controls
- Prefer fonts whose digits render consistently in Power BI; if alignment still
  fails, use a monospaced family for KPI/table numeric values only (Cascadia
  Code, Consolas) and keep labels in the body family
- Verify alignment in a test page with two columns of values of
  different magnitudes

**Theme direction**:
```json
"textClasses": {
  "callout": { "fontFace": "'Segoe UI', sans-serif", "fontSize": 32 }
}
```

Per-visual: card `value.fontFamily` set to the monospace family for the
KPI cards specifically.

### S2. Display serif headlines

> Page titles and section headers in a display serif (Source Serif Pro,
> Merriweather, Georgia). Body and chart text in a sans. The serif/sans
> contrast is the signature.

**When**: Editorial, Scholarly, FT-style.

**How**:
- `textClasses.title.fontFace` → serif
- `textClasses.largeTitle.fontFace` → serif (visual titles)
- `textClasses.label.fontFace` → sans (data labels stay legible)
- `textClasses.callout.fontFace` → sans bold (KPI values stay readable
  at high contrast)

### S3. All-caps tracked headlines

> Page titles in ALL CAPS with extra letter-spacing. Reads as deliberate,
> editorial, Bauhaus. Don't track lowercase body — only the headline.

**When**: Bauhaus, Industrial, Brand-forward.

**How**: Treat tracking as intent. Power BI does not expose reliable
`letter-spacing` per text class, so do not promise exact tracking. Set short
headings/section labels to uppercase in the brief; authoring uses uppercase text
and spacing/layout to approximate the tracked look.

### S4. Caption-style annotations under every visual

> Every chart has a small caption (8–9pt) below it explaining the
> takeaway. The caption is the headline; the chart is the evidence.

**When**: Narrative Story, Scholarly, Editorial.

**How**: Per-visual `subTitle.show: true` with `text` set to a
hand-authored takeaway sentence. Subtitle font 9pt, fontColor
`#6B7280` (mid-grey).

---

## Chromatic signatures

### S5. Single-accent discipline

> One saturated accent color used throughout. Everything else greyscale.
> The eye goes straight to whatever wears the accent.

**When**: Minimal Restrained, Executive landing, any primary-metric-with-context
report.

**How**:
- `dataColors[0]` = the accent (any saturated hue)
- `dataColors[1..7]` = greyscale ramp (`#9CA3AF`, `#6B7280`, `#4B5563`,
  `#374151`, `#1F2937`, `#111827`, `#0F172A`)
- Primary KPI value in accent; supporting cards in `#374151`
- Every chart: hero series in accent, others in greys

### S6. Highlight-and-grey

> All bars/lines in muted grey EXCEPT the one being highlighted (top
> performer, current period, selected category). The highlight is the
> entire visual story.

**When**: Comparative Benchmark, Operational Monitor, "rank by X" pages.

**How**: Per-visual `dataPoint.fill` with scope-identity selector for
the highlighted category — set to accent. Everything else: `dataColors[0]`
= `#BDBDBD`.

### S7. FT pink (or any tinted) surface

> Page background is a tinted surface (FT pink `#FFF1E5`, cream
> `#FAF7F0`, mint `#F0FDF4`, etc.) — not white, not grey. The tint is
> the signature.

**When**: Editorial Newsroom, FT Pink Financial, Scholarly Calm.

**How**: `page.json → objects.background.color` to the tint hex with
`transparency: 0D`. Visual containers stay white `#FFFFFF` to layer.

### S8. Status-coded KPI cards

> Every KPI card's accent bar (or background tint) reflects status —
> green if good, amber if warning, red if bad. The dashboard reads as a
> traffic-light board at a glance.

**When**: Operational Monitor, Executive Summary with KPI status.

**How**: Per-card `accentBar.color` driven by a measure (uses
conditional formatting). Card backgrounds stay neutral; the accent bar
or a colored top-border carries the signal.

---

## Structural signatures

### S9. Composite KPI focus

> One KPI treatment — the page's primary metric plus its context — is
> visually emphasized without wasting the hero region on a bare number.
> The eye lands on the metric instantly, then sees why it matters.

**When**: Executive Summary, landing pages, single-question reports where
the primary metric needs immediate emphasis.

**How**: Use a compact-but-prominent card or status tile with value,
delta/reference label, sparkline or threshold band, and a nearby explanation
chart. Keep supporting cards 28–36pt. Do not let a bare single-measure
`cardVisual` occupy the largest/dominant region; the large hero area belongs
to the trend, ranked driver, variance, or other explanatory visual.

### S10. Hairline rules instead of borders

> No borders on any visual. Section breaks marked by 1px hairline
> rules (top + bottom of section). Whitespace + rules carry the
> structure; containers are invisible.

**When**: Editorial Newsroom, Scholarly Calm, Minimal Restrained.

**How**: Per-visual `border.show: false`; `background.show: false` on
chart visuals (white-on-white); section dividers are 1px tall textboxes
with `background.color: #E5E7EB`.

### S11. Pill-shaped section labels

> Section headers wrapped in pill-shaped chips with rounded ends.
> Every section ("KPIs", "Trends", "Top Performers") gets its own
> pill. Reads warm, modern, energetic.

**When**: Playful Energetic, consumer-facing, brand-forward.

**How**: Textbox with `background.color` (warm tint), `border.radius: 24px`,
horizontal padding 16px. Position at top-left of each section.

### S12. Modular grid with consistent gutter

> Every visual on the page snaps to a strict 12-column grid with a
> single gutter value (16px or 24px). No exceptions, no off-grid
> elements. The signature is the regularity itself.

**When**: Industrial Dense, Bauhaus Catalog, any analyst workbench.

**How**: Brief specifies the grid; authoring computes coordinates so
every visual's `x`/`y`/`width`/`height` is on the grid. Pre-flight
checks the grid before handoff.

---

## Iconographic signatures

### S13. Duotone iconography on KPI cards

> Every KPI card carries a duotone icon (filled silhouette + accent
> color overlay) to its left of the value. The icons are a consistent
> visual family.

**When**: Playful Energetic, Corporate Cool with personality, B2B SaaS.

**How**: Registered PNGs (one per metric) at 32px; keep sizing and style
consistent across the card row.

### S14. Channel/brand logos in cards

> One KPI card per channel/platform/region/competitor, each carrying
> that entity's logo. The logo IS the card's identity element.

**When**: Multi-platform marketing reports, competitor benchmarking,
multi-region operations.

**How**: One registered PNG per entity. Cards arrayed in a row;
consistent logo sizing (32–40px); logo positioned top-left, value
centered, label below.

### S15. Status icons in tables

> Every row in a table carries a status icon column (✓ / ! / ✗ or
> custom glyphs). The table reads as a status board.

**When**: Operational Monitor, compliance reports, project tracking.

**How**: Conditional formatting `iconRule` on a status measure. Use
the built-in icon set, or register custom PNGs for brand-specific
status glyphs.

---

## Composing tone + signature

The signature should *emerge from* the tone, not contradict it. Quick
checks:

| If tone is… | Don't pick signature… | Do pick signature… |
|---|---|---|
| Editorial Newsroom | S11 (pill labels), S13 (duotone icons) | S2 (display serif), S1 (tabular numerals), S10 (hairline rules) |
| Industrial Cockpit | S2 (display serif), S11 (pill labels) | S5 (single-accent), S8 (status-coded cards), S15 (status icons) |
| Playful Energetic | S10 (hairline rules), S5 (single-accent monochrome) | S11 (pill labels), S13 (duotone icons), S14 (channel logos) |
| Minimal Restrained | S13 (duotone icons), S11 (pill labels) | S5 (single-accent), S9 (composite KPI focus), S10 (hairline rules) |
| FT Pink Financial | S11 (pill labels), S13 (duotone icons) | S1 (tabular numerals), S2 (display serif), S7 (pink surface) |
| Monospace Terminal | S2 (display serif), S11 (pill labels) | S1 (tabular numerals), S5 (single-accent), S15 (status icons) |
| Industrial Dense | S11 (pill labels), S9 (KPI-focus signature — too sparse for dense analysis) | S1 (tabular numerals), S12 (modular grid), S15 (status icons) |
| Clinical Calm | S5 with red accent (red is reserved for alerts) | S5 with teal/sage, S10 (hairline rules), S13 (duotone icons in muted palette) |

When tone and signature feel disconnected, the signature wins
visually — but reads as accidental. Pick a signature the tone
naturally supports.

---

## Authoring fresh signatures

If none of the gallery entries fit, author a new one. The `Design Brief:` may
use a gallery signature ID/name, a remixed signature, or a custom one-sentence
signature. Do not force a report into the gallery if a custom recurring move
fits better.

A good signature has these properties:

1. **One sentence describes it** — "every KPI card has a hairline rule
   above the value and the value is set 2× the label size"
2. **Theme-snippet authorable** — there's a concrete `textClasses` /
   `visualStyles` / per-visual VCO change that delivers it
3. **Recurs across pages** — not a one-time hero element
4. **Tone-coherent** — fits the report's mood

Document the new signature in the brief's `design_identity.signature` field
with the same one-sentence pattern.
