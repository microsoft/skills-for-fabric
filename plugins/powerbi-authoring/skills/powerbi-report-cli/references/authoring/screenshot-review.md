# Screenshot Review

Use this file after `powerbi-desktop` screenshot capture and before reporting completion for any rendered-output change.

## Review workflow

Perform an independent screenshot review using:

1. The screenshot image file paths.
2. A short description of what changed and what should be visible.
3. The checklist and troubleshooting table below.

Do not rely only on structural validation. Fix any issue found in screenshots, then repeat the PBIR validate → Desktop reload → screenshot review loop.

> **Screenshot scope:** Each screenshot captures the report page **AND** the right-hand filter pane (`outspacePane`) when the filter pane is enabled and expanded. Filter pane and filter card (`filterCard`) chrome are formattable surfaces — review them alongside on-page visuals (background color, border, font color, search/checkbox treatment, applied vs available states). See [filter-pane.md](filter-pane.md) for the formatting model.

## Checklist

### Layout and visibility

- Are all visuals fully visible with no edge clipping or unintentional overlap?
- Does each page have a visible descriptive title/header?
- Do top-bar slicers sit to the right of the title instead of replacing the title anchor?
- Are titles, labels, values, subtitles, and legends readable and not truncated?
- Do cards and KPIs show complete values, not ellipses or missing digits?
- Do textboxes render without scrollbars?
- Are slicers fully visible, including lower portions and dropdown areas?
- Is spacing intentional, with no accidental large gaps?

### Data rendering

- Do charts show actual bars, lines, or points rather than empty frames?
- Do tables and matrices have data rows, not just headers?
- Are any visuals showing error icons, "Can't display", or "Requires X fields"?
- Are blank, null, or dash values expected?
- Do slicers show selectable values?

### Formatting and theming

- Are background colors and theme applied, not default white/gray?
- Do font colors contrast against their backgrounds?
- Do chart colors contrast with card/page backgrounds and distinguish series?
- Does each measure follow `Design Brief.color_map` consistently across visuals?
- Are card gutters/padding intentional, with no accidental white padding from wildcard theme styles?
- Is conditional formatting visually present where expected?
- Do border radius, shadows, and other effects render as intended?

> **Note:** Some formatting properties are valid JSON but have no visible effect for a visual type. If a property is not rendering, verify it with `powerbi-report-author formatting describe-object <type> <object>`.

## Common screenshot problems

| Symptom | Likely cause | Fix |
|---|---|---|
| Visual shows error icon | Wrong entity/property names in `queryState` | Check TMDL for correct table/column names. |
| Chart frame with no data | Missing or wrong role bindings | Verify roles with `powerbi-report-author catalog describe <type>`. |
| Card/KPI value shows `...` or cutoff | Font too large for visual size, or card resized without font adjustment | Read `position.height`/`width`, then increase size or reduce `value.fontSize`; recheck `label.fontSize` and padding. |
| Textbox shows scrollbar or clipped title | Textbox height did not account for theme/VCO padding | Increase height with `max(18, ceil(fontSize * 25/16)) + padding_top + padding_bottom`, or add textbox-specific zero padding. |
| Redundant subtitle appears | Auto-generated or hand-authored subtitle repeats the title | Hide it or replace with useful context such as date range, units, active filter, baseline, or caveat. |
| Text invisible on dark background | Font color matches background | Set explicit contrasting `fontColor`. |
| Visual overlaps another | Position coordinates conflict | Recalculate `x`, `y`, `width`, and `height`. |
| Slicer hidden behind chart/table | Header band overlaps next row, or slicer height is too small | Re-read `references/authoring/slicers.md`, recompute height, and reserve a full top/header band or rail. |
| Card has white gutters/padding | Wildcard theme padding/background applied to cards | Add/restore `cardVisual`-specific padding, spacing, and background overrides. |
| Same measure uses different colors | `Design Brief.color_map` was not applied consistently | Re-read the brief and set each measure-bound visual to the mapped color. |
| Blank page | Page has no visuals, or visuals have `z < 0` | Check visual directories and z-order. |
| Slicer shows no items | Wrong column binding or filter conflict | Verify the slicer's `queryState` column has data. |
| Bars/columns invisible despite data | `dataPoint.fill` without a selector | Use `defaultColor` for base color, or add a `metadata` selector to `fill`. |
