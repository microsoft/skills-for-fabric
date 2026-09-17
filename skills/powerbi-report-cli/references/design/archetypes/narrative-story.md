# Narrative / Data Story

> **Archetype**: Narrative / Data Story
> **Theme**: for generated reports, preserve `references/design/assets/base.json` safeguards while adapting `dataColors` to domain; for brownfield, preserve the existing theme unless a theme swap is requested
> **Canvas**: greenfield default FHD 1920 x 1080; preserve existing size for brownfield unless resize is approved · 7/5 asymmetric layout
> **Success metric**: Reader can restate the argument in one sentence

---

## Job To Be Done

| Dimension | Value |
|-----------|-------|
| Primary user | Board member, senior stakeholder, external audience |
| Session trigger | CFO presents: "Revenue missed $42M. Here are three drivers. Here's the plan." |
| Mode | Author-driven argument; reader is convinced, not exploring |
| Structure | Multi-page, paced, annotation-rich |
| Success metric | Reader restates the argument in one sentence |
| Failure signal | Reader asks "so what?" after viewing the page |
| Design implication | Minimal interactivity; content is curated, not generated on the fly |

---

## Core Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | **Thesis in the title** | "Q3 revenue missed $42M, driven by EMEA enterprise" — not "Revenue Overview" |
| 2 | **Annotations carry the argument** | Arrows, callouts, reference lines, shaded periods do the explaining |
| 3 | **One anchor chart per page** | Single visual that proves the page's thesis |
| 4 | **Reveal pacing** | Bookmarks or page sequence control what reader sees when |
| 5 | **Highlight + grey context** | Hero data in brand color, everything else grey |
| 6 | **Reader interactivity minimal** | No slicers on main narrative path |
| 7 | **Chart chosen for the point** | Slope for rank change, waterfall for bridge, dumbbell for before/after |

---

## Structural Patterns (Segel & Heer)

| Pattern | Flow | PBI implementation |
|---------|------|--------------------|
| **Martini glass** | Linear narrative → open exploration at end | Pages 1–N guided; final page has slicers + filters |
| **Interactive slideshow** | Linear steps with optional side trips | `pageNavigator` + drill-through from each step |
| **Drill-down story** | Hub page with spoke detail pages | Hub has `actionButton` links to each spoke |

### Decision Table: Which Pattern?

| If the story… | Use | Because |
|---------------|-----|---------|
| Has a single linear argument | Martini glass | Reader follows one path to conclusion + can explore |
| Has parallel threads (3 drivers) | Interactive slideshow | Reader can branch to any driver |
| Centers on one entity with many facets | Drill-down story | Hub gives overview; spokes give depth |

---

## Layout Variants

Pick ONE variant based on the story's structure from Step 0. Do NOT mix. Default to **A** only when signals genuinely tie — record the signal that drove your pick in `variant_rationale`.

| Signal (from story structure + brief) | Variant |
|---|---|
| Single anchor chart with a side annotation panel; balanced "show + tell" | **A. 7/5 Split** |
| Multiple short narrative beats stacked vertically; reader scrolls/pages | **B. Single-Column-Scroll** |
| One dominant chart that argues the whole point; annotations on the chart itself | **C. Annotated-Hero** |

---

### Variant A — 7/5 Split (default, balanced argument)

Anchor chart on the left (7/12 width), annotation panel on the right (5/12 width), body text below. Classic "show on the left, tell on the right".

```text
┌──────────────────────────────────────────────────────────┐
│  PAGE TITLE: thesis sentence (28-32pt)                   │  h=56
│  subtitle: context / date range (14pt)                   │
├──────────────────────────────┬───────────────────────────┤
│                              │                           │
│  ANCHOR CHART                │  ANNOTATION PANEL         │
│  (7/12 width)                │  (5/12 width)             │  h=340
│                              │  • callout boxes          │
│  Hero in brand color         │  • arrows to chart        │
│  Rest in grey                │  • key numbers            │
│                              │                           │
├──────────────────────────────┴───────────────────────────┤
│  BODY TEXT                                               │
│  What the chart shows → Why it matters → So what / action│  h=160
│  (11-12pt, ~1.4 line height)                             │
├──────────────────────────────────────────────────────────┤
│  [← Prev]                                    [Next →]    │  h=48
└──────────────────────────────────────────────────────────┘
```

| Zone | Height | Content |
|------|--------|---------|
| Title block | 56 px | Thesis sentence + subtitle |
| Chart + annotations | 340 px | 7/12 anchor chart + 5/12 annotation panel |
| Body text | 160 px | Narrative: shows → matters → so-what |
| Navigation | 48 px | Prev / Next buttons (or page navigator) |

---

### Variant B — Single-Column-Scroll

