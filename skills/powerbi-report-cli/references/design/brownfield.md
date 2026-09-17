# Brownfield Redesign — Entry Workflow

Read this when the user wants to redesign, restyle, theme-swap (light↔dark),
modernize, or critique an existing Power BI report. The greenfield workflow
in `SKILL.md` still applies — every Step (0 → 7) runs — but each Step runs
in **delta-against-current** mode rather than from a blank canvas.

## When this file applies

User intents that flag brownfield mode:

- "redesign this report" / "restyle the visuals" / "make it look professional"
- "switch to dark mode" / "convert this to light theme" / "theme swap"
- "make it consistent with brand X" / "apply our brand"
- "modernize this report" / "bring this up to date"
- "the visuals don't match the rest of the dashboard"
- "fix the design of [specific page]"

For these intents, default to brownfield mode. If unclear (e.g., the user
shows a screenshot but isn't explicit about whether to redesign or build
new), **ask** before proceeding.

## Entry workflow (6 steps)

1. **Load the report** — confirm the existing PBIP path with the user.
2. **Screenshot all pages** via `powerbi-desktop screenshot-all --pid <pid>`
   — these become the "before" evidence.
3. **Diagnose** the existing report against:
   - `references/design/anti-patterns.md`
   - authoring anti-patterns
   - the Pre-Flight Checklist in `references/design/pre-flight-checklist.md`
   - the new design identity (compute the gap)
4. **Emit the re-design brief** (`mode: brownfield`) — list specific pages,
   visuals, themes, and chrome that change. Include rationale for each
   delta. Bookmarks and `visualLink` refs are preserved unless the redesign
   explicitly retires them; flag any that target ids that change.
5. **Hand off to the `authoring` mode** for the surgical edits. Authoring
   runs `powerbi-report-author validate` after each batch to catch theme
   mismatches (`PBIR_THEME_*`), formatting drift (`PBIR_FORMATTING_*`), and
   layout regressions before reload — common brownfield-edit defects.
6. **Final Audit** — screenshot AFTER. Verify the redesign delivered on the
   target tone without breaking what worked.

## How each Step changes in brownfield mode

| Step | Greenfield | Brownfield delta |
|---|---|---|
| 0 — Data | Inspect the model from scratch | Usually unchanged — the model is the same |
| 1 — Identity | Commit `tone` + `signature` | Capture both `current_tone` AND `target_tone`; the delta drives the redesign plan |
| 2 — Archetype Router | Route per page | AUDIT existing pages against the archetype rules and the new identity — identify pages that don't fit and either re-route or accept and document |
| 3–4 — Chart / Visual | Select and configure visuals | Preserve useful existing visuals; replace only when the visual no longer serves the target question or identity |
| 5 — Theme | Adapt the existing/custom theme to identity | Compute a theme **delta** — which palette entries change, which `textClasses` move, which `visualStyles` defaults are tightened. Document the swap; do not rebuild from scratch |
| 6 — Brief | Emit greenfield brief | Emit a **re-design brief** — same template, with the brownfield fields filled in (`current_tone`, `current_signature`, `mode: brownfield`) |
| 7 — Review | Pre-Flight Checklist | Same checklist plus brownfield-specific items: every removed/replaced visual reasoned about; theme swap preserves CF logic; dark↔light swap re-validates contrast pairs; bookmarks and `visualLink` refs survive any visual id changes |

## Brownfield-specific Pre-Flight items

In addition to the standard `references/design/pre-flight-checklist.md`, verify:

- [ ] **Removed/replaced visuals** — every visual that disappears or changes
      type is reasoned about in the brief (not silently dropped).
- [ ] **Conditional-formatting logic preserved** — theme swap (e.g., palette
      change or dark↔light) does not invalidate CF rules that reference
      palette slots; verify thresholds and color expressions still resolve.
- [ ] **Contrast re-validated** — for any light↔dark swap, every text /
      background pair that was WCAG-compliant before is still compliant
      after. See `references/design/accessibility.md`.
- [ ] **Bookmarks survive id changes** — if the redesign renames or
      replaces visuals, every bookmark that references the old id is
      updated or explicitly retired. `powerbi-report-author validate`
      catches schema-level structural issues; manually verify bookmark
      `visualLink` targets against the new visual ids.
- [ ] **Page background re-checked** — dark themes need a darker page
      background than the default `#F3F2F1`; confirm the page background
      contrasts with the new visual containers.

## Theme-swap shortcut (light↔dark)

When the user asks for a pure theme swap with no other redesign:

1. Read the current theme JSON.
2. Produce a sibling theme with inverted neutrals (page background, card
   surfaces, text colors, gridlines) and an adjusted palette (often the
   same hues with adjusted saturation/lightness for legibility on the new
   background).
3. Identify theme changes that also require per-visual updates (for example
   gradient stops, card accent bars, state-aware buttons) and record them in
   the redesign brief; the `authoring` mode handles the PBIR mechanics.
4. For full mechanics see the dark mode authoring checklist in
   the `authoring` mode.
