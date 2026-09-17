# Tone Catalog

The Step 1 `tone` field is **open vocabulary** — a free-text adjective +
short elaboration. But agents (and humans) struggle to pick a tone from
nothing. This catalog is a calibration set, not a closed style menu. Prefer
a catalog entry when it fits the audience, data, brand, and user constraints;
otherwise remix entries or author a custom tone.

The `Design Brief:` may use a catalog name, a remixed name, or a short custom
tone phrase as long as it drives concrete downstream choices. Do not force every
report into one of these entries.

Each entry maps the tone to **downstream choices** so picking a tone
actually drives later decisions:

- Typography pairing (display + body)
- Palette move (cool/warm, accent count, surface)
- Density / rhythm (modular ratio)
- Gridline / border treatment
- Default signature candidate
- Iconography style
- Domain examples

If your report's tone is one word ("modern", "professional", "clean") and
not in this catalog, **do one of two things**:

1. **Pick a catalog entry instead.** "Modern" is ambiguous; "Editorial
   Bold" or "Corporate Cool" or "Minimal Restrained" are not.
2. **Write a short elaboration** that pins it down. "Modern" → "modern
   editorial newsroom with serif display headings, sans body, single
   amber accent, no gridlines."

A custom tone must include enough detail to guide implementation:

- Emotional feel / audience posture
- Surface or palette direction
- Typography direction
- Density / spacing direction
- One concrete downstream implication

**Font guardrail:** prefer fonts that Power BI reliably supports across Desktop
and Service (for example Segoe UI, DIN, Georgia, Consolas, Arial, Calibri,
Tahoma, Verdana). Catalog font names are design direction; when a font is not
guaranteed in Power BI, specify a built-in fallback and do not assume Service,
mobile, or embedded rendering will match Desktop.

Tone is not interior decoration — it's a constraint that makes every
later decision easier.

---

## 1. Editorial Newsroom

> Reads like a Sunday business broadsheet. Type leads. One sharp accent.
> Whitespace generous.

| Aspect | Pick |
|---|---|
| Display typography | Serif (Source Serif Pro, Merriweather, or Georgia) at 28–48pt |
| Body typography | Sans (Segoe UI, Inter, or Source Sans) at 11–13pt |
| Surface | Cream `#FAF7F0` or off-white `#F8F9FA` |
| Accent | One — black `#0F172A` for emphasis, or mustard `#D4A30A` for highlight |
| Density / ratio | 1.500 (Perfect Fifth) — strong hierarchy |
| Gridlines | Hairline rules above/below sections; no chart gridlines |
| Borders | None on visuals; section dividers only |
| Default signature | Display serif headlines + tabular numerals on KPIs |
| Iconography | Outlined hairline (1px) — restrained |
| Domain examples | Quarterly review for board, annual report, financial publication, news/media analytics |

## 2. Industrial Cockpit

> Dark canvas, instrument-panel feel. High contrast. Restrained color —
> color is reserved for status, not decoration.

| Aspect | Pick |
|---|---|
| Display typography | Geometric sans bold (Inter Bold, Roboto Bold) at 24–36pt |
| Body typography | Same family, regular weight, at 10–12pt |
| Surface | Dark navy `#120E2A` or near-black `#0E0E10` |
| Accent | Indigo `#5772D9` + cyan `#8CEEEE` for status; muted purple `#7D77A8` for chrome |
| Density / ratio | 1.333 (Perfect Fourth) — gentle hierarchy, density-friendly |
| Gridlines | Dotted, low-opacity (`#3A3A4A`) |
| Borders | Subtle (`#2A2A3A`); use background-fill cards for grouping instead |
| Default signature | High-contrast status values on dark; status icons in cards |
| Iconography | Filled, geometric — high contrast on dark |
| Domain examples | Ops monitoring, NOC dashboards, on-call wallboards, infrastructure health |

## 3. Clinical Calm

> Cool, almost-white canvas. Teal/sage accents. Generous spacing.
> Healthcare-feeling without being sterile.

| Aspect | Pick |
|---|---|
| Display typography | Humanist sans (Source Sans, Lato, Inter) at 22–32pt |
| Body typography | Same, regular, at 11pt |
| Surface | Cool blue-white `#F0F9FF` |
| Accent | Teal `#0D9488` + sage `#84CC16`; reserve red strictly for genuine alerts |
| Density / ratio | 1.250 (Major Third) — gentle |
| Gridlines | Solid, very-low-opacity (`#E5E7EB`) |
| Borders | 1px hairline `#E5E7EB`, radius 8px |
| Default signature | Calm spacing within the space-audit budget; KPI values centered in compact cards |
| Iconography | Outlined, semi-bold stroke; never red except for alerts |
| Domain examples | Patient safety dashboards, clinical operations, healthcare KPIs, wellness programs |

## 4. FT Pink Financial