Vertical narrative beats stacked top to bottom, each one a small chart + paragraph. Use when the story has 3–5 sequential points that each deserve their own frame.

```text
┌──────────────────────────────────────────────────────────┐
│  PAGE TITLE: thesis sentence (28-32pt)                   │  h=56
├──────────────────────────────────────────────────────────┤
│  BEAT 1 — sub-thesis (16pt SemiBold)                     │
│  ┌──────────────────────┐  Body: ~3 sentences explaining │  h=160
│  │  small chart 480w    │  what the chart shows and why  │
│  └──────────────────────┘  it advances the argument.     │
├──────────────────────────────────────────────────────────┤
│  BEAT 2 — sub-thesis                                     │
│  ┌──────────────────────┐  Body text continuing the      │  h=160
│  │  small chart 480w    │  narrative.                    │
│  └──────────────────────┘                                │
├──────────────────────────────────────────────────────────┤
│  BEAT 3 — sub-thesis                                     │
│  ┌──────────────────────┐  Body text — closing argument  │  h=160
│  │  small chart 480w    │  or call to action.            │
│  └──────────────────────┘                                │
├──────────────────────────────────────────────────────────┤
│  [← Prev]                                    [Next →]    │  h=48
└──────────────────────────────────────────────────────────┘
```

| Zone | Height | Content |
|------|--------|---------|
| Title block | 56 px | Thesis sentence |
| Beat 1–3 | 160 px each | Sub-thesis + small chart (left ~480px) + body text (right) |
| Navigation | 48 px | Prev / Next buttons |

> Each beat is self-contained — the reader can stop after any beat with a complete thought. **Maximum 3 beats per page**; beyond that, split to a new page in the sequence.

---

### Variant C — Annotated-Hero

A single dominant chart fills most of the canvas. All explanation lives on the chart itself: arrows, callout boxes, shaded regions, reference lines. Use when the chart's shape IS the argument.

```text
┌──────────────────────────────────────────────────────────┐
│  PAGE TITLE: thesis sentence (28-32pt)                   │  h=56
├──────────────────────────────────────────────────────────┤
│                                                          │
│   HERO CHART — full width                                │
│                                                          │
│   ┌─ shaded period: "promotion" ─┐                       │  h=480
│   │  ~∿~∿~∿~∿~ ↗ "+18% lift"    │                       │
│   │  ~∿~∿~/                     │  ← arrow + callout    │
│   │     ↑ inflection             │                       │
│   │     "Aug launch"             │                       │
│   └──────────────────────────────┘  ── reference line ── │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  CALLOUT — one-sentence interpretation                   │  h=80
├──────────────────────────────────────────────────────────┤
│  [← Prev]                                    [Next →]    │  h=48
└──────────────────────────────────────────────────────────┘
```

| Zone | Height | Content |
|------|--------|---------|
| Title block | 56 px | Thesis sentence |
| Hero chart | 480 px | Single chart with on-chart annotations: arrows, callouts, shaded periods, reference lines |
| Callout | 80 px | Textbox: one-sentence interpretation reinforcing the title |
| Navigation | 48 px | Prev / Next buttons |

> Annotation z-order: shaded regions back, chart middle, arrows + callouts front. Use the brand color for the data being argued and grey for everything else — preattentive highlight does the lifting.
>
> Callouts must interpret the chart shape, threshold, anomaly, or period change.
> Do not use callout boxes for a bare metric that simply repeats the adjacent
> visual's measure.

---

## Chart Selection

### Choosing the Anchor Chart

| If the point is… | Use | Why |
|------------------|-----|-----|
| Trend over time | `lineChart` | Position along common scale |
| Rank change between periods | Slope chart (simulated `lineChart`) | Crossing lines show overtakes |
| Additive decomposition | `waterfallChart` | Bridge from start to end |
| Before / after comparison | Dumbbell (simulated `barChart`) | Gap = change magnitude |
| Part-to-whole at one moment | Stacked bar (single bar) | Length encoding |
| Distribution of a metric | Histogram (binned `columnChart`) | Shape of distribution |

### Do NOT Use

| Visual type | Reason |
|-------------|--------|
| Dense dashboards (> 3 visuals) | Narrative has ONE anchor per page |
| Unannotated charts | Without annotations, chart doesn't argue |
| Matrix with > 2 measures | Too analytical; belongs in canvas archetype |
| Slicer-heavy layouts | Reader doesn't explore; author curates |

---

## Annotation Techniques

