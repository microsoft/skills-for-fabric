# Accessibility for Data Visualization

## Core Principles

1. **Color is never the sole signal** (WCAG 1.4.1) — always pair color with shape, label, icon, or pattern.
2. **Contrast floors are non-negotiable** — 4.5:1 for body text, 3:1 for large text and non-text elements.
3. **Alt text describes the insight, not the chart type** — "Revenue rose 12% QoQ" not "This is a bar chart."
4. **Keyboard navigable** — every interactive element reachable without a mouse.
5. **Reading order matches visual hierarchy** — tab order follows the logical story, not the creation order.
6. **Minimum 24×24px touch/click targets** — slicers, buttons, and interactive elements must be large enough.
7. **Design for 200% zoom** — layouts should not break or clip when zoomed.

---

## WCAG 2.1 / 2.2 Checklist for Dashboards

| SC | Title | Dashboard Implication | How to Satisfy |
|---|---|---|---|
| 1.1.1 | Non-text Content | Every chart needs alt text | Write insight-driven alt text in the visual's accessibility pane |
| 1.3.1 | Info and Relationships | Visual grouping must be programmatic | Use tab order and heading hierarchy, not just spatial proximity |
| 1.3.2 | Meaningful Sequence | Screen reader order matches visual layout | Set tab order in Selection pane to follow reading flow |
| 1.4.1 | Use of Color | Color must not be only differentiator | Add labels, icons, or patterns alongside color |
| 1.4.3 | Contrast (Minimum) | Body text ≥4.5:1 on background | Check every text/background pair; use WebAIM tool |
| 1.4.11 | Non-text Contrast | Chart bars, lines, icons ≥3:1 on background | Verify data marks against canvas color |
| 1.4.4 | Resize Text | Text readable at 200% zoom | Avoid fixed pixel sizes that clip on zoom |
| 2.1.1 | Keyboard | All functions keyboard-operable | Test full report with Tab, Enter, Escape only |
| 2.4.3 | Focus Order | Focus sequence is logical | Tab order in Selection pane matches reading order |
| 2.4.7 | Focus Visible | Focused element has visible indicator | PBI provides default focus ring; don't override with custom CSS |
| 2.5.8 | Target Size (Minimum) | Interactive targets ≥24×24px | Ensure slicer items, buttons, headers meet minimum |
| 4.1.2 | Name, Role, Value | Interactive elements have accessible names | Use visual titles and alt text; avoid decorative-only visuals |

---

## Alt Text Patterns

Four reusable templates for writing effective alt text:

### 1. Headline + Trend
```text
"[Measure] [direction] [amount] over [period].
Currently at [value], compared to [reference]."

Example: "Monthly revenue increased 12% over Q3.
Currently at $4.2M, compared to $3.8M target."
```

### 2. Chart Structure + Notable Finding
```text
"[Chart type] showing [measure] by [dimension].
[Key finding]: [specific data point or pattern]."

Example: "Bar chart showing sales by region.
Western region leads at $2.1M, 35% above the next closest."
```

### 3. Comparison Framing
```text
"Comparing [measure] across [N] [dimension items].
[Winner/loser]: [value]. [Runner-up]: [value]."

Example: "Comparing conversion rates across 4 channels.
Email leads at 4.2%. Social trails at 1.8%."
```

### 4. Data-as-Table Fallback
```text
"Data table: [column headers].
Row 1: [values]. Row 2: [values]. ..."

Use only when the above patterns don't apply or for
complex multi-measure visuals.
```

**Rules**:
- Lead with the insight, not the chart type.
- Include actual numbers when available.
- Keep under 150 characters for cards; under 300 for complex visuals.
- Update alt text when filters change the visual's story (use DAX-driven alt text).

---

## Keyboard Navigation Reference

| Key | Action in PBI Report |
|---|---|
| `Tab` | Move to next visual in tab order |
| `Shift+Tab` | Move to previous visual in tab order |
| `Enter` / `Space` | Activate / select focused element |
| `Escape` | Exit current visual / deselect |
| `Ctrl+Right/Left` | Move between data points within a visual |
| `Alt+Shift+F10` | Open visual header menu |
| `Alt+Shift+F11` | Open filter pane |
| `Ctrl+F6` | Move focus between report sections |
| `Shift+?` | Show keyboard shortcuts dialog |
| `Arrow keys` | Navigate within slicers, matrices, tables |

**Test protocol**: Navigate the entire report using only the keys above. Every visual, slicer, and button must be reachable and operable.

---

## WCAG Contrast Requirements

### Ratio Formula

```text
L = 0.2126·R + 0.7152·G + 0.0722·B   (relative luminance, linearized sRGB)
Ratio = (L_lighter + 0.05) / (L_darker + 0.05)
```

### Thresholds

| Element | Minimum Ratio | WCAG Level |
|---|---|---|
| Body text (<18pt regular, <14pt bold) | 4.5 : 1 | AA |
| Large text (≥18pt regular, ≥14pt bold) | 3.0 : 1 | AA |
| Non-text (icons, chart elements, borders) | 3.0 : 1 | AA |
| Enhanced body text | 7.0 : 1 | AAA |

### Worked Examples

| Foreground | Background | Ratio | AA Body | AA Large | AA Non-Text |
|---|---|---|---|---|---|
| `#333333` | `#FFFFFF` | 12.6 : 1 | ✅ | ✅ | ✅ |
| `#3182BD` | `#FFFFFF` | 4.2 : 1 | ❌ | ✅ | ✅ |
| `#6BAED6` | `#FFFFFF` | 2.4 : 1 | ❌ | ❌ | ❌ |
| `#E15759` | `#FFFFFF` | 3.7 : 1 | ❌ | ✅ | ✅ |
| `#FFFFFF` | `#08519C` | 7.9 : 1 | ✅ | ✅ | ✅ |

