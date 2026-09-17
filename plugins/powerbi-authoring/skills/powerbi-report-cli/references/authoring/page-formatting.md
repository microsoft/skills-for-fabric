# Page-Level Formatting (`page.json` objects)

Page formatting controls the page canvas, wallpaper, and page-level background
images. All stored in `page.json → objects` using PBIR expression encoding.

> **Read first:** [`formatting-overview.md`](formatting-overview.md) for the
> cascade model and encoding rules. For visual-level formatting (inside
> `visual.json`), see [`formatting.md`](formatting.md). For filter pane and
> filter card chrome (also in `page.json` but a separate concern), see
> [`filter-pane.md`](filter-pane.md).

## Contents

- [Canvas Background (`background`)](#canvas-background-background)
- [Wallpaper (`outspace`)](#wallpaper-outspace)
- [Background Images](#background-images)

## Canvas Background (`background`)

The canvas rectangle behind all visuals. This is a **page-level** object —
NOT the same as VCO `background` on visuals.

> **⚠️ Page background has NO `show` property.** It is always visible.
> Only VCO `background` (on visuals) supports `show`. Do not add
> `"show": true/false` to page background — the schema will reject it.

```json
"background": [{
  "properties": {
    "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#F5F5F5'" } } } } },
    "transparency": { "expr": { "Literal": { "Value": "0D" } } }
  }
}]
```

Properties: `color` (fill), `image` (see below), `transparency` (0–100).

## Wallpaper (`outspace`)

The area behind/outside the canvas:

```json
"outspace": [{
  "properties": {
    "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#0D1117'" } } } } },
    "transparency": { "expr": { "Literal": { "Value": "0D" } } }
  }
}]
```

Same properties as `background`: `color`, `image`, `transparency`.

**⚠️ Transparency pitfall**: Canvas background at high transparency (e.g., white at 80%)
creates a translucent overlay — the wallpaper bleeds through creating unexpected
composite colors. For dark themes, set both layers to opaque dark colors.

## Background Images

Both `background` and `outspace` support images. The `image` property uses a **nested `image` sub-object** — the same structure as visual plot area background images (see [`image.md` § Plot Area Background Image](image.md#plot-area-background-image-plotareaimage)).

**⚠️ Both page backgrounds and visual plot areas use the nested `image.image` structure** (`image.image.name`, `image.image.url`, `image.image.scaling`). A flat `image.name/url/scaling` will silently fail to render.

**⚠️ The image must be copied to `StaticResources/RegisteredResources/` and registered in `report.json` — see [`image.md`](image.md) for the registration workflow.**

```json
"background": [{
  "properties": {
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
    },
    "transparency": { "expr": { "Literal": { "Value": "0D" } } },
    "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } }
  }
}]
```

**Image fit modes:**

| Value | Behavior |
|-------|----------|
| `'Fit'` | Fit within bounds, preserve aspect ratio (may letterbox) |
| `'Stretch'` | Stretch to fill bounds exactly (may distort) |
| `'Fill'` | Fill bounds, preserve aspect ratio (may crop) |

## See Also

- [`filter-pane.md`](filter-pane.md) — filter pane (`outspacePane`) and
  filter card (`filterCard`) appearance, also stored in `page.json → objects`.