| Technique | PBI implementation | Use case |
|-----------|--------------------|----------|
| Arrow pointing to data | `shape` with arrowhead property | "This is the inflection point" |
| Callout text box | `textbox` with filled background | Key number or quote |
| Reference line | `axis > referenceLine` | Target, SLA, benchmark |
| Shaded region | `basicShape` (low-opacity rectangle) behind chart via z-order | "This period was promotional" |
| Preattentive highlight | `dataColors` override: one series brand, rest grey | Focus on the subject of the sentence |
| Direct data label | Labels on hero data point only | Call out the exact value |

### Annotation Z-Order

| Layer | Content |
|-------|---------|
| Back | Shaded regions (`basicShape`, 10–20% opacity) |
| Middle | Chart visual |
| Front | Arrows, callout textboxes, direct labels |

---

## Color & Typography

### Highlight + Grey Context Palette

| Role | Color | Hex |
|------|-------|-----|
| Hero / subject | Brand primary | `dataColors[0]` from theme |
| Context / other series | Grey | `#9E9E9E` to `#BDBDBD` |
| Annotation text background | Light fill | `#F5F5F5` at 90% opacity |
| Negative callout | Semantic red | `#D13438` |

> **Rule**: Maximum two non-grey colors on any page. If three things need highlighting, the page has too many points.

### Typography

| Element | Size | Weight | Notes |
|---------|------|--------|-------|
| Page title (thesis) | 28–32 pt | Bold | Must be a complete sentence |
| Subtitle | 14 pt | Regular | Date range, context |
| Body prose | 11–12 pt | Regular | ~1.4 line height; narrative is read |
| Annotation callout | 10 pt | SemiBold | Inside callout box |
| Axis labels | 9 pt | Regular | Minimal, unobtrusive |
| Footer / source | 9 pt | Light | Bottom of page |

---

## Interaction Design

Interactivity is minimal and guided — the author controls pacing.

| Pattern | PBI mechanism | Notes |
|---------|--------------|-------|
| Page sequence | `pageNavigator` or Prev/Next `actionButton` | Linear story flow |
| Staged reveals | Bookmarks triggered by `actionButton` | Show data progressively |
| "Next" affordance | Button always visible, labeled with next page's thesis | Reader knows what comes next |
| Page tooltips | Supporting detail on hover | Don't clutter the page |
| Smart Narrative | `aiNarratives` visual | Drafts "what changed"; agent usually rewrites |
| Martini-glass bowl | Slicers on final exploration page ONLY | Not on narrative path |

### Do NOT Use on Narrative Pages

| Pattern | Why |
|---------|-----|
| Slicers | Author controls the story, not the reader |
| Cross-filter webs | Unpredictable state changes break pacing |
| Drill-down | Reader might lose their place in the argument |

---

> Anti-patterns: see references/design/anti-patterns.md

---

## PBI Formatting Reference

### Text & Annotation Visuals

| Visual | Key properties | Purpose |
|--------|---------------|---------|
| `textbox` | Font, background fill, padding | Thesis titles, body prose, callouts |
| `shape` / `basicShape` | Fill, opacity, arrowhead, z-order | Arrows, shaded regions, annotation backing |
| `image` | URL or embedded, alt text | Supporting imagery (use sparingly) |

### Navigation

| Visual | Key properties | Purpose |
|--------|---------------|---------|
| `actionButton` | Action: `PageNavigation` / `Bookmark` / `Drillthrough` | Prev / Next / reveal |
| `pageNavigator` | Style, position | Linear page flow |
| `bookmarkNavigator` | Bookmark group | Staged reveal sequence |

### Narrative Intelligence

| Visual | Key properties | Purpose |
|--------|---------------|---------|
| `aiNarratives` | Summarize key changes | Auto-generated insight (agent rewrites) |

### Page-Level

| Property path | Value | Purpose |
|---------------|-------|---------|
| `page > displayName` | Thesis sentence (abbreviated) | Reads as TOC in page tabs |
| `page > tooltip > tooltipType` | `ReportPage` | Enable custom tooltip pages |
| `dataColors` override | Brand + grey | Highlight + context palette |
| `referenceLine` | Target / benchmark value | Draw comparison baseline |

---

## Decision Checklist

| # | Check | Pass? |
|---|-------|-------|
| 1 | Every page title is a thesis sentence | ☐ |
| 2 | One anchor chart per page, annotated | ☐ |
| 3 | Body text explains: shows → matters → so-what | ☐ |
| 4 | Palette is highlight + grey (max 2 non-grey colors) | ☐ |
| 5 | Navigation (Prev/Next) always visible | ☐ |
| 6 | No slicers on narrative pages | ☐ |
| 7 | Annotations use arrows, callouts, or reference lines | ☐ |
| 8 | Page `displayName` reads as table of contents | ☐ |
| 9 | Story structure follows Segel & Heer pattern | ☐ |
| 10 | Reader can restate argument after viewing | ☐ |
