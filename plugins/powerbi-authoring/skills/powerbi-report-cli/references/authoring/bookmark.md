# Bookmark Authoring

Use report bookmarks to save deterministic report state for storytelling,
show/hide panels, chart swaps, reset views, and button-driven navigation.
This guide covers **report bookmarks stored in PBIR**. Personal bookmarks are
user/service state and are out of scope.

## Contents

- [Required workflow](#required-workflow)
- [File layout](#file-layout)
- [Bookmark index and groups](#bookmark-index-and-groups)
- [Bookmark state](#bookmark-state)
- [Visibility toggles and chart swaps](#visibility-toggles-and-chart-swaps)
- [Current page](#current-page)
- [Filter and slicer state](#filter-and-slicer-state)
- [Bookmark buttons](#bookmark-buttons)
- [Bookmark navigator](#bookmark-navigator)
- [Validation diagnostics](#validation-diagnostics)
- [Desktop verification checklist](#desktop-verification-checklist)
- [Anti-patterns](#anti-patterns)

## Required workflow

1. Inspect the existing report's page, visual, and filter names.
2. Copy `$schema` values from bookmark files in the same report. If the report
   has no bookmarks, use the schema versions in the templates below and let
   Desktop upgrade them on save.
3. Create each `definition/bookmarks/<bookmarkName>.bookmark.json`.
4. Add every bookmark to `definition/bookmarks/bookmarks.json`, directly or as
   a group child.
5. Wire any button actions to the bookmark's exact `name`.
6. Run `powerbi-report-author validate <Report>.Report`.
7. Reload in Desktop and exercise every forward and reverse transition.

Bookmark state contains raw PBIR identifiers, not display names:

- Page references use `page.json` → `name`.
- Visual references use `visual.json` → `name`.
- Newly authored live filter state starts from the matching
  `filterConfig.filters[]` entry.
- Button targets use the bookmark file's `name`.

Do not invent or shorten these identifiers.

## File layout

```text
definition/
├── bookmarks/
│   ├── bookmarks.json
│   ├── <bookmarkName>.bookmark.json
│   └── <bookmarkName>.bookmark.json
└── pages/
```

The bookmark file name and its `name` property must match:

```text
definition/bookmarks/32e6a5dec73817815177.bookmark.json
```

```json
{
  "name": "32e6a5dec73817815177"
}
```

The validator reports `PBIR_BOOKMARK_NAME_FILE_MISMATCH` when they differ.

## Bookmark index and groups

`bookmarks.json` controls the report's bookmark ordering and groups.

### Ungrouped bookmark

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmarksMetadata/1.0.0/schema.json",
  "items": [
    {
      "name": "32e6a5dec73817815177"
    }
  ]
}
```

### Bookmark group

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmarksMetadata/1.0.0/schema.json",
  "items": [
    {
      "displayName": "View selector",
      "name": "b95e490160978ca1c3d9",
      "children": [
        "32e6a5dec73817815177",
        "b7082154158c6ccc84be"
      ]
    }
  ]
}
```

Rules:

- Every child must name an existing `.bookmark.json` file.
- A bookmark must appear exactly once in the index.
- The group `name` is its own unique ID; it does not need a bookmark file.
- `displayName` is user-facing and may contain spaces.
- An unindexed bookmark file does not appear in the report bookmark list.

## Bookmark state

A bookmark has three main sections:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmark/2.1.0/schema.json",
  "displayName": "Show chart",
  "name": "32e6a5dec73817815177",
  "options": {
    "targetVisualNames": [],
    "suppressData": true,
    "suppressDisplay": false,
    "suppressActiveSection": true,
    "applyOnlyToTargetVisuals": false
  },
  "explorationState": {
    "version": "1.3",
    "activeSection": "fb1f349df66655761237",
    "sections": {}
  }
}
```

### Options mapping

PBIR stores the inverse of several Desktop bookmark checkboxes:

| Desktop bookmark option | PBIR field | Enabled value |
|---|---|---|
| Data | `suppressData` | `false` |
| Display | `suppressDisplay` | `false` |
| Current page | `suppressActiveSection` | `false` |
| Selected visuals | `applyOnlyToTargetVisuals` | `true` |

Use these combinations deliberately:

| Pattern | Data | Display | Current page | Selected visuals |
|---|---:|---:|---:|---:|
| Show/hide or chart swap | Off | On | Usually Off | Usually Off |
| Reset filters/slicers | On | Optional | Off | Usually Off |
| Story step across pages | As needed | On | On | Usually Off |

For a pure visibility toggle, keep Data off (`suppressData: true`) so clicking
the bookmark does not reset slicers or filters.

### Target visuals

For deterministic display snapshots, list the exact visual IDs, include state
entries only for those visuals, and default `applyOnlyToTargetVisuals` to
`false`:

```json
"options": {
  "targetVisualNames": [
    "f0b7a9e5317ef5d3cb16",
    "9f489283587461417621"
  ],
  "suppressData": true,
  "suppressDisplay": false,
  "suppressActiveSection": true,
  "applyOnlyToTargetVisuals": false
}
```

Every targeted visual should also have a state entry in the relevant page's
`visualContainers`. Avoid targeting only the visual that becomes visible:
include both sides of a toggle so the reverse transition is deterministic.

Use `applyOnlyToTargetVisuals: true` only when the user explicitly requests
Desktop's **Selected visuals** bookmark option. Physically verify that state:
some Desktop builds accept the PBIR but ignore authored display or filter state
when this flag is enabled.

## Visibility toggles and chart swaps

Visibility is stored in:

```text
explorationState.sections.<pageName>.visualContainers.<visualName>
```

A visible visual can use an empty state:

```json
"f0b7a9e5317ef5d3cb16": {
  "singleVisual": {}
}
```

A hidden visual uses `display.mode: "hidden"`:

```json
"9f489283587461417621": {
  "singleVisual": {
    "display": {
      "mode": "hidden"
    }
  }
}
```

Complete two-bookmark chart/table toggle:

```json
{
  "displayName": "Show chart",
  "name": "32e6a5dec73817815177",
  "options": {
    "targetVisualNames": [
      "f0b7a9e5317ef5d3cb16",
      "9f489283587461417621"
    ],
    "suppressData": true,
    "suppressDisplay": false,
    "suppressActiveSection": true,
    "applyOnlyToTargetVisuals": false
  },
  "explorationState": {
    "version": "1.3",
    "activeSection": "fb1f349df66655761237",
    "sections": {
      "fb1f349df66655761237": {
        "visualContainers": {
          "f0b7a9e5317ef5d3cb16": {
            "singleVisual": {}
          },
          "9f489283587461417621": {
            "singleVisual": {
              "display": {
                "mode": "hidden"
              }
            }
          }
        }
      }
    }
  }
}
```

The paired "Show table" bookmark must store the inverse state for **both**
visuals. The same pattern applies to detail panels: include the panel shape,
text, controls, and close button in both the show and hide bookmarks.

## Current page

To save and apply a page:

```json
"options": {
  "suppressActiveSection": false
},
"explorationState": {
  "activeSection": "fb1f349df66655761237"
}
```

To keep the user on the current page, use
`suppressActiveSection: true`. The `activeSection` value may still be present
as captured metadata, but it is not applied.

Every key under `explorationState.sections` must also be an existing page ID.

## Filter and slicer state

Data-enabled bookmarks can restore filters at all three filter scopes. Current
Desktop-authored PBIR stores them in `byExpr` arrays:

| Filter scope | Bookmark state path |
|---|---|
| Report | `explorationState.filters.byExpr[]` |
| Page | `explorationState.sections.<pageId>.filters.byExpr[]` |
| Visual | `explorationState.sections.<pageId>.visualContainers.<visualId>.filters.byExpr[]` |

Use the same filter `name`, `type`, expression, and predicate as the matching
`filterConfig.filters[]` entry at that scope when authoring a bookmark for a
current live filter. Desktop-authored snapshots can legitimately retain saved
filter entries after the corresponding live filter card is removed, so do not
reject an existing snapshot solely because its `name` is absent from the
current `filterConfig`. A verified categorical entry is:

```json
"filters": {
  "byExpr": [
    {
      "name": "Filter4f088dcd17c3495bb785",
      "type": "Categorical",
      "filter": {
        "Version": 2,
        "From": [
          {
            "Name": "c",
            "Entity": "Company",
            "Type": 0
          }
        ],
        "Where": [
          {
            "Condition": {
              "In": {
                "Expressions": [
                  {
                    "Column": {
                      "Expression": {
                        "SourceRef": {
                          "Source": "c"
                        }
                      },
                      "Property": "Company"
                    }
                  }
                ],
                "Values": [
                  [
                    {
                      "Literal": {
                        "Value": "'Contoso'"
                      }
                    }
                  ]
                ]
              }
            }
          }
        ]
      },
      "expression": {
        "Column": {
          "Expression": {
            "SourceRef": {
              "Entity": "Company"
            }
          },
          "Property": "Company"
        }
      },
      "howCreated": 1
    }
  ]
}
```

The top-level `expression` uses `SourceRef.Entity`, while expressions inside
`filter.Where` use `SourceRef.Source` with the alias from `filter.From`.
`howCreated: 1` identifies the user-created filter card. Desktop may also
capture generated visual field cards with `howCreated: 0`; preserve them when
copying Desktop-authored state, but do not mistake them for authored filter
predicates.

Do not use `filters.byName` for newly authored bookmark filter state. It can
schema-validate while Desktop silently restores the filter as `(All)`.

Data-on bookmarks restore the complete captured data state, not one isolated
filter scope. A bookmark intended to demonstrate a report, page, or visual
filter should explicitly capture the other scopes as selected values or
`(All)`. Do not promise that separate filter-scope bookmarks compose
independently; switching bookmarks can reset unspecified scopes.

Slicer selections remain under the slicer's
`singleVisual.objects.merge.general[].properties.filter.filter` state. See
filters.md (see `filters.md`) and slicers.md (see `slicers.md`).

For visibility-only bookmarks, omit filter state and set
`suppressData: true`.

## Bookmark buttons

Wire an `actionButton` through
`visual.visualContainerObjects.visualLink`:

```json
"visualContainerObjects": {
  "visualLink": [
    {
      "properties": {
        "show": {
          "expr": {
            "Literal": {
              "Value": "true"
            }
          }
        },
        "type": {
          "expr": {
            "Literal": {
              "Value": "'Bookmark'"
            }
          }
        },
        "bookmark": {
          "expr": {
            "Literal": {
              "Value": "'32e6a5dec73817815177'"
            }
          }
        }
      }
    }
  ]
}
```

The target is the bookmark `name`, not its `displayName`. The validator reports:

- `PBIR_BOOKMARK_ACTION_TARGET_MISSING` when the target property is absent.
- `PBIR_BOOKMARK_ACTION_REF_MISSING` when the named bookmark does not exist.

See button.md (see `button.md`) for complete button structure and state formatting.

## Bookmark navigator

`bookmarkNavigator` is a no-data-role visual that renders report bookmarks.
Its bookmark-group binding is not a plain string literal in all Desktop
versions. Until the CLI exposes a typed encoder for that property:

- Preserve an existing Desktop-authored bookmark navigator.
- Copy a known-good navigator only within the same report and group structure.
- Do not guess the `bookmarks.bookmarkGroup` expression shape.
- Prefer explicit `actionButton` bookmark actions for deterministic new
  authoring.

## Validation diagnostics

`powerbi-report-author validate` reports broken bookmark semantics with stable
codes:

| Code | Meaning |
|---|---|
| `PBIR_BOOKMARKS_METADATA_MISSING` | Bookmark files exist without `bookmarks.json` |
| `PBIR_BOOKMARK_NAME_FILE_MISMATCH` | Bookmark `name` differs from its file name |
| `PBIR_BOOKMARK_NAME_DUPLICATE` | Multiple files declare the same bookmark name |
| `PBIR_BOOKMARK_INDEX_REF_MISSING` | Index/group references a missing bookmark |
| `PBIR_BOOKMARK_INDEX_DUPLICATE_REFERENCE` | Bookmark appears more than once in the index |
| `PBIR_BOOKMARK_FILE_NOT_INDEXED` | Bookmark file is not present in the index |
| `PBIR_BOOKMARK_PAGE_REF_MISSING` | Saved state references a missing page |
| `PBIR_BOOKMARK_VISUAL_REF_MISSING` | Target or section references a missing visual |
| `PBIR_BOOKMARK_ACTION_TARGET_MISSING` | Bookmark action has no target |
| `PBIR_BOOKMARK_ACTION_REF_MISSING` | Bookmark action targets a missing bookmark |

## Desktop verification checklist

After validation succeeds:

1. Reload the report in Desktop.
2. Confirm all bookmarks appear in the expected order/group.
3. Exercise each bookmark from a neutral state.
4. Exercise every pair in both directions: A → B → A.
5. Change slicers before a visibility bookmark and confirm they remain changed.
6. Confirm show/hide groups include every panel component.
7. Confirm Current page behavior matches the intended navigation.
8. Click every bookmark button and check that it is enabled.
9. Save, reload, and repeat the cycle to catch Desktop normalization issues.

## Anti-patterns

| Anti-pattern | Result | Fix |
|---|---|---|
| File name and bookmark `name` differ | Broken identity and index references | Use one exact ID in both places |
| Bookmark file omitted from `bookmarks.json` | Bookmark is not exposed in the report | Add it directly or as a group child |
| Visibility bookmark has Data enabled | Slicers and filters unexpectedly reset | Set `suppressData: true` |
| Toggle saves only the visual being shown | Reverse transition leaves both visuals visible/hidden | Save explicit state for both sides |
| Using page or visual display names | References do not resolve | Use raw PBIR `name` IDs |
| Button targets bookmark `displayName` | Button is disabled | Target bookmark `name` |
| Guessing navigator group encoding | Navigator may ignore the group or fail schema validation | Preserve a Desktop-authored navigator |