> Specific reference: the Financial Times pink-tinted broadsheet. Tabular
> numerals everywhere. Editorial discipline applied to financial data.

| Aspect | Pick |
|---|---|
| Display typography | Serif (Financier, Source Serif Pro fallback) at 28–48pt |
| Body typography | Sans (Segoe UI, Inter) with tabular-looking numeric treatment where values must align |
| Surface | Pink-tinged white `#FFF1E5` (the FT pink) |
| Accent | Black `#0F172A` for type; one teal/red for variance signal only |
| Density / ratio | 1.500 — strong hierarchy via type |
| Gridlines | None on charts; thin rules between sections |
| Borders | None |
| Default signature | Tabular numerals throughout + serif display headlines |
| Iconography | Minimal — type carries the load |
| Domain examples | Hedge fund / asset-management reporting, financial earnings dashboards, market commentary |

## 5. Bauhaus Catalog

> Geometric, modernist, functional. Primary colors used sparingly.
> Type-as-signal.

| Aspect | Pick |
|---|---|
| Display typography | Geometric sans (Futura, ITC Avant Garde, or Inter Bold) at 32–48pt; consider all-caps tracking |
| Body typography | Same family at 11–13pt |
| Surface | Off-white `#FAFAFA` |
| Accent | One primary — true red `#E63946`, true blue `#1D3557`, or true yellow `#F4D03F` |
| Density / ratio | 1.333 — modular |
| Gridlines | None or solid hairline |
| Borders | Strong (2px solid) where used; otherwise none |
| Default signature | All-caps tracked headlines + bold geometric ratios |
| Iconography | Geometric / pictogram |
| Domain examples | Design-team dashboards, brand reporting, creative-agency analytics |

## 6. Monospace Terminal

> Developer/quant feel. Monospaced numbers (and possibly all type).
> Ticker-style KPI bars. Color used like syntax highlighting.

| Aspect | Pick |
|---|---|
| Display typography | Monospace (Cascadia Code, JetBrains Mono, Consolas) at 24–36pt OR sans display + monospace numerals |
| Body typography | Monospace at 11pt OR sans body with mono numerals |
| Surface | Off-white `#F8F8F2` (Solarized-light) or near-black `#0E0E10` |
| Accent | Two accents like syntax tokens — green `#50FA7B` + magenta `#FF79C6` (Dracula), or muted teal `#268BD2` + amber `#B58900` (Solarized) |
| Density / ratio | 1.250 — dense |
| Gridlines | Dotted, monospace-grid feel |
| Borders | None or 1px subtle |
| Default signature | Monospaced KPI ticker bar across the top |
| Iconography | ASCII-style or filled geometric |
| Domain examples | Engineering dashboards, quant trading, observability, developer-team metrics |

## 7. Industrial Dense (Analyst Workbench)

> Off-white surface, dense data, charcoal type, two-color accent. Built
> for the analyst who is going to spend an hour in this report.

| Aspect | Pick |
|---|---|
| Display typography | Sans (Inter, Work Sans) at 18–26pt |
| Body typography | Same family at 10–11pt |
| Surface | Off-white `#FAFAFA` |
| Accent | Steel blue `#3B6E91` + burnt orange `#C8742A`; charcoal `#262626` for text |
| Density / ratio | 1.250 — packed but legible |
| Gridlines | Solid `#E5E5E5` — packed grids need them |
| Borders | 1px `#E0E0E0` — defines cells in dense layouts |
| Default signature | Tabular numerals + matrix-style page layout |
| Iconography | Filled, small (14–16px) |
| Domain examples | Financial models, ops analytics, sales-pipeline workbenches, IBCS-style variance reports |

## 8. Playful Energetic

> Warm, bright, geometric. Coral and warm accents. Soft shapes.
> Consumer/lifestyle feel without being childish.

| Aspect | Pick |
|---|---|
| Display typography | Rounded geometric (Quicksand, Nunito, or Poppins) at 28–40pt |
| Body typography | Same family at 11pt |
| Surface | Warm cream `#FFF7ED` |
| Accent | Coral `#FB7185` + black `#171717`; peach `#FED7AA` for cues |
| Density / ratio | 1.333 — friendly hierarchy |
| Gridlines | None on charts; pill-shaped section labels instead |
| Borders | Rounded (radius 12–16px); soft drop-shadow on primary KPI cards OK |
| Default signature | Pill-shaped KPI cards + warm coral accent |
| Iconography | Rounded duotone — soft and friendly |
| Domain examples | Consumer / retail, lifestyle apps, hospitality, creator-economy dashboards |

## 9. Minimal Restrained

> White canvas, black type, one accent, no chartjunk. The "less is more"
> tone — relies entirely on confident hierarchy.

