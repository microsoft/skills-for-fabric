# Color Strategy

## Core Principles

1. **Palette family matches data family** — sequential for ordered, diverging for ±, categorical for nominal.
2. **Never rainbow on ordered data** — rainbow has no perceptual order; it misleads.
3. **Color is never the sole channel** — always pair with shape, label, or pattern (WCAG 1.4.1).
4. **Cap categorical palettes at 7–8 hues** — beyond that, colors become indistinguishable.
5. **Restraint beats vibrance** — most of the canvas should be neutral; color draws the eye to what matters.
6. **Contrast is non-negotiable** — every text-on-background pair must meet WCAG AA.
7. **Reserve semantic colors** — green/red/amber carry meaning; don't waste them on decoration.

---

## Palette Reference Tables

### Sequential Palettes

| Name | Hex Ramp (5-step) | CVD Safe | Use |
|---|---|---|---|
| **Blues** (ColorBrewer) | `#EFF3FF` `#BDD7E7` `#6BAED6` `#3182BD` `#08519C` | ✅ All | Default sequential; low-to-high magnitude |
| **YlOrRd** (ColorBrewer) | `#FFFFB2` `#FECC5C` `#FD8D3C` `#F03B20` `#BD0026` | ⚠️ Deutan marginal | Heat / urgency encoding |
| **Viridis** | `#440154` `#3B528B` `#21908C` `#5DC863` `#FDE725` | ✅ All | Perceptually uniform; print-safe |
| **Cividis** | `#002051` `#3F5B75` `#8E8E52` `#CBBE2D` `#FDEA45` | ✅ All + grayscale | Best CVD-safe option; blue-yellow only |

### Diverging Palettes

| Name | Low → Mid → High | Midpoint | CVD Safe |
|---|---|---|---|
| **RdBu** | `#B2182B` → `#F7F7F7` → `#2166AC` | Neutral white/grey | ✅ |
| **BrBG** | `#8C510A` → `#F5F5F5` → `#01665E` | Neutral white/grey | ✅ |
| **PiYG** | `#C51B7D` → `#F7F7F7` → `#4D9221` | Neutral white/grey | ⚠️ Protan marginal |

### Categorical Palettes

| Name | Colors (hex) | Count | CVD Safe |
|---|---|---|---|
| **Okabe-Ito** | `#E69F00` `#56B4E9` `#009E73` `#F0E442` `#0072B2` `#D55E00` `#CC79A7` `#000000` | 8 | ✅ All |
| **Set2** (ColorBrewer) | `#66C2A5` `#FC8D62` `#8DA0CB` `#E78AC3` `#A6D854` `#FFD92F` `#E5C494` `#B3B3B3` | 8 | ✅ |
| **Tableau 10** | `#4E79A7` `#F28E2B` `#E15759` `#76B7B2` `#59A14F` `#EDC948` `#B07AA1` `#FF9DA7` `#9C755F` `#BAB0AC` | 10 | ⚠️ Deutan pair clash at 9-10 |

---

## Color Vision Deficiency (CVD) and WCAG Contrast

> Contrast and CVD: see references/design/accessibility.md

---

## Semantic Color Rules

| Color | Default Meaning | Rule |
|---|---|---|
| **Green** | Good / positive / on-target | Reserve for favorable status only |
| **Red** | Bad / negative / critical | Reserve for unfavorable status only |
| **Amber/Yellow** | Warning / approaching threshold | Use between green and red |
| **Grey** | Neutral / context / benchmark | Default for non-highlighted elements |
| **Blue** | Informational / primary brand accent | Safe default when no semantic load |

**Constraints**:
- Never flip semantics (green = bad) without explicit user instruction.
- Never use red and green as the only differentiator — pair with icon or label.
- Cultural caveat: in some East Asian financial contexts, red = gain. Note if the report targets those markets.

---

## Power BI Theme Grounding

| Theme Key | Purpose | Notes |
|---|---|---|
| `dataColors` | Ordered list of categorical series colors | First 8 entries matter most |
| `good` / `neutral` / `bad` | Sentiment triplet | Map to green / grey / red |
| `firstLevelElements` (`foreground`) | Primary text and foreground marks | Must pass 4.5:1 on `background` |
| `secondLevelElements` (`foregroundNeutralSecondary`) | Axis labels, subtitles, secondary text | Must pass contrast on `background` / `secondaryBackground` |
| `thirdLevelElements` (`backgroundLight`) | Gridlines, subtle rules, low-emphasis fills | Keep visible on page and visual surfaces |
| `fourthLevelElements` (`foregroundNeutralTertiary`) | Dimmed labels and tertiary foreground | Use only for non-critical context |
| `background` | Page canvas | Usually white or near-white |
| `secondaryBackground` (`backgroundNeutral`) | Visual/container secondary fill, disabled fills | Often slightly offset from `background` |
| `tableAccent` | Accent lines, borders | Use for gridlines, dividers |

Per-visual color choices: `dataPoint.fill.solid.color`, `labels.color`,
`title.fontColor`, and visual-specific conditional formatting rules (not custom
theme JSON).

---

## Color Assignment Strategy

Assign colors per-page so visuals are visually linked when they share a
measure and distinct when they don't.

### Rules

