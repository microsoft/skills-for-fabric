# Filter Pane & Filter Card Formatting

The filter pane is the collapsible side panel where users select and apply
filters at runtime. Its chrome lives in `page.json → objects.outspacePane`,
and each individual filter control is styled via `page.json → objects.filterCard`
with `Applied` / `Available` state selectors.

> **Scope:** This file covers the **appearance** of the filter pane and its
> filter cards. For filter **definitions** (which fields are filtered, `Where`
> conditions, filter scopes at report/page/visual level), see
> [`filters.md`](filters.md). For slicer visuals (a different mechanism,
> stored in `visual.json`), see [`slicers.md`](slicers.md).
>
> **Read first:** [`formatting-overview.md`](formatting-overview.md) for the
> cascade model and PBIR encoding rules.

## Contents

- [Filter Pane (`outspacePane`)](#filter-pane-outspacepane)
- [Filter Cards (`filterCard`)](#filter-cards-filtercard)
- [Theme-Level Styling](#theme-level-styling)

## Filter Pane (`outspacePane`)

The collapsible filter panel on the right side of a page:

```json
"outspacePane": [{
  "properties": {
    "backgroundColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } },
    "foregroundColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#252423'" } } } } },
    "titleSize": { "expr": { "Literal": { "Value": "12D" } } },
    "headerSize": { "expr": { "Literal": { "Value": "11D" } } },
    "searchTextSize": { "expr": { "Literal": { "Value": "9D" } } },
    "fontFamily": { "expr": { "Literal": { "Value": "'Segoe UI'" } } },
    "border": { "expr": { "Literal": { "Value": "true" } } },
    "borderColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#C8C8C8'" } } } } },
    "checkboxAndApplyColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#118DFF'" } } } } },
    "inputBoxColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } },
    "width": { "expr": { "Literal": { "Value": "250D" } } }
  }
}]
```

**All 12 properties:**

| Property | Type | Description |
|----------|------|-------------|
| `backgroundColor` | fill | Pane background |
| `transparency` | numeric | Background transparency (0–100) |
| `foregroundColor` | fill | Text and icon color |
| `titleSize` | numeric | Title text size (pt) |
| `headerSize` | numeric | Section header text size (pt) |
| `searchTextSize` | numeric | Search box text size (pt) |
| `fontFamily` | string | Font family for pane text |
| `border` | bool | Show pane border |
| `borderColor` | fill | Border color |
| `checkboxAndApplyColor` | fill | Checkbox accent and Apply button color |
| `inputBoxColor` | fill | Search/input box background |
| `width` | numeric | Pane width in pixels |

## Filter Cards (`filterCard`)

Individual filter controls within the pane. Use `id` selectors to distinguish
**Applied** (active) vs **Available** (inactive) states:

```json
"filterCard": [
  {
    "properties": {
      "backgroundColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } },
      "foregroundColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#252423'" } } } } },
      "textSize": { "expr": { "Literal": { "Value": "9D" } } },
      "border": { "expr": { "Literal": { "Value": "true" } } },
      "borderColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#C8C8C8'" } } } } }
    },
    "selector": { "id": "Available" }
  },
  {
    "properties": {
      "backgroundColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#E8F0FE'" } } } } },
      "borderColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#118DFF'" } } } } }
    },
    "selector": { "id": "Applied" }
  }
]
```

**⚠️ PascalCase required**: Selectors must be `"Applied"` / `"Available"`, not lowercase.

**8 properties per state:**

| Property | Type | Description |
|----------|------|-------------|
| `backgroundColor` | fill | Card background |
| `transparency` | numeric | Background transparency (0–100) |
| `foregroundColor` | fill | Text and icon color |
| `textSize` | numeric | Text size (pt) |
| `fontFamily` | string | Font family |
| `inputBoxColor` | fill | Input/dropdown background |
| `border` | bool | Show card border |
| `borderColor` | fill | Border color |

## Theme-Level Styling

The patterns above set filter pane appearance for a **single page** via
`page.json`. To apply filter pane styling to an entire report (e.g., as
part of a dark theme), set `outspacePane` and `filterCard` inside the
theme's `visualStyles["*"]["*"]`. The filter pane does **NOT** inherit
from theme structural colors, so theme switches will not update it
automatically — explicit theme entries are required.

See [`re-theming.md` § Dark Mode Authoring Checklist](re-theming.md#dark-mode-authoring-checklist)
for the complete dark-mode workflow, and [`re-theming.md` § Step 3: Filter pane + filter cards](re-theming.md#step-3-filter-pane--filter-cards)
for the theme-level filter pane recipe.
