# Operational Monitor Dashboard

> **Archetype**: Operational Monitor
> **Theme**: for generated reports, preserve `references/design/assets/base.json` safeguards while adapting `dataColors` to domain; for brownfield, preserve the existing theme unless a theme swap is requested
> **Canvas**: greenfield default FHD 1920 x 1080; preserve existing size for brownfield unless resize is approved · F-pattern
> **Scan-time target**: ≤ 5 seconds to "normal / not-normal"

---

## Job To Be Done

| Dimension | Value |
|-----------|-------|
| Primary user | Shift operator, on-call engineer, warehouse supervisor |
| Session mode | Continuous peripheral surveillance; burst attention on anomaly |
| Core question | "Is it me or is it broken?" |
| Success metric | Deviation detected < 5 s, before downstream alert fires |
| Failure signal | Operator misses a state change visible on the dashboard |
| Design implication | Passive consumption — minimize required clicks to zero |

---

## Core Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | **Freshness first** | Visible last-updated + staleness flag; stale data is worse than no data |
| 2 | **Thresholds ARE the design** | Explicit good / warn / bad bands on every metric |
| 3 | **Exceptions bubble up** | Sort by severity desc, never alphabetical |
| 4 | **Density fine, decoration not** | Pack information tightly; strip all chrome |
| 5 | **Alerts paged, not dashboarded** | Dashboard shows state; PagerDuty / email sends notifications |
| 6 | **State persists across refresh** | No jarring re-render; viewer tracks delta |
| 7 | **Four golden signals skeleton** | Digital: latency / traffic / errors / saturation; Physical: throughput / queue / exception-rate / asset-health |

---

## Layout Variants

Pick ONE variant based on the operational context from Step 0. Do NOT mix. Default to **A** only when signals genuinely tie — record the signal that drove your pick in `variant_rationale`.

| Signal (from operational context + brief) | Variant |
|---|---|
| Desk viewing (≤1.5 m), 4 golden signals, both surveillance and triage | **A. 4-Up Status** |
| Wallboard / TV-wall (≥3 m), peripheral surveillance, no detail expected on screen | **B. Wallboard** |
| Active incident response — exception queue is the working surface | **C. Incident-First** |

---

### Variant A — 4-Up Status (default, balanced surveillance + triage)

Status tiles, hero time series, and an exception detail row. Optimized for a desk monitor where the operator both surveilles and works the queue.

```text
┌──────────────────────────────────────────────────────────┐
│  ENV / REGION selectors    LAST UPDATED: 14:32 UTC  ⚠️   │  h=56
├──────────┬──────────┬──────────┬──────────────────────────┤
│ STATUS 1 │ STATUS 2 │ STATUS 3 │ STATUS 4                 │  h=120
│ ████░░░  │ ████████ │ ███░░░░  │ █████░░                  │  bullet-style
├──────────┴──────────┴──────────┴──────────────────────────┤
│  HERO TIME SERIES — shared X axis — 24 h window           │  h=280
│  ┌─latency──┐ ┌─traffic──┐ ┌─errors───┐ ┌─saturation─┐  │
│  │  ~∿~∿~   │ │  ~∿~∿~   │ │  ~∿~∿~   │ │  ~∿~∿~     │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
├──────────────────────────────┬────────────────────────────┤
│  EXCEPTION QUEUE             │  GEO / TOPOLOGY MAP        │  h=240
│  (table, severity desc)      │  (filled / shape / azure)  │
├──────────────────────────────┴────────────────────────────┤
│  source · cadence: 30 s · runbook: link                   │  h=24
└──────────────────────────────────────────────────────────┘
```

| Zone | Height | Content |
|------|--------|---------|
| Header | 56 px | Environment selector, last-updated, staleness icon |
| Status tiles | 120 px | 4 bullet-graph-style indicators |
| Hero time series | 280 px | 24 h window, shared X axis, 4 golden signals |
| Detail row | 240 px | Exception queue + geo/topology map |
| Footer | 24 px | Source, refresh cadence, runbook link |

---

### Variant B — Wallboard (TV-wall surveillance)

Two composite status tiles dominate the screen. No detail row. Designed to be
readable from across a room — peripheral attention catches state changes without
the operator looking directly at the screen. These are not bare one-measure
cards; each primary tile needs state color, threshold/reference context, and a
sparkline or banded status cue.

