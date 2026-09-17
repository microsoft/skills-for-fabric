# Interactivity & Storytelling

## Core Principles

1. **Shneiderman's mantra**: Overview first → zoom and filter → details on demand.
2. **Primary insight visible on load**: The primary insight is visible without any interaction.
3. **Every interaction must change something visible** — if clicking does nothing perceptible, remove the interaction.
4. **Never hide the primary insight behind a click** — interactions reveal depth, not the headline.
5. **State must be legible** — the user can always see which filters are active and what scope they're viewing.
6. **Match interaction budget to archetype** — executives get 1–2 clicks; analysts get full drill-down.

---

## Interaction Taxonomy

### 5 Clusters

| Cluster | PBI Features | When to Use | Common Pitfall |
|---|---|---|---|
| **Selection & Filtering** | Slicers, visual filters, cross-filter, cross-highlight, drillthrough | Narrow scope to a subset | Invisible filter state; user doesn't know what's excluded |
| **Navigation** | Page navigator, buttons, bookmarks, drill-through back button | Multi-page reports; guided flow | No breadcrumb; user gets lost |
| **Aggregation & Granularity** | Drill up/down, hierarchy expand, matrix expand/collapse | Dimensional exploration | Drill without clear hierarchy labels |
| **Annotation & Tooltip** | Tooltip pages, visual headers, report page tooltips, info buttons | Contextual detail on hover/focus | Tooltip as only path to critical data |
| **Provenance & Personalization** | Personalize visuals, persistent filters, export, subscribe | Self-service for power users | Feature overload on casual users |

---

## Descriptive Titles & Information Scent

| Guideline | Rule | Example |
|---|---|---|
| **Top inch earns its space** | Page title + 1 sentence or KPI row must convey the headline | "Revenue up 12% QoQ — driven by APAC expansion" |
| **Page titles as questions** | Frame what this page answers | "How is revenue trending by region?" |
| **Headlines as answers** | Visual titles state the finding, not the chart type | "APAC revenue grew 23% YoY" not "Revenue by Region" |
| **Navigation labels smell of destination** | Tab/button labels preview the content | "Regional Breakdown" not "Page 2" |
| **KPI context** | Always show comparison (vs target, vs prior period) | "12.3M vs 11.0M target (+11.8%)" |

---

## Cross-Filter Etiquette

| Mode | Behavior | When to Use | When to Avoid |
|---|---|---|---|
| **Highlight** | Dims non-selected; retains context | Default for most visuals; shows proportion | When exact filtered values are needed |
| **Filter** | Removes non-selected data entirely | Drill-through source; when context confuses | When user needs to see the whole picture |
| **None** | No cross-interaction | Independent visuals (e.g., KPI cards, slicers) | Rarely — most visuals should respond |

**Rules**:
- Cards and KPI visuals: set to **Filter** (they must update to show the selected subset).
- Context visuals (benchmark lines, reference charts): set to **None** (they provide fixed reference).
- Default for charts: **Highlight** — it preserves context while focusing attention.
- Configure via Edit Interactions in PBI Desktop for each source→target pair.

---

## Power BI Feature Grounding

| Feature | Purpose | Key Considerations |
|---|---|---|
| **Drill-through** | Navigate from summary to detail page with context | Always add a back button; limit to 1–2 drill-through fields |
| **Tooltip pages** | Rich hover detail replacing default tooltip | Keep small (320×240); load fast; don't put critical data here |
| **Edit Interactions** | Control cross-filter/highlight/none per visual pair | Review every pair; disable where interaction misleads |
| **Sync Slicers** | Keep slicers consistent across pages | Sync by field, not by visual; test edge cases |
| **Page Navigator** | Tab-style page switching | Label pages descriptively; limit to 5–7 visible tabs |
| **Buttons** | Custom navigation, bookmark triggers | Use for drill-through, bookmark, page nav; always show destination |
| **Bookmarks** | Saved states: filter + visibility + position | Use for narrative steps; don't exceed 8–10 bookmarks |
| **Bookmark Navigator** | Visual bookmark selector | Good for slideshow pattern; label each bookmark clearly |
| **Filters Pane** | Persistent filter panel | Hide for executive; show for analytical; pre-set defaults |
| **Personalize Visuals** | End-user can change measure/axis | Enable for analytical archetype only; confusing for casual users |

---

> Anti-patterns: see references/design/anti-patterns.md

---

## Slicer Placement Decision Table

| Placement | Layout | When to Use | Archetype |
|---|---|---|---|
| **Horizontal filter strip** | Top of page, full width, 48px tall | 2–3 key filters that apply to entire page | Executive, Narrative |
| **Vertical rail (left)** | Left column, 200px wide, full height | Analytical pages with F-pattern layout | Analytical |
| **Vertical rail (right)** | Right column, 200–240px wide | When left column is the primary visual area | Analytical, Comparative |
| **Collapsible panel** | Bookmark-toggled visibility | Many filters that are rarely changed | Operational, Executive |
| **Inline with visual** | Adjacent to the visual it controls | When filter scope is local, not page-wide | Analytical (per-section) |
| **Filter pane (built-in)** | PBI native filter pane | Power users who prefer the standard UX | Analytical |

**Never**: Place slicers in the top-left focal point (position x<200, y<100). That space belongs to the headline or primary KPI.

---

## Interaction Complexity Budget

| Complexity Level | Max Clicks to Insight | Features Allowed | Archetype |
|---|---|---|---|
| **Minimal** | 0–1 | Page load shows all; one optional slicer | Executive |
| **Guided** | 2–3 | Bookmark steps, page navigator, tooltips | Narrative |
| **Moderate** | 3–5 | Slicers, cross-filter, drill-through | Operational, Comparative |
| **Rich** | Unlimited | Full drill-down, personalize, export, cross-filter matrix | Analytical |

---

## Bookmark Design Rules

| Rule | Description |
|---|---|
| **Name descriptively** | "Q4 Revenue by Region" not "Bookmark 1" |
| **Capture minimal state** | Only capture filters + visibility that change; leave layout unchanged |
| **Test all transitions** | Every bookmark → bookmark transition must produce a coherent view |
| **Reset bookmark** | Always include a "Reset to default" bookmark |
| **Limit count** | 5–8 bookmarks max per report; beyond that, use pages instead |
| **Group by purpose** | Navigation bookmarks vs filter-state bookmarks — don't mix |
