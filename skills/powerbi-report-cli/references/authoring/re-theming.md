# Re-theming & Dark Mode — Workflow Reference

> Referenced from SKILL.md and theming.md. Read this when switching an existing
> report to a new theme or applying dark mode to a report with existing visuals.
> For theme JSON structure and creation, read theming.md (see `theming.md`) first.

When a report already has per-visual formatting overrides (shapes, buttons, page
backgrounds, cards), changing the theme JSON alone does not propagate colors to
those overrides — they sit above the theme in the cascade. A re-theming
operation updates both the theme file AND sweeps inline overrides in a single
atomic step.

> **When is the full workflow needed?** Reports with explicit per-visual `objects`
> or `visualContainerObjects` color properties need the sweep. A freshly-created
> report with no inline color overrides (all colors inherited from theme) can be
> re-themed by editing the theme file alone — the cascade will propagate changes.
> When unsure, grep `definition/` for hex color values from the old theme — if
> any appear outside the theme file, the sweep is needed.

## Table of Contents

- Re-theming an Existing Report (continued in `re-theming-part-02.md`)
  - Why Theme Changes Don't Fully Propagate (continued in `re-theming-part-02.md`)
  - Re-theming Workflow (continued in `re-theming-part-02.md`) — Steps 0–4
  - Preventive Authoring: Theme-Adaptive Visuals (continued in `re-theming-part-02.md`)
- Dark Mode Authoring Checklist (continued in `re-theming-part-03.md`)