```text
┌──────────────────────────────────────────────────────────┐
│   ENV    LAST UPDATED: 14:32 UTC                     ⚠️  │  h=64
├──────────────────────────────┬───────────────────────────┤
│                              │                           │
│   PRIMARY HEALTH             │   PRIMARY VOLUME          │
│   (huge value + status        │   (huge value + sparkline │
│    color + threshold band)   │    + threshold band)      │  h=440
│                              │                           │
│   FONT: 72-96pt               │   FONT: 72-96pt           │
│                              │                           │
├──────────┬──────────┬────────┴───────┬───────────────────┤
│ Sub 1    │ Sub 2    │ Sub 3          │ Sub 4             │  h=160
│ (med)    │ (med)    │ (med)          │ (med)             │
├──────────┴──────────┴────────────────┴───────────────────┤
│  cadence: 30 s · last incident: 11:42                    │  h=32
└──────────────────────────────────────────────────────────┘
```

| Zone | Height | Content |
|------|--------|---------|
| Header | 64 px | Environment + last-updated, large font for room visibility |
| Primary tiles | 440 px | 2 composite status tiles: PRIMARY HEALTH, PRIMARY VOLUME — value font 72–96pt plus state/context cues |
| Sub tiles | 160 px | 4 secondary indicators, font ~36pt |
| Footer | 32 px | Refresh cadence + last-incident timestamp |

> **Dark wallpaper recommended** — set `page > background` and `wallpaper` to a near-black fill so alert colors pop in peripheral vision. **No exception table** — wallboards aren't where you triage; they tell you to go look at the triage screen.

---

### Variant C — Incident-First (queue dominant for active responders)

When the page is consumed by an on-call engineer working an active incident, the exception queue is the working surface. Status tiles shrink to a status strip.

```text
┌──────────────────────────────────────────────────────────┐
│   STATUS STRIP — 4 mini-tiles (h=56)            ⚠️ stale │  h=56
├──────────────────────────────────────────────────────────┤
│                                                          │
│   EXCEPTION QUEUE — full width                           │  h=400
│   ┌─severity─┬──when──┬──what──┬──where──┬──action──┐   │
│   │ Critical │ 2 m ago│ ...    │ region1 │ runbook→ │   │
│   │ Critical │ 4 m ago│ ...    │ region2 │ runbook→ │   │
│   │ Warning  │ 8 m ago│ ...    │ region1 │ runbook→ │   │
│   └──────────┴────────┴────────┴─────────┴──────────┘   │
├──────────────────────────────┬───────────────────────────┤
│  AFFECTED-ENTITY TIMELINE    │  RECENT DEPLOYS / CHANGES │  h=200
│  (sparkline grid for         │  (table, deploy events    │
│   selected entity)           │   correlated to incidents)│
├──────────────────────────────┴───────────────────────────┤
│  cadence: 30 s · runbook root: link                      │  h=24
└──────────────────────────────────────────────────────────┘
```

| Zone | Height | Content |
|------|--------|---------|
| Status strip | 56 px | 4 compact tiles + staleness flag — context, not the focus |
| Exception queue | 400 px | Full-width table sorted severity desc; columns: severity, when, what, where, action link |
| Correlation row | 200 px | Affected-entity timeline + recent-deploys / change events |
| Footer | 24 px | Cadence + runbook root link |

> The queue ROW must be selectable, and selecting a row should cross-filter the correlation row below — that's the whole interaction model. Configure `actionButton` per row (or a column with `Web URL` action) to jump straight to the runbook.

---

## Chart Selection

### Use

| Visual type | Role | Notes |
|-------------|------|-------|
| Bullet graph (simulated) | Status tile | `barChart` + `referenceLine` + banded `basicShape` behind |
| `lineChart` sparkline | Inline trends in tables | 120 × 40, all chrome off |
| Status tile | KPI state | `cardVisual` + `shape` + icon; CF drives color |
| Heat strip | Time × entity state | `matrix` with background CF, suppress numbers |
| Exception table | Alert queue | `tableEx` with CF icons + data bars, sort severity desc |
| Maps | Spatial state | `azureMap` preferred. If Azure Maps cannot render the geography because of tenant policy, region support, or environment constraints, use a non-map fallback such as a `tableEx` of locations with conditional formatting or a `clusteredBarChart` by region. Avoid the legacy `map` / `filledMap` visuals; `shapeMap` is a specialized shape-based visual, not a general Azure Maps substitute. |

### Do NOT Use

| Visual type | Reason |
|-------------|--------|
| `pieChart` / `donutChart` | Cannot show deviation; no threshold encoding |
| `scatterChart` | Requires analytical attention; wrong mode |
| `treemap` | Area encoding unreliable at glance |
| Analytical slicers | Operators don't slice; they surveille |
| `decompositionTree` | Analytical, not operational |

---

## Color & Typography

### Semaphore Palette