> Rule of thumb: mid-range hues on white often fail body-text contrast. Test every pair.

---

## Contrast Checking Workflow

### Tools

| Tool | Type | URL / Access |
|---|---|---|
| **WebAIM Contrast Checker** | Web | webaim.org/resources/contrastchecker |
| **TPGi Colour Contrast Analyser** | Desktop | Free download; includes eyedropper |
| **Stark** | Figma/Sketch plugin | For design-phase checking |
| **Browser DevTools** | Built-in | F12 → Elements → color picker shows ratio |

### Worked Examples

| Element | Foreground | Background | Ratio | Verdict |
|---|---|---|---|---|
| Axis label | `#767676` | `#FFFFFF` | 4.5:1 | ✅ AA body |
| Subtitle text | `#AAAAAA` | `#FFFFFF` | 2.3:1 | ❌ Fails all |
| Chart bar fill | `#4E79A7` | `#FFFFFF` | 4.6:1 | ✅ AA non-text |
| Card value | `#333333` | `#F2F2F2` | 11.3:1 | ✅ AAA |

**Process**: For every foreground/background pair in the design, compute or measure the ratio. Fix any pair below 3:1 for non-text, 4.5:1 for body text.

---

## Color Vision Deficiency (CVD) Section

- **Prevalence**: ~8% of males, ~0.5% of females have some form of color vision deficiency.
- **Most common**: Deuteranopia (red-green), followed by protanopia (red-green), then tritanopia (blue-yellow).
- **Safe palettes**: Okabe-Ito (8 colors), viridis, cividis — all pass all three CVD types.
- **Simulation**: Use Coblis, Viz Palette, or Chrome DevTools (Rendering → Emulate vision deficiencies) to preview before shipping.
- **Rule**: If any two colors in your palette become indistinguishable under simulation, add a secondary channel (label, shape, pattern).

---

## Power BI Accessibility Grounding

| Feature | Purpose | How to Configure |
|---|---|---|
| **Alt text field** | Describes visual to screen readers | Visual → Format → General → Alt text (static or DAX expression) |
| **Tab order** | Controls keyboard navigation sequence | View → Selection pane → drag visuals into logical reading order |
| **Visual headers** | Provide interactive menu access | Enabled by default; don't disable unless decorative visual |
| **Theme contrast** | Global text/background contrast | Set `foreground` and `background` in theme JSON with ≥4.5:1 |
| **High-contrast mode** | OS-level high contrast support | PBI respects Windows High Contrast; test with it enabled |
| **Show as table** | Exposes underlying data in tabular form | Enabled by default; provides data fallback for screen readers |
| **Bookmarks as a11y escape** | Lets users jump to an accessible layout | Create a "data table view" bookmark as an alternative |
| **Focus mode** | Enlarges a single visual to full screen | Keyboard: Enter on visual → focus mode available |

---

## Archetype Accessibility Priorities

| Archetype | Priority A11y Concern | Rationale |
|---|---|---|
| **Executive** | Alt text quality | Often consumed via email or read aloud by assistants; alt text IS the content |
| **Operational** | Keyboard + target size | Used in control rooms / kiosks; mouse may not be available |
| **Analytical** | Show as table | Power users need raw data access; screen readers can navigate tables |
| **Narrative** | Reading order | Story depends on sequence; wrong tab order breaks the narrative |
| **Comparative** | CVD-safe color + non-text contrast | Color carries the comparison signal; must survive CVD simulation |

---

> Anti-patterns: see references/design/anti-patterns.md

---

## Accessibility Testing Checklist

Run through this before publishing any report:

| # | Test | Method | Pass Criteria |
|---|---|---|---|
| 1 | Keyboard-only navigation | Unplug mouse; Tab through entire report | Every visual, slicer, and button reachable |
| 2 | Screen reader | NVDA or Narrator on Windows | All visuals announced with alt text; reading order logical |
| 3 | Zoom 200% | Ctrl+= in browser / PBI Service | No clipping, overlapping, or text truncation |
| 4 | High contrast mode | Windows Settings → High Contrast | All visuals remain legible; no invisible elements |
| 5 | CVD simulation | Chrome DevTools → Emulate vision deficiency | All color-coded information distinguishable |
| 6 | Contrast ratios | WebAIM Contrast Checker on all text pairs | Body ≥4.5:1; large ≥3:1; non-text ≥3:1 |
| 7 | Tab order audit | View → Selection pane | Order matches visual reading flow (top-left → bottom-right) |
| 8 | Alt text review | Check every visual's accessibility pane | Insight-driven text present; no "chart" or "image" |
| 9 | Touch target size | Measure slicer items, buttons | All ≥24×24px |
| 10 | Data table fallback | Right-click → Show as table on each visual | Table renders with correct headers and values |

---

## DAX-Driven Alt Text

For visuals where the insight changes with filters, use a DAX measure for dynamic alt text:

```text
Alt Text =
VAR _revenue = FORMAT([Total Revenue], "$#,##0.0,,M")
VAR _change = FORMAT([Revenue YoY %], "+0.0%;-0.0%")
VAR _period = SELECTEDVALUE(Calendar[Quarter])
RETURN
    "Revenue is " & _revenue & " in " & _period & ", " & _change & " year over year."
```

**Rules for DAX alt text**:
- Keep under 300 characters after evaluation.
- Always include the key measure value and its context (period, filter).
- State direction: "up", "down", "flat" — not just the number.
- Test with actual slicer selections to verify sensible output in all states.
