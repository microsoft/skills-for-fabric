# `powerbi-report-author` CLI Reference

Use this file when the root command table is not enough. The CLI is the source
of truth for visual roles, formatting objects, property names, enum values,
selectors, expression/value encodings, and PBIR validation.

## Command catalog

| Command | Purpose | When to use |
|---|---|---|
| `--help` / `<command> --help` | Show syntax and available flags | Before using an unfamiliar command or flag |
| `catalog list` | List all built-in visual types and deprecated entries | Choosing a visual type |
| `catalog describe <type>` | Roles, formatting keys, cardinality | Before creating/editing a visual |
| `formatting list-objects <type>` | Valid `objects.*` keys + VCO keys; flags objects needing id selectors | Before applying formatting |
| `formatting describe-object <type> <object>` | Property names, types, enum values, descriptions; `_selectorHint` when id selector required | Finding exact property names and allowed values |
| `formatting describe-property <type> <object> <prop>` | Focused single-property lookup | When you already know the object and want one property |
| `formatting search <type> <regex>` | Regex search across formatting objects + VCOs | When you do not know which object a property belongs to |
| `formatting list-vcos` | Enumerate shared visualContainerObjects | Auditing chrome/container formatting surface |
| `formatting effective-properties <type>` | Flattened visual objects + shared VCOs | One-shot snapshot of every formatting surface for a visual |
| `expr encode --kind <t> <v> [percent]` | Generate correct PBIR value encoding | Writing formatting values |
| `expr decode '<json>'` | Decode a PBIR expression to plain value | Inspecting existing formatted values |
| `theme encode --kind <t> <v>` | Generate the plain-JSON value used inside a theme file | Editing theme JSON |
| `theme shade-color <hex> <percent>` | Apply ThemeDataColor shadeColor adjustment | Previewing tinted/shaded theme colors |
| `validate <path>` | Full validation of a `.pbip` or `.Report` directory | After every batch of PBIR edits |
| `preview-visuals <path> [--with-derived]` | Enumerate every visual with stable summary fields + path to JSON | Auditing visuals across a report |
| `preview-pages <path> [--with-derived]` | Page metadata summary | Quick page overview |
| `preview-filters <path>` | Enumerate report/page/visual filters | Filter audit |
| `preview-themes <path> [--with-derived]` | Registered custom theme summary | Theme audit |
| `doctor` | Environment self-check | First-run setup or troubleshooting |

## Validation result handling

Run `powerbi-report-author validate <path-to-.Report-dir>` after every logical
batch of PBIR edits.

- Fix every error before Desktop reload.
- Review warnings before proceeding. Unknown visual types or theme visual keys
  usually mean a typo unless the report intentionally uses a custom `.pbiviz`.
- Diagnostics include file paths and JSON paths. Use them to jump directly to
  the broken node.
- For large diagnostics, use `--pretty` for readable output or `--out <file>` to
  write the full result to a file.
