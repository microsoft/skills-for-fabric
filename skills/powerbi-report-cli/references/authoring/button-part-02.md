# Button Visual Authoring Guide - Part 2

## Contents

- [Action Types](#action-types)
  - [Data Function (translytical task flow)](#data-function-translytical-task-flow)
- [Formatting Objects](#formatting-objects)
- [Dual-Entry Pattern (Required)](#dual-entry-pattern-required)
- [State Selectors](#state-selectors)
- [Conditional Formatting (Data-Driven Color)](#conditional-formatting-data-driven-color)
- [Shape Options](#shape-options)
- [Icon Options](#icon-options)


Continuation of `button.md`. Open this file directly from the skill reference index.

## Action Types

Actions are set via `visualContainerObjects.visualLink`. Discover this VCO and
its properties with
`powerbi-report-author formatting search actionButton "type|link"`. The `type`
property determines the action; a companion property configures the destination.
Commonly used action types:

| Action Type | `type` Value | Additional Properties | Use Case |
|---|---|---|---|
| Back | `'Back'` | — | Return to previous page (drillthrough) |
| Page Navigation | `'PageNavigation'` | `navigationSection`: `'<pageId>'` | Navigate to a specific page |
| Bookmark | `'Bookmark'` | `bookmark`: `'<bookmarkName>'` | Apply a bookmark state |
| Drillthrough | `'Drillthrough'` | `drillthroughSection`: `'<pageId>'` | Navigate with filter context |
| Web URL | `'WebUrl'` | `webUrl`: `'<url>'` | Open external link |
| Q&A | `'Qna'` | — | Open Q&A explorer |
| Apply All Slicers | `'ApplyAllSlicers'` | — | Apply pending slicer selections |
| Clear All Slicers | `'ClearAllSlicers'` | — | Reset all slicers on page |
| Data Function | `'DataFunction'` | `dataFunction`: structured item reference (see [Data Function](#data-function-translytical-task-flow)) | Invoke a Fabric User Data Function (translytical task flow) |

**Page Navigation example:**
```json
"visualLink": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "type": { "expr": { "Literal": { "Value": "'PageNavigation'" } } },
    "navigationSection": { "expr": { "Literal": { "Value": "'<target_page_id>'" } } },
    "tooltip": { "expr": { "Literal": { "Value": "'Go to Details'" } } }
  }
}]
```

**Web URL example:**
```json
"visualLink": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "type": { "expr": { "Literal": { "Value": "'WebUrl'" } } },
    "webUrl": { "expr": { "Literal": { "Value": "'https://example.com'" } } }
  }
}]
```

> **Data-driven Web URL.** `webUrl` also accepts a **measure** returning a URL
> string:
> `"webUrl": { "expr": { "Measure": { "Expression": { "SourceRef": { "Entity": "Metrics" } }, "Property": "Btn URL" } } }`.
> See
> conditional-formatting.md § Buttons and shapes (see `conditional-formatting.md`, section `buttons-and-shapes`).

> **Note:** The companion property
> (`navigationSection`, `drillthroughSection`, `bookmark`) is the raw page id or
> bookmark name as a string literal. The validator cross-checks bookmark action
> targets against `definition/bookmarks/`; a missing destination is reported as
> `PBIR_BOOKMARK_ACTION_REF_MISSING` before Desktop reload. See
> bookmark.md (see `bookmark.md`).

### Data Function (translytical task flow)

A `DataFunction` button invokes a published Fabric **User Data Function** (UDF) —
a *translytical task flow* that runs server-side logic (e.g. Python write-back).
Unlike the other action types, its companion `dataFunction` property is **not** a
string literal: it is a **structured item reference** to the UDF plus a cached
copy of the function signature and the button's parameter bindings.

Structure:

```json
"visualLink": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "type": { "expr": { "Literal": { "Value": "'DataFunction'" } } },
    "tooltip": { "expr": { "Literal": { "Value": "'Run data function'" } } },
    "dataFunction": {
      "kind": "ItemLocation",
      "byReference": {
        "itemId":      { "expr": { "Literal": { "Value": "'<userDataFunctions_item_id>'" } } },
        "workspaceId": { "expr": { "Literal": { "Value": "'<workspace_id>'" } } }
      },
      "metadata": {
        "dataFunction": {
          "name": "<function_name>",
          "autoRefresh": true,
          "parameters": [
            {
              "name": "<param_name>",
              "dataType": "string",
              "isOptional": false,
              "defaultValue": null,
              "type": "SlicerParameter",
              "slicer": "<slicer_visual_name>",
              "autoClear": false
            }
          ]
        }
      }
    }
  }
}]
```

Field reference:

| Field | Meaning | How to obtain |
|---|---|---|
| `byReference.workspaceId` | GUID of the workspace holding the UDF (the **Workspace** dropdown in Desktop) | Resolve workspace name → id (see SKILL.md **CRITICAL NOTES** (see `../authoring.md`, section `critical-notes`): list workspaces + JMESPath filter) |
| `byReference.itemId` | GUID of the **UserDataFunctions** item — the **Function set** dropdown | List items of type `UserDataFunctions` in the workspace → id (SKILL.md **CRITICAL NOTES** (see `../authoring.md`, section `critical-notes`)) |
| `metadata.dataFunction.name` | The function within the item — the **Data function** dropdown | From the UDF definition, or ask the user |
| `metadata.dataFunction.parameters[]` | Cached copy of the function's parameter signature, each with its binding to a report element | From the UDF signature; bind each parameter to an input on the page |

The GUIDs use the standard `expr → Literal → Value` envelope (single-quoted
string), same as every other literal in PBIR — so once the ids are resolved, the
reference is authored exactly like any other property.

**Parameter bindings** — each `parameters[]` entry copies the UDF parameter
(`name`, `dataType`, `isOptional`, `defaultValue`) and adds how the button feeds
it a value. **General rule:** every **required** parameter (`isOptional: false`,
no `defaultValue`) must be bound to some input source on the page; **optional**
parameters (`isOptional: true`, with a `defaultValue`) can be left unmapped and
the function's default is used. If every parameter is optional, the button needs
no input control at all.

Per the [translytical task flow docs](https://learn.microsoft.com/power-bi/create-reports/translytical-task-flow-button),
a parameter's input source can be **a slicer** (button, list, or input/text
slicer), **a data field** (a column in the Data pane), or **a measure**
(e.g. `SELECTEDVALUE(Customer[CustomerID])` to pass a single value). The `type`
field on the `parameters[]` entry selects which source is used; author it to
match the input you intend to bind.

*Example — binding a parameter to a slicer* (`type: "SlicerParameter"`):

```json
{
  "name": "<param_name>",
  "dataType": "string",
  "isOptional": false,
  "defaultValue": null,
  "type": "SlicerParameter",
  "slicer": "<slicer_visual_name>",
  "autoClear": false
}
```

`slicer` is the target slicer visual's `name` (its `visuals/<name>` folder);
`autoClear` controls whether the slicer resets after the function runs; the bound
slicer must exist on the page for the button to enable. For a **field** or
**measure** source the entry uses a different `type` and binding property —
inspect a button authored in Desktop to capture the exact `parameters[]` shape
before hand-writing it.

**Authoring flow:**
1. Inspect the UDF signature. For each **required** parameter, choose an input
   source (slicer / field / measure); **optional** parameters may be skipped.
2. Ensure each chosen input exists on the page (e.g. for a slicer source, note
   its visual `name`).
3. Resolve `workspaceId` and the `UserDataFunctions` `itemId`
   (SKILL.md **CRITICAL NOTES** (see `../authoring.md`, section `critical-notes`): list items + JMESPath filter).
4. Author the button `visual.json` with `type: 'DataFunction'` and the
   `dataFunction` block above — one `parameters[]` entry per **bound** UDF
   parameter, each with the `type` and binding property for its source.
5. **Publish** the report — the Fabric service executes the function when the
   button is clicked.

> **Runtime note:** The referenced UDF must **return a string**. If the item
> reference or a **required** parameter's bound input (slicer/field/measure) is
> missing or invalid, the button still validates but stays **disabled** at
> runtime.

---

## Formatting Objects

List the objects and which require selectors with
`powerbi-report-author formatting list-objects actionButton`, and read each
object's properties, types, and valid selector IDs (`_selectorHint`) with
`powerbi-report-author formatting describe-object actionButton <object>`.

Two things the CLI does not surface:
- `shape` needs a `default`-selector entry to render — see [Shape Options](#shape-options).
- `rotation` takes no selector — author its properties in a single no-selector entry.

---

## Dual-Entry Pattern (Required)

Button formatting objects use a **dual-entry** array pattern:

1. **Entry 1 (no selector):** Toggle properties (`show`) — applies to ALL states
2. **Entry 2 (with state selector):** Styling properties — applies to that specific state

```json
"fill": [
  { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } },
  { "properties": { "fillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#0078D4'" } } } } } }, "selector": { "id": "default" } }
]
```

> ⚠️ **Putting all properties in one entry (with or without selector) causes
> formatting to silently fail.** The button renders with defaults — no fill,
> no text color, no icon styling. Always separate `show` from styling properties.

**Exceptions:**
- `outline` with `show: false` — can be a single unselectored entry (nothing to style)
- `rotation` — never takes a selector; author all rotation properties in one
  no-selector entry (unlike `shape`, it does **not** need a `default`-selector entry).
- `shape` — uses a **two-entry** pattern, but different from the `show`/style split above (there is no `show` toggle). See [Shape Options](#shape-options).

> **`shadow` and `glow` follow the standard dual-entry rule — do not treat them like
> `rotation`.** They are effect objects *with* a `show` toggle *and* a state selector, so
> `show` goes in Entry 1 (no selector) and the styling (`color`, `shadowBlur`,
> `shadowPositionPreset`, `shadowDistance`, `angle`) in Entry 2 (`selector: { "id":
> "default" }`). Putting `show` inside the `default`-selector entry (or cramming everything
> into one selectored entry) leaves the object **toggled off in the format pane and not
> rendered** — the effect silently never appears. This is the same failure as the `fill`
> example above.

---

## State Selectors

Stateful objects accept a `{ "id": "<state>" }` selector on each styling entry.
Read the valid state IDs for an object from its `_selectorHint`
(`describe-object`). The enum names don't spell out what each state means:

| Selector ID | State | When active |
|---|---|---|
| `"default"` | Normal/resting | Not hovered or pressed |
| `"hover"` | Mouse over | Cursor is on the button |
| `"selected"` | Pressed/active | Button is clicked/held |
| `"disabled"` | Inactive | Button action unavailable |

> **`shape` is state-selectable too — the CLI does not show it.** In Desktop the Shape card
> has an "Apply settings to → State" dropdown, and per-state `shape` entries render correctly
> (e.g. a `default` hexagon that becomes an `oval` on hover), **verified by Desktop render**.
> But `describe-object actionButton shape` currently returns **no `_selectorHint`**, so the
> CLI understates it — treat `shape` (including `tileShape`) as accepting the same
> `default`/`hover`/`selected`/`disabled` selectors as `fill`/`text`/`outline`.
>
> The `disabled` state only appears when the button's action is genuinely unavailable — the
> only reliable trigger is a `Drillthrough` button with no data point selected. A button with
> an always-available action can author `disabled` styling but will never display it.

Add one styling entry per state:

```json
"fill": [
  { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } },
  { "properties": { "fillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#0078D4'" } } } } } }, "selector": { "id": "default" } },
  { "properties": { "fillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#005A9E'" } } } } } }, "selector": { "id": "hover" } }
]
```

Only the `default` state renders on the Edit-view canvas and in `screenshot-all`;
`hover`/`selected` show only in Reading view or via the Format pane's state
dropdown. A button whose action is unavailable renders in its `disabled` state
automatically.

---

## Conditional Formatting (Data-Driven Color)

Button color properties, the text label (`text.text`), and the Web URL action
target support data-driven formatting. See
conditional-formatting.md § Buttons and shapes (see `conditional-formatting.md`, section `buttons-and-shapes`)
for the supported properties, styles (field value / rules / gradient), selector
requirements, limits, and examples.

---

## Shape Options

Set via `objects.shape` using a **two-entry** array. This is **required for the
shape to actually render** — a single selector-less entry passes validation but
Power BI Desktop **silently renders a flat rectangle** regardless of `tileShape`.

- **Entry 1 (no selector):** `tileShape` + any shape-specific geometry params
  (`roundEdge`, `parallelogramSlant`, `speechBubbleHeight`, etc.).
- **Entry 2 (`selector: { "id": "default" }`):** `tileShape` **only** — this is
  the entry Desktop reads to select the rendered shape.

```json
"shape": [
  { "properties": { "tileShape": { "expr": { "Literal": { "Value": "'parallelogram'" } } }, "parallelogramSlant": { "expr": { "Literal": { "Value": "20L" } } } } },
  { "properties": { "tileShape": { "expr": { "Literal": { "Value": "'parallelogram'" } } } }, "selector": { "id": "default" } }
]
```

Keep geometry params in Entry 1 and only `tileShape` in the `default` entry —
this matches Power BI's own serialization so the file round-trips cleanly. Get
the `tileShape` enum values and each shape's geometry params (all integer
literals, e.g. `20L`) from
`powerbi-report-author formatting describe-object actionButton shape`.

> **Non-rectangular shapes seat the label in a non-rectangular region** — centered white
> text can overrun the colored area and vanish on the canvas. There is no sizing formula
> for this; handle it via shape choice, `text.horizontalAlignment`, short labels, and a
> render check — see Button Sizing Step 2
> and Step 5.

> ⚠️ **Never author `tileShape: 'line'`.** The enum includes `'line'`, but it is a
> phantom — not offered in Desktop's Shape dropdown, renders as a near-invisible
> thin rule, and **crashes the Desktop format pane** when the button is selected.
> The CLI cannot flag this; exclude it yourself.

---

## Icon Options

Set via `objects.icon` with a `{ "id": "default" }` selector. Get the `shapeType`
enum (built-in glyphs) and `placement` enum from
`powerbi-report-author formatting describe-object actionButton icon`.

Behavioral facts the CLI does not surface:
- `shapeType: 'blank'` renders no icon (label only).
- `iconSize` is a numeric point size (`Double`, e.g. `28D`), not an integer literal.
- `shapeType: 'custom'` sets the icon `image` to a **registered resource** — add the
  raster under `StaticResources/RegisteredResources/`, list it in the report's
  `resourcePackages`, and point `image.url` at that resource path. Prefer a built-in
  `shapeType` glyph when one fits; only use `custom` when you have a real registered
  raster. Avoid inline `data:` URIs — they may author and validate (schema checks are
  skipped when the schema is unreachable) but can fail to render or destabilize Desktop.

**Dual-entry for icon:** put `icon.show` in the first no-selector entry and the
styling (`shapeType`, `placement`, `lineColor`, `iconSize`, `image`) in a
`{ "id": "default" }` entry — same split as `fill`/`text`:

```json
"icon": [
  { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } },
  { "properties": { "shapeType": { "expr": { "Literal": { "Value": "'information'" } } }, "placement": { "expr": { "Literal": { "Value": "'left'" } } } }, "selector": { "id": "default" } }
]
```

---
