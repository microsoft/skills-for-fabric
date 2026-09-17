# Image Visual Authoring Guide

Create and configure image visuals in PBIR format. Covers all three source types
and links to formatting reference for styling.

## Table of Contents
- [Source Types Overview](#source-types-overview)
- [1. Local File Image](#1-local-file-path-to-the-image)
- [2. URL Image](#2-a-url-from-the-web)
- [3. Data-Bound Image](#3-select-from-data)
- [Image Formatting (`objects.image`)](#image-formatting-objectsimage)
- [Plot Area Background Image (`plotArea.image`)](#plot-area-background-image-plotareaimage)

---

## Source Types Overview

The report could be a new report or an existing report that might have pages and visuals already added, there could be images already in the resources folder and registered. In any case, do not assume the source type and source of the image. Please follow the below steps:

The input to the image to render the image visual could be from any of the following sources
1. Local file path to the image
2. A url (from the web)
3. Select from data

If the user has not specified the source or just asks to add a new image, prompt the user with the source options. Do NOT even render an empty image visual layout, prompt for the source first unless the user mentions to render only the layout specifically.

Each source has a different structure and different set of properties.

### 1. Local file path to the image

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 16, "y": 16, "z": 0, "height": 104, "width": 304, "tabOrder": 0 },
  "visual": {
    "visualType": "image",
    "objects": {
      "general": [{
        "properties": {
          "imageUrl": {
            "expr": {
              "ResourcePackageItem": {
                "PackageName": "RegisteredResources",
                "PackageType": 1,
                "ItemName": "<filename_in_RegisteredResources>.<ext>"
              }
            }
          }
        }
      }]
    },
    "drillFilterOtherVisuals": true
  }
}
```
**⚠️ Important**: Image visuals use `ResourcePackageItem` expression (NOT a URL literal).
The image file must exist in `StaticResources/RegisteredResources/` and be registered
in `report.json` → `resourcePackages[]`. If the image already exists,
then do not add a duplicate copy, use the existing one.

**Filename convention**: When copying an image to `RegisteredResources/`, append a unique numeric
suffix (e.g., a timestamp) to the base filename before the extension — this replicates Power BI
Desktop's behavior and avoids name collisions. The original filename is preserved as the display
name in `image.image.name` (for background images) or `ResourcePackageItem.ItemName` references
use the suffixed name.

| Concept | Example |
|---------|---------|
| Original file | `screenshot2.png` |
| File on disk in RegisteredResources | `screenshot217123456789012345.png` |
| `report.json` resource `name` & `path` | `screenshot217123456789012345.png` |
| `ResourcePackageItem.ItemName` | `screenshot217123456789012345.png` |
| `image.image.name` (display name) | `'screenshot2.png'` |

**Registration in `report.json`** — add a `RegisteredResources` entry (or append to an existing one):

```json
"resourcePackages": [
  {
    "name": "RegisteredResources",
    "type": "RegisteredResources",
    "items": [
      {
        "name": "my_image17123456789012345.png",
        "path": "my_image17123456789012345.png",
        "type": "Image"
      }
    ]
  }
]
```

- **`type` must be `"Image"`** — not `"ResourceItem"` or any other value (fails schema validation).
- **All filenames must include the file extension** (e.g., `.png`, `.jpg`, `.svg`). Omitting the extension changes the file type and breaks image rendering.
- **`name`** is the identifier used by `ResourcePackageItem.ItemName` in the visual — it must match exactly.
- **`path`** is the filename on disk in `StaticResources/RegisteredResources/`.
- **`ResourcePackageItem.ItemName`** in the visual must match the `name` field in the resource package entry.

### 2. A url (from the web)

**⚠️ URL image requirements**:
- The URL must be **publicly accessible** (anonymous access, no sign-in required). Test by opening in a browser incognito window.
- The URL must point **directly to an image file** (e.g., ending in `.jpg`, `.png`, `.gif`, `.bmp`, `.svg`), not a webpage containing the image.
- Use **HTTPS** URLs — HTTP may work in Desktop but can be blocked by the Power BI Service.
- Reference: https://community.fabric.microsoft.com/t5/Desktop/Image-URL-creation/td-p/1910627

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 16, "y": 16, "z": 0, "height": 104, "width": 304, "tabOrder": 0 },
  "visual": {
    "visualType": "image",
    "objects": {
      "image": [
        {
          "properties": {
            "sourceType": {
              "expr": {
                "Literal": {
                  "Value": "'imageUrl'"
                }
              }
            },
            "sourceUrl": {
              "expr": {
                "Literal": {
                  "Value": "'<url_to_the_image_location>'"
                }
              }
            }
          }
        }
      ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

### 3. Select from data
For data-bound image URLs, the column or measure must have **Data Category set to "Image URL"** in the semantic model.

> ⚠️ **Validate the field before creating a data-bound image visual.**
> Before creating ANY data-bound image visual:
> 1. Search the TMDL file for the **specific field the user requested** and check whether it has `dataCategory: ImageUrl`.
> 2. If the field does **not** have `dataCategory: ImageUrl`, warn the user before proceeding — the visual will render blank or error, and the user may not know this requirement. Present alternatives (other ImageUrl fields, local file, URL, or adding `dataCategory: ImageUrl` in the semantic model) and confirm the user's choice before creating.
> 3. Proceed when the field has `dataCategory: ImageUrl`, or after the user has chosen an alternative.

**Before creating a data-bound image visual**, always inspect the TMDL files and search for `dataCategory: ImageUrl`. This tells you which fields can render as images.

- **Requested field lacks ImageUrl** → **Warn the user before creating.** The requested field (e.g., `Revenue`) is not image-capable because it has no `dataCategory: ImageUrl`. Suggest alternatives: (1) use a field that does have `dataCategory: ImageUrl` (list any you found), (2) use a local file or URL image instead, or (3) add `dataCategory: ImageUrl` to a column/measure in the semantic model that contains image URLs. Confirm the user's choice before creating.
- **No ImageUrl fields found at all** → Inform the user that the semantic model has no fields with the ImageUrl data category. Suggest the local file or URL alternatives and confirm before creating any data-bound image visual.
- **One ImageUrl field found** → You can safely use that field/measure to render the image.
- **Multiple ImageUrl fields found** → Prompt the user to select which field/measure to use. Do NOT randomly select one unless the user asks to do so.

**From a measure:**

```json
"sourceField": {
  "expr": {
    "Measure": {
      "Expression": {
        "SourceRef": {
          "Entity": "<TableName>"
        }
      },
      "Property": "<MeasureName>"
    }
  }
}
```

**From a column** (wrapped in Aggregation with `Function: 3` = Min):

```json
"sourceField": {
  "expr": {
    "Aggregation": {
      "Expression": {
        "Column": {
          "Expression": {
            "SourceRef": {
              "Entity": "<TableName>"
            }
          },
          "Property": "<ColumnName>"
        }
      },
      "Function": 3
    }
  }
}
```

Full visual template (using measure example):

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 16, "y": 16, "z": 0, "height": 280, "width": 280, "tabOrder": 0 },
  "visual": {
    "visualType": "image",
    "objects": {
      "image": [
        {
          "properties": {
            "sourceType": {
              "expr": {
                "Literal": {
                  "Value": "'imageData'"
                }
              }
            },
            "sourceField": {
              "expr": {
                "Measure": {
                  "Expression": {
                    "SourceRef": {
                      "Entity": "<TableName>"
                    }
                  },
                  "Property": "<MeasureName>"
                }
              }
            }
          }
        }
      ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

## Image Formatting (`objects.image`)

Image visuals have formatting properties under the `image` object
(`objects.image`) that control the **image content area** (border, background,
corner radius, effects). Discover these via the CLI:

```bash
powerbi-report-author formatting describe-object image image    # image-level properties
powerbi-report-author formatting search image <property>      # find which object owns a property
```

### Image object vs Visual Container Objects (VCO) — overlapping properties

Image visuals have **two layers** of formatting that can both be active at the
same time:

| Concern | Image object (`objects.image`) | VCO (`visualContainerObjects`) |
|---------|-------------------------------|-------------------------------|
| **Scope** | The image content area | The outer visual container card (title, subtitle area included) |
| **Border** | `strokeShow/strokeColor/strokePattern/strokeWidth/strokeTransparency` — supports `solid`, `dashed`, `dotted` | `border.show/color/width/radius` — solid only |
| **Background** | `backgroundEnabled/backgroundColor` — behind the image content | `background.show/color/transparency` — behind the entire card |
| **Corner radius** | `cornerRadius` + per-corner variants — rounds the image content | `border.radius` — rounds the outer card |

**⚠️ Routing rule for image visuals** — because both layers have overlapping
concerns (border, background, corner radius), always run
`powerbi-report-author formatting search image <property>` to find the correct
object before setting a value. The `image` object properties control the image
content area; VCO properties control the outer card container.

## Plot Area Background Image (`plotArea.image`)

This is **not** an image visual — it's a background image rendered *behind* the
data area of a chart visual (bar, column, line, etc.) that supports a
`plotArea` formatting object.

> **Routing — "background image" disambiguation:**
> - "background image" in the context of a specific chart visual →
>   `visual.objects.plotArea.image` (this section)
> - "page background image" / "canvas background" →
>   [`page-formatting.md` § Background Images](page-formatting.md#background-images)
> - User adds an image visual itself → see [Source Types Overview](#source-types-overview) above

Confirm the visual type supports `plotArea` with
`powerbi-report-author formatting search <visualType> "plotArea"`, then inspect
the `image` sub-structure with
`powerbi-report-author formatting describe-object <visualType> plotArea`.

### Example — Local registered resource as plot area background

```json
"plotArea": [{
  "properties": {
    "transparency": { "expr": { "Literal": { "Value": "0D" } } },
    "image": {
      "image": {
        "name": { "expr": { "Literal": { "Value": "'my-bg-image.png'" } } },
        "url": {
          "expr": {
            "ResourcePackageItem": {
              "PackageName": "RegisteredResources",
              "PackageType": 1,
              "ItemName": "my-bg-image17123456789012345.png"
            }
          }
        },
        "scaling": { "expr": { "Literal": { "Value": "'Fit'" } } }
      }
    }
  }
}]
```

**⚠️ Both visual plot areas and page backgrounds use the nested `image.image` structure** (`image.image.name`, `image.image.url`, `image.image.scaling`). A flat `image.name/url/scaling` will silently fail to render.

**⚠️ Registration required:** The referenced image must be copied to
`StaticResources/RegisteredResources/` and registered in `report.json` — same
workflow as the local-file image source above.