# Conditional Formatting Patterns

## Contents

- [Field-Value Result Contracts and Support Guardrails](#field-value-result-contracts-and-support-guardrails)
  - [Result contracts](#result-contracts)
  - [Shared authoring checks](#shared-authoring-checks)
  - [Support decision and fallbacks](#support-decision-and-fallbacks)
  - [Validation and diagnostics](#validation-and-diagnostics)
- [VCO Conditional Formatting](#vco-conditional-formatting)
  - [Data-Bound Expression Rules](#data-bound-expression-rules)
- [Authoring Workflow](#authoring-workflow)
- [Formatting Options by Visual Type](#formatting-options-by-visual-type)
  - [Tables/matrices](#tablesmatrices)
  - [Charts](#charts)


Read this when applying data-driven visual formatting in PBIR. Conditional
formatting is supported on chart `dataPoint` properties, line and marker colors, selected data-label colors,table / matrix `values` cells, and selected card/KPI font-color properties. Support is
property-specific; do not assume that every color property accepts a rule.
The supported visual-container properties are listed under
[VCO Conditional Formatting](#vco-conditional-formatting). Other container
objects such as axes and legends are not covered by these patterns.

Page canvas and wallpaper colors are also not conditional-formatting targets.
Use static colors only; see
`page-formatting.md` § Dynamic Color Limitation (see `page-formatting.md`, section `dynamic-color-limitation`).

Related references:
- `formatting.md` (see `formatting.md`) — value encoding, selectors, VCOs.
- `formatting-overview.md` (see `formatting-overview.md`) — cascade and encoding.
- `expressions.md` (see `expressions.md`) — `Measure`, `Column`, `Aggregation`,
  `NativeMeasure`, and `ScopedEval` expression trees.
- `table.md` (see `table.md`) — table/matrix authoring and style presets.

> Examples use illustrative `<table>.<measure>` identifiers — substitute your own.

## Field-Value Result Contracts and Support Guardrails

A field-value binding is valid only when its driver resolves to one scalar value
that the target property accepts. A valid PBIR expression shape does not prove
that the runtime value is valid or that the target supports field-value
formatting.

Use this section as a contract and routing index. Keep detailed PBIR mechanics
in the linked result-type and visual-specific sections below.

### Result contracts

| Result | Required runtime value | Supported built-in routes | Invalid or unsupported behavior |
|--------|------------------------|---------------------------|---------------------------------|
| **Color (continued in `conditional-formatting-part-07.md`)** | Nonblank text containing `#RGB`, `#RRGGBB`, a standard CSS color name, `rgb()` / `rgba()`, `hsl()` / `hsla()`, or a verified report-theme color name. Solid field-value colors may also use `#RRGGBBAA`; see the hex-form restrictions (continued in `conditional-formatting-part-03.md`). Prefer a text-typed measure with one color format. | [Table/matrix cells](#tablesmatrices); supported chart targets (continued in `conditional-formatting-part-02.md`); [VCO colors](#vco-conditional-formatting); button/shape colors (continued in `conditional-formatting-part-03.md`); supported Azure Maps layer colors (continued in `conditional-formatting-part-02.md`). | A missing or non-color field can error the visual or fall back to default formatting. Page canvas/wallpaper, combo line/marker CF, scatter category-label CF, and other targets marked unsupported below must remain static. |
| **Web URL (continued in `conditional-formatting-part-06.md`)** | Nonblank text containing an absolute `http://` or `https://` URL. Use `dataCategory: WebUrl` when the field itself is displayed as a link; also prefer it for URL-driving fields and measures. | Table/matrix Web URL data category (continued in `conditional-formatting-part-06.md`); matrix `values.webURL`; button/shape `visualLink.webUrl` (continued in `conditional-formatting-part-03.md`). | Malformed or relative values do not become links. `tableEx` does not expose `values.webURL`; chart data points do not gain actions from a URL-valued field. |
| **Image (continued in `conditional-formatting-part-07.md`)** | Nonblank text containing an absolute, directly reachable image URL; HTTPS is preferred. The model field must have `dataCategory: ImageUrl`. | Table/matrix image cells (continued in `conditional-formatting-part-07.md`) and a data-bound standalone image visual (see `image.md`, section `3-select-from-data`). | A missing data category shows URL text or a blank visual; unreachable, non-image, authentication-gated, or CORS-blocked resources render blank/broken. |
| **Icon (continued in `conditional-formatting-part-06.md`)** | One exact icon name from the icon catalog (continued in `conditional-formatting-part-06.md`), stored as a string `Literal` in a `Conditional.Cases[]` result. | Table/matrix `values.icon` rules. | Icon names are not free-form field-value outputs. Invalid names can crash Desktop; button glyph names and Azure Maps marker shapes are separate static enums. |
| **Text** | One scalar text value. Prefer a text measure; a column must resolve to one value in context or be wrapped in an appropriate aggregation. | [VCO title/alt text](#vco-conditional-formatting), button/shape labels (continued in `conditional-formatting-part-03.md`), and dynamic textboxes (see `textbox.md`, section `dynamic-textbox-value`). | A missing field errors the visual; a multi-valued raw column can return blank or an ambiguous result. Do not assume arbitrary axis, legend, or label text properties accept data-bound expressions. |

### Shared authoring checks

- **Refuse incompatible or unknown result types before writing PBIR.** A color
  field-value driver must be verified as text-typed and return valid color
  strings; a Web URL driver must be text-typed and return absolute HTTP(S)
  URLs; an image driver must additionally have `dataCategory: ImageUrl`. Do not
  author a deliberately invalid binding to discover Desktop's fallback. If the
  driver's type, data category, or representative values cannot be verified,
  stop and request a valid field or the required semantic-model correction.
- Keep the displayed/formatting **target** separate from the **driver** that
  supplies the result. Follow Driving field vs. target
  field (continued in `conditional-formatting-part-03.md`).
- Ensure the driver resolves to one scalar value. Reference measures directly;
  aggregate raw columns as documented in Aggregation: columns vs.
  measures (continued in `conditional-formatting-part-03.md`).
- Treat `Min`/`Max` only as scalarization. Use it when all contributing rows
  should return the same result or lexical minimum/maximum is intentional;
  otherwise use a measure that defines the business rule.
- Use the target visual's documented expression and selector route; see the
  selector summary (continued in `conditional-formatting-part-03.md`). Do not infer one
  visual's route from another.

### Support decision and fallbacks

1. Confirm the visual type, object, property, and accepted expression type with
   `powerbi-report-author catalog describe` and
   `powerbi-report-author formatting describe-object`.
2. Check the target-specific matrices in this file. A property typed as `fill`
   proves its value shape, not that the target property supports field-value,
   Rules, or Gradient formatting.
3. Verify the model field/measure exists, has the required data type and data
   category, and returns values matching the table above. This is a hard
   pre-authoring gate: reject numeric/boolean color outputs, non-URL action
   values, and image fields without `ImageUrl` metadata rather than persisting
   them for Desktop to diagnose. Delegate model changes or data inspection to
   the semantic-model authoring capability.
4. If the target is supported, author the documented selector and expression.
   If unsupported, do not move the expression to a similarly named property or
   rely on schema permissiveness. Explain the limitation and offer a static
   value or a supported built-in visual/target.
5. Run PBIR validation, load the latest report, and review a screenshot with
   representative nonblank, blank, and invalid values where those cases can
   occur.

Known cross-cutting unsupported cases include:

- Page canvas and wallpaper field-value colors; use static colors and see
  `page-formatting.md` (see `page-formatting.md`, section `dynamic-color-limitation`).
- Table/matrix column width is static and not conditionally formattable; see
  Column width (continued in `conditional-formatting-part-07.md`).
- Button icon glyph/size/placement, shape geometry, and shadow/glow numeric
  parameters; only their documented color or text properties are data-driven.
- Chart Web URL actions and field-driven icon names.
- Any visual/property combination marked `No*` or unsupported in a capability
  matrix in this file.

Marketplace, organizational, and private custom visuals define their own
capabilities. The built-in catalog and matrices in this guide cannot guarantee
their field-value support. Inspect the visual package's
`capabilities.dataRoles` and formatting capabilities or authoritative vendor
documentation, then verify in Desktop. Successful registration and recognition
do not prove that a custom visual supports conditional formatting. See
`custom-visuals.md` (see `custom-visuals.md`).

### Validation and diagnostics

Offline validation cannot evaluate the values returned by model measures or
columns, so runtime rendering remains required.

| Symptom or diagnostic | Meaning | Action |
|-----------------------|---------|--------|
| Grey **See details** overlay or field warning | Driver is missing, errors, or returns the wrong result type | Repair or replace the model field through the semantic-model capability; do not silently substitute an unrelated field |
| Validates but keeps default/static formatting | Unsupported target, wrong selector, or driver does not resolve at that scope | Recheck the target matrix, selector, and driver context; use a documented fallback if unsupported |
| `PBIR_PAGE_COLOR_DATA_BOUND_UNSUPPORTED` | Page canvas/wallpaper cannot evaluate a data-bound color | Replace it with a static `Literal` |
| URL remains plain text or image is blank/broken | Value/data category is invalid, or the resource is unreachable | Validate representative values and the required `WebUrl` / `ImageUrl` model metadata |
| Desktop fails while loading an icon rule | Icon result is not in the documented catalog | Replace it with an exact catalog name before reloading |

## VCO Conditional Formatting

Visual-container conditional formatting is stored in
`visual.json → visual.visualContainerObjects`. VCOs are visual-wide settings
and do not use selectors.

| Property | Valid expressions |
|----------|-------------------|
| Title text (`title.text`); alt text (`general.altText`) | `Literal`; `Conditional` (Type 2 (continued in `conditional-formatting-part-05.md`)); `Measure`; `Column`; `NativeMeasure`; `Aggregation`; `ScopedEval`; `SelectRef` (continued in `conditional-formatting-part-04.md`) |
| Title font color (`title.fontColor`); title background (`title.background`); visual background color (`background.color`); border color (`border.color`) | `Literal`; `ThemeDataColor`; `FillRule` (Type 1 (continued in `conditional-formatting-part-04.md`)); `Conditional` (Type 2 (continued in `conditional-formatting-part-05.md`)); color-valued `Measure`; `Column`; `NativeMeasure`; `Aggregation`; `ScopedEval`; `SelectRef` (continued in `conditional-formatting-part-04.md`) |

> `general.altText` describes the visual and its meaningful insights for
> accessibility.

### Data-Bound Expression Rules

| Property | Data-bound expression | Rules |
|----------|-----------------------|-------|
| `title.text`; `general.altText` | `Measure` | Preferred option. Must reference the exact owning table and measure and return scalar text. |
| `title.text`; `general.altText` | `Column` | Must resolve to one value in the current filter context. Prefer a measure using `SELECTEDVALUE`. |
| `title.text`; `general.altText` | `Aggregation` | Must aggregate the referenced column into one scalar text-compatible value. |
| `title.text`; `general.altText` | `NativeMeasure` | Must be available in the visual query and return text. |
| `title.text`; `general.altText` | `ScopedEval` | Referenced roles and fields must exist in the visual query; the result must be text. |
| `title.text`; `general.altText` | `SelectRef` | Referenced query selection must exist and return text. |
| `title.text`; `general.altText` | `Conditional` | Every case value and default must return text. |
| `title.fontColor` | `Measure`, `Column`, `Aggregation`, `NativeMeasure`, `ScopedEval`, `SelectRef` | Must resolve to one valid CSS color or theme token. Null is not allowed. |
| `title.fontColor` | `Conditional` | Every case value and default must return a valid color. |
| `title.fontColor` | `FillRule` | Input must be an available numeric field or measure; gradient stops must provide valid colors. |
| `title.background` | `Measure`, `Column`, `Aggregation`, `NativeMeasure`, `ScopedEval`, `SelectRef` | Must resolve to a valid color. Null is allowed. |
| `title.background` | `Conditional` | Every result must be a valid color or null. |
| `title.background` | `FillRule` | Input must be numeric; gradient stops must provide valid colors. |
| `background.color` | `Measure`, `Column`, `Aggregation`, `NativeMeasure`, `ScopedEval`, `SelectRef` | Must resolve to a valid color. Null is not allowed. |
| `background.color` | `Conditional` | Every result must be a valid color. |
| `background.color` | `FillRule` | Input must be numeric; gradient stops must provide valid colors. |
| `border.color` | `Measure`, `Column`, `Aggregation`, `NativeMeasure`, `ScopedEval`, `SelectRef` | Must resolve to a valid color. Null is not allowed. |
| `border.color` | `Conditional` | Every result must be a valid color. |
| `border.color` | `FillRule` | Input must be numeric; gradient stops must provide valid colors. |

`Literal` and `ThemeDataColor` are constant/static expressions rather than
conditional-formatting types. `FillRule` corresponds to Type 1, and
`Conditional.Cases[]` corresponds to Type 2.

## Authoring Workflow

1. **Identify the visual type.** Start with the relevant section under
   [Formatting Options by Visual Type](#formatting-options-by-visual-type).
2. **Validate the result and target.** Apply the
   [field-value result contracts and support guardrails](#field-value-result-contracts-and-support-guardrails),
   then follow the linked type for the desired result, such as a gradient,
   rules, icons, data bars, links, or field-driven color.
3. **Build the formatting expression.** Reference the field or measure that
   drives the formatting and follow the
   driver-expression decision path (continued in `conditional-formatting-part-03.md`):
   an existing visual query selection uses `SelectRef`; otherwise a DAX measure
   uses `Measure`, and a raw column uses `Aggregation(Column, Function)`. Keep
   the driving field distinct from the target field (continued in `conditional-formatting-part-03.md`)
   and use only valid hex color results (continued in `conditional-formatting-part-03.md`).
4. **Apply the correct object and selector.** Use the
   selector summary (continued in `conditional-formatting-part-03.md`); requirements differ
   across tables, matrices, charts, cards, and KPIs.
5. **Validate and render.** Run `powerbi-report-author validate <path>`, reload
   the report in Desktop, and confirm that the formatting appears.

## Formatting Options by Visual Type

### Tables/matrices

- Cell gradients: Type 1: Color Gradient (continued in `conditional-formatting-part-04.md`)
- Rule-based cell colors: Type 2: Rules-Based Formatting (continued in `conditional-formatting-part-05.md`)
- Cell icons: Type 3: Icon Sets (continued in `conditional-formatting-part-06.md`)
- In-cell bars: Type 4: Data Bars (continued in `conditional-formatting-part-06.md`)
- Clickable links: Type 5: Web URL (continued in `conditional-formatting-part-06.md`)
- Colors supplied by a field: Type 6: Field-Driven Color (continued in `conditional-formatting-part-07.md`)
- Images in cells: Type 7: Image Field Values (continued in `conditional-formatting-part-07.md`)
- Totals/subtotals targeting: Totals, subtotals, and the matrix `total` slot (continued in `conditional-formatting-part-07.md`)
- Column width (not conditionally formattable; static width lives in
  table.md § Column width (static) (see `table.md`, section `column-width-static`)):
  Column width — not conditionally formattable (continued in `conditional-formatting-part-07.md`)

> **`tableEx` (table) and `pivotTable` (matrix) share the same CF syntax for
> Types 1–6.** Those types use the same objects and selectors on both visuals;
> the examples below use a table for brevity and apply to a matrix unchanged. On
> a matrix the `metadata` queryRef still targets the **Values** measure whose
> cells you format (Types 1/2/3/5/6 use `dataViewWildcard` + `metadata`; Type 4
> data bars are `metadata`-only). **Type 7 (image field values) differs** between
> the two — a table binds an ImageUrl **column** directly, while a matrix needs a
> **measure** or an `Aggregation`-wrapped column; see
> Type 7 (continued in `conditional-formatting-part-07.md`) for the placement rules.
>
> **Cell CF targets Values-role fields.** Both visuals bind the formatted field
> through the **Values** role. In a `pivotTable`, cell CF (Background color, Font
> color, Data bars, Icons, Web URL) is available **only for Values-role fields** —
> fields in the **Rows** or **Columns** role cannot be conditionally formatted this
> way, so the `metadata` selector must reference a **Values-role** field's queryRef,
> never a Rows/Columns field. A `tableEx` has a single **Values** role that holds
> every displayed column, so any column can be formatted. (Row/column *header*
> styling is a separate format-pane setting, not cell CF.)

### Charts

- Data-point, line, marker, and label gradients:
  Type 1: Color Gradient (continued in `conditional-formatting-part-04.md`)
- Rule-based chart colors:
  Type 2: Rules-Based Formatting (continued in `conditional-formatting-part-05.md`)
- Colors supplied by a field:
  Type 6: Field-Driven Color (continued in `conditional-formatting-part-07.md`)
- Legend and series-label color consistency:
  Chart color inheritance (continued in `conditional-formatting-part-07.md`)