| State | Color | Hex | Shape | Icon |
|-------|-------|-----|-------|------|
| Good | Green | `#107C10` | ● | ✓ |
| Warning | Amber | `#FF8C00` | ◐ | ◐ |
| Critical | Red | `#D13438` | ▲ | ▲ |
| Unknown / stale | Grey | `#797775` | ○ | ? |

> **WCAG 1.4.1**: Never encode state with color alone — always pair with shape + icon.

> **Saturated reds**: Use calibrated, vivid reds for critical. Pastels fail to trigger peripheral attention.

### Typography by Viewing Distance

| Context | Body | Tile headline | Card value | Axis labels |
|---------|------|---------------|------------|-------------|
| Laptop (0.5 m) | 14 pt | 18 pt | 24 pt | 10 pt |
| TV wall (3 m) | 18 pt | 24 pt | 36 pt | 14 pt |

> **Dark background advisory**: NOC/control-room screens benefit from dark wallpaper (reduces bloom, makes alert colors pop). Not the default — configure via `page > background` and `wallpaper`.

---

## Freshness & Refresh

| Mechanism | PBI property | Constraint |
|-----------|-------------|------------|
| Auto page refresh | `autoPageRefreshInterval` | DirectQuery only; Premium 1 s min, shared 30 min |
| Change-detection refresh | `changeDetection` | Fires refresh only when upstream data changes |
| Last-updated display | `MAX(timestamp)` measure or `NOW()` | Show prominently in header |
| Stale-flag CF | Conditional formatting rule | Flag when elapsed > 2× expected cadence |

### Staleness Decision Table

| Expected cadence | Stale threshold | Action |
|------------------|-----------------|--------|
| Real-time (≤ 5 s) | > 15 s | Amber icon + "Data may be stale" |
| Near-real-time (30 s) | > 90 s | Red icon + suppress KPI values |
| Batch (hourly) | > 3 h | Grey overlay + "Awaiting refresh" |

---

## Interaction Design

| Pattern | Implementation | Notes |
|---------|---------------|-------|
| Mostly passive | No required clicks in normal operation | — |
| Page tooltip on status tile | 24 h sparkline + threshold bands | 320 × 240 tooltip page |
| Drill-through on red tile | Detail page with timeline + runbook | One click from anomaly to root cause |
| Shift bookmarks | Day / night context | Adjusts thresholds + background |
| Cross-highlight | Subtle; never rearranges layout | Avoid disorienting the peripheral viewer |

---

> Anti-patterns: see references/design/anti-patterns.md

---

## PBI Formatting Reference

### Status Tiles

| Property path | Value | Purpose |
|---------------|-------|---------|
| `cardVisual` background CF | Green / amber / red fill | State encoding |
| `shape` (backing plate) | Rectangle behind card | Colored status indicator |
| `visualHeader > show` | `false` | Clean tile surface |

### Time Series

| Property path | Value | Purpose |
|---------------|-------|---------|
| `lineChart > categoryAxis > axisType` | `DateTime` | Continuous time axis |
| `referenceLine` / `constantLine` | SLO threshold values | Draw good / warn / bad bands |
| Shared X axis | Align all charts to same 24 h window | Visual correlation |

### Exception Table

| Property path | Value | Purpose |
|---------------|-------|---------|
| `tableEx` CF icons | Severity icon set | Visual severity ranking |
| `tableEx` data bars | Metric magnitude | Quick magnitude scan |
| Sort | Severity desc | Worst-first ordering |

### Refresh & Page

| Property path | Value | Purpose |
|---------------|-------|---------|
| `autoPageRefreshInterval` | Per data source cadence | Live refresh (DQ/Premium) |
| `changeDetection` | `true` | Efficient refresh trigger |
| `page > background` | Optional dark fill | NOC screen optimization |
| `page > wallpaper` | Optional dark fill | NOC screen optimization |
| `border > show` | `false` | Clean tile boundaries |

---

## Decision Checklist

| # | Check | Pass? |
|---|-------|-------|
| 1 | Last-updated timestamp is visible and prominent | ☐ |
| 2 | Staleness flag fires when data exceeds expected cadence | ☐ |
| 3 | Every metric has explicit good / warn / bad thresholds | ☐ |
| 4 | State encoded with color + shape + icon (never color alone) | ☐ |
| 5 | Exception list sorted by severity desc | ☐ |
| 6 | Four golden signals represented | ☐ |
| 7 | Font sizes calibrated for actual viewing distance | ☐ |
| 8 | Zero clicks required for normal-state assessment | ☐ |
| 9 | Drill-through from red tile to detail + runbook | ☐ |