| Aspect | Pick |
|---|---|
| Display typography | Sans (Inter, Segoe UI) at 24–48pt |
| Body typography | Same, regular, at 11pt |
| Surface | True white `#FFFFFF` |
| Accent | One — usually black `#0F172A` for type and ONE single hue (any) for the highlight |
| Density / ratio | 1.500 or 1.618 — strong hierarchy via size, since color isn't doing the work |
| Gridlines | None |
| Borders | None |
| Default signature | Composite KPI focus + everything else greyscale |
| Iconography | Omit, or outline-only at small sizes |
| Domain examples | Executive landing pages, primary-metric-with-context reports, dashboards where the story is the headline |

## 10. Corporate Cool

> The default for B2B SaaS, enterprise. Cool grey surface, slate type, one
> tech-feeling accent. Restrained but not stark.

| Aspect | Pick |
|---|---|
| Display typography | Sans (Segoe UI Semibold, Inter Semibold) at 22–32pt |
| Body typography | Same family at 11pt |
| Surface | Cool grey `#F1F5F9` |
| Accent | Slate `#334155` + cyan `#06B6D4`; slate-300 `#CBD5E1` for cues |
| Density / ratio | 1.333 |
| Gridlines | Solid `#E2E8F0`, low-opacity |
| Borders | 1px `#E2E8F0`, radius 8px |
| Default signature | Cyan accent on primary KPI/context; everything else slate |
| Iconography | Outlined, semi-bold stroke |
| Domain examples | B2B SaaS metrics, enterprise dashboards, internal tooling reports |

## 11. Scholarly Calm

> Stone surface, forest-green and soft-red accents, serif headings, no
> bright colors. Reads like an academic paper.

| Aspect | Pick |
|---|---|
| Display typography | Serif (Merriweather, EB Garamond) at 22–32pt |
| Body typography | Sans (Source Sans, Inter) at 11pt |
| Surface | Stone `#F5F5F4` |
| Accent | Forest `#1C5E47` + soft red `#C2615F`; stone-400 `#A8A29E` for cues |
| Density / ratio | 1.250 — gentle |
| Gridlines | Hairline rules, low-opacity |
| Borders | None or stone-300 hairline |
| Default signature | Serif headings + footnote-style annotations |
| Iconography | Outlined hairline; sparing use |
| Domain examples | Research dashboards, academic analytics, policy reporting, public-data visualizations |

## 12. Brand-Forward (template)

> When the user provides brand guidelines, treat the brand as the tone.
> This is a *template*, not a fixed entry — adapt to the brand's
> typography, palette, and signature elements.

| Aspect | Pick |
|---|---|
| Display typography | Brand display font (with system fallback chain) |
| Body typography | Brand body font (with Segoe UI fallback) at 11pt |
| Surface | Brand-neutral surface (off-white tinted toward brand if defined) |
| Accent | Primary brand color for the main emphasis; secondary for context |
| Density / ratio | Pick from brand mood — energetic brands → 1.5; restrained brands → 1.25 |
| Gridlines | Match brand's rule treatment (none / hairline / dotted) |
| Borders | Match brand's container treatment |
| Default signature | The brand's most recognizable visual move (logo placement, header band, accent stripe) |
| Iconography | Brand icon library if provided; otherwise pick a single style consistent with brand mood |
| Domain examples | Customer-facing dashboards with brand identity, white-label reports, marketing analytics for a specific brand |

---

## Remixing tones

Two tones can compose if the resulting choices are coherent:

- **Editorial Newsroom × FT Pink Financial** → serif display + tabular
  numerals + pink surface. Coherent. ✓
- **Industrial Cockpit × Bauhaus Catalog** → dark canvas + geometric type
  + primary-color accent. Coherent. ✓
- **Playful Energetic × Clinical Calm** → coral + teal? Pick one. ✗

When in doubt, pick ONE and apply it cleanly. A muddied tone reads as no
tone at all.

## Default tone by domain (when user is silent)

If the prompt is otherwise specific enough to design, use domain as a
recommendation signal for tone. If the overall prompt is vague (missing
audience, purpose, page count, or filtering depth), follow the root skill's
clarification workflow first and offer the domain-inferred tone as one option,
not as permission to proceed silently.

| Domain | Default tone |
|---|---|
| Finance / banking / audit | Corporate Cool or Editorial Newsroom |
| Healthcare / clinical | Clinical Calm |
| Operations / monitoring / NOC | Industrial Cockpit (dark) or Industrial Dense (light) |
| Retail / consumer / lifestyle | Playful Energetic |
| Engineering / observability / quant | Monospace Terminal or Industrial Dense |
| Executive landing / board reports | Minimal Restrained or Editorial Newsroom |
| B2B SaaS / enterprise | Corporate Cool |
| Research / academic / policy | Scholarly Calm |
| Brand-led (user provided guidelines) | Brand-Forward |

Surface the recommendation to the user or record it as an assumption in the
brief — *"Recommended tone: **Industrial Cockpit** (dark canvas, indigo +
cyan accents, dense data)."*