1. **Same measure → same color.** If a card shows "Total Fights" with a sky
   blue accent bar, the line chart trending Total Fights should also be sky
   blue (via `defaultColor`). This creates a visual link — the card and its
   trend chart tell the same story.

2. **Breakdown of a measure → gradient of that color.** A bar chart showing
   Total Fights *by Weight Class* uses a light→dark gradient of sky blue
   (via `dataPoint.fill` FillRule). The gradient ties the breakdown to its
   parent measure while the value shading reinforces the sort order.

3. **Different measure → different hue.** A bar chart showing Events by
   Country uses a different palette hue than a Fights chart. Pick the next
   unused color from the theme's `dataColors` array.

4. **Cards consume palette slots first** in reading order (top-left →
   right). Charts derive from or take the next available slot.

### Example (4 cards + 3 charts on one page)

| Visual | Measure | Color | Source |
|--------|---------|-------|--------|
| Card 1: Total Events | count | `dataColors[0]` #D55E00 | Slot 0 |
| Card 2: Total Fights | measure | `dataColors[1]` #56B4E9 | Slot 1 |
| Card 3: Total Fighters | count | `dataColors[2]` #009E73 | Slot 2 |
| Card 4: Finish Rate | rate | `dataColors[3]` #0072B2 | Slot 3 |
| Line: Fights by Year | Total Fights | #56B4E9 | **matches Card 2** |
| Bar: by Weight Class | Total Fights breakdown | #56B4E9 gradient | **gradient of Card 2** |
| Bar: by Country | Total Events breakdown | #D55E00 gradient | **gradient of Card 1** |

### Implementation

- **Cards**: set accent bar color via `accentBar.color` (Literal hex)
- **Line/area charts**: set `dataPoint.defaultColor` to match the card
- **Bar charts**: set `dataPoint.fill` FillRule `linearGradient2` with min
  (light tint, ~50% toward white) and max (base color). Use `Literal` hex —
  `ThemeDataColor` does not work inside FillRule.
- **Data labels on charts**: always use neutral dark (#252423), never the
  accent color — colored labels clash with the chart elements

---

## Archetype Calibration

| Archetype | Palette Strategy | Typical Colors |
|---|---|---|
| **Executive** | 3 semantic (green/amber/red) + 1 brand accent + grey | 5 total |
| **Operational** | RAG (red/amber/green) + status grey + 1 highlight | 5 total |
| **Analytical** | Full categorical (Okabe-Ito or Set2) + sequential for heatmaps | Up to 8 |
| **Narrative** | 1 highlight + grey context | 2–3 total |
| **Comparative** | Diverging (RdBu) or paired categorical | 4–6 total |

---

> Anti-patterns: see references/design/anti-patterns.md

---

## Highlight Pattern

Use color to draw attention to the key data point while greying out context:

| Element | Color Treatment | Example |
|---|---|---|
| **Highlighted bar/line** | Saturated brand or semantic color | `#3182BD` (blue) or `#E15759` (red) |
| **Context bars/lines** | Light grey | `#D9D9D9` or `#E0E0E0` |
| **Reference line** | Medium grey, dashed | `#999999`, 1px dashed |
| **Background** | White or near-white | `#FFFFFF` |

This pattern works across archetypes. In Narrative reports, the highlight is the thesis.
In Analytical reports, the highlight is the selected subset.

---

## Conditional Formatting Techniques

Use conditional formatting when it reinforces the page's main comparison,
threshold, or exception pattern.

| Technique | Use on | Effect |
|---|---|---|
| **Per-series color** | Bar/column charts | Each category bar gets a distinct color when category identity matters |
| **Threshold color** | KPI cards | Background or font color changes based on good/neutral/bad thresholds |
| **Data bars** | Table numeric columns | In-cell horizontal bars show magnitude at a glance |
| **Icon sets** | Table status columns | Pass/fail or good/warn/bad status becomes scannable |
| **Color gradient** | Matrix cells, heatmaps | Min→mid→max color scale reveals patterns |
| **Highlight + grey** | Any chart | One series in accent color, rest in `#BDBDBD` — draws the eye to the insight |

For implementation mechanics, hand these choices to the `authoring` mode.

---

## Color Assignment Rules

| Rule | Description |
|---|---|
| **Consistent mapping** | Same category = same color across every page and visual in the report |
| **Semantic priority** | If a category has inherent meaning (e.g., "Critical"), use semantic color first |
| **Order follows palette order** | First series = first `dataColors` entry; don't skip indices |
| **Legend = data order** | Legend should sort to match the visual order of data elements |
| **Conditional formatting sparingly** | Only for traffic-light status, heatmaps, or threshold-based alerts |
| **No color for decoration** | Every color applied must encode information |

---

## Palette Selection Decision Tree

```text
What type of data?
├── Nominal / categorical (no order)
│   ├── ≤8 categories → Okabe-Ito or Set2
│   └── >8 categories → Group into "Other"; limit to 7-8 hues
├── Ordinal / sequential (low→high)
│   ├── Needs CVD safety → Cividis or Viridis
│   └── Standard → Blues (ColorBrewer)
├── Diverging (±from midpoint)
│   ├── Needs CVD safety → BrBG
│   └── Standard → RdBu
└── Semantic (status / sentiment)
    └── Use theme `good` / `neutral` / `bad` keys
```
