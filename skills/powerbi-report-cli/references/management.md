
## Contents

- [Companion Skills](#companion-skills)
- [Tool Stack](#tool-stack)
  - [Deterministic PBIR Transport Helper](#deterministic-pbir-transport-helper)
  - [Modern-PBIR preflight before pack](#modern-pbir-preflight-before-pack)
- [Authentication](#authentication)
- [Finding Workspaces and Reports](#finding-workspaces-and-reports)
  - [Resolve Report ID by Name](#resolve-report-id-by-name)

<!-- Mode reference for the `powerbi-report-cli` skill. Loaded on demand from `skills/powerbi-report-cli/SKILL.md` when the request matches the `management` mode. -->

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. **Never publish or overwrite the remote report with local changes until
>    the user explicitly gives permission.** Approval of edits, validation,
>    screenshots, preview, or a previous publish is not permission for a new
>    remote write. If the current request does not explicitly ask to publish,
>    upload, push, or deploy the local changes, or you are unsure, keep the
>    changes local and do not publish — do not pack or call any mutating Fabric
>    API, and do not ask to publish.
> 4. **Never overwrite an existing remote report without explicit user
>    permission to publish and overwrite.** When the user has already asked to
>    publish, confirm they agree to overwrite the existing report before calling
>    `updateDefinition`. Do not call `updateDefinition` based only on a general
>    publish request.

# powerbi-report-cli management mode -- Power BI Report Items in Fabric

Manage Power BI reports in Microsoft Fabric workspaces using `az rest` against
the Fabric REST API. This skill covers the full CRUD lifecycle for report items
and their PBIR definitions.

> **Scope**: Report item CRUD and definition management only. For report layout
> authoring (pages, visuals, filters, formatting), use the `authoring` mode.

> **Boundary**: This skill transports PBIR definitions to and from Fabric. PBIR
> content authoring remains owned by the `authoring` mode.

## Companion Skills

This skill is one of three that partition the Power BI authoring surface.
Each owns a single concern; route work to the right one.

| Skill | Owns | Use for |
|---|---|---|
| `authoring` mode | Report content (PBIR JSON authoring) | Pages, visuals, filters, formatting, themes, expressions, `definition.pbir`, `version.json`, `report.json` |
| `management` mode (this mode) | Report transport to/from Fabric | List, create, get, update, delete report items; download/upload PBIR definitions |
| Semantic-model authoring skill | Semantic model authoring + deployment | Create/edit measures/tables/relationships, TMDL, deploy semantic models to Fabric |

**When publishing a local `.pbip` to Fabric**, this skill is the entry
point. If the user wants to publish the local semantic model alongside
the report, this skill delegates the model deploy to
an available semantic-model authoring skill, then resolves
the resulting `semanticModelId` and binds the report to it. See
**Publishing a local .pbip** in `management-part-04.md`.

## Tool Stack

| Tool | Role | Install |
|---|---|---|
| `az` CLI | **Primary**: `az rest` for Fabric REST API calls, `az login` for auth | Pre-installed in most dev environments |
| `powerbi-report-author` (>= 0.3.0-beta.0) | **Required PBIR transport helper** for all primary documented workflows: deterministic `pack`/`unpack` for base64 encode/decode, part walking, path normalization, and Fabric request-body generation | Install or upgrade via the `authoring` mode CLI setup (`@microsoft/powerbi-report-authoring-cli@latest`) |
| `jq` / `base64` | **Not supported as an executable workflow in this skill**. Mentioned only to describe safety requirements for reviewing external legacy/manual recipes. | Do not install or use as a substitute for `powerbi-report-author`; install/upgrade the CLI instead. |

> **Agent check** — verify before first operation:
>
> ```bash
> set -euo pipefail
> if ! az version >/dev/null 2>&1; then
>   echo "INSTALL: https://learn.microsoft.com/cli/azure/install-azure-cli"
>   exit 1
> fi
> MIN_POWERBI_REPORT_AUTHOR_VERSION="0.3.0-beta.0"
> POWERBI_REPORT_AUTHOR_VERSION=$(powerbi-report-author --version 2>/dev/null || true)
> node -e 'const p=s=>{const m=/^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$/.exec((s||"").trim());return m&&{n:m.slice(1,4).map(Number),pre:m[4]?m[4].split("."):[]};};const c=(a,b)=>{for(let i=0;i<3;i++){if(a.n[i]!==b.n[i])return a.n[i]-b.n[i];}if(!a.pre.length||!b.pre.length)return a.pre.length?-1:b.pre.length?1:0;for(let i=0;i<Math.max(a.pre.length,b.pre.length);i++){if(a.pre[i]===undefined)return-1;if(b.pre[i]===undefined)return 1;if(a.pre[i]===b.pre[i])continue;const an=/^\d+$/.test(a.pre[i]),bn=/^\d+$/.test(b.pre[i]);if(an&&bn)return Number(a.pre[i])-Number(b.pre[i]);if(an!==bn)return an?-1:1;return a.pre[i].localeCompare(b.pre[i]);}return 0;};const g=p(process.argv[1]),m=p(process.argv[2]);process.exit(g&&m&&c(g,m)>=0?0:1);' "$POWERBI_REPORT_AUTHOR_VERSION" "$MIN_POWERBI_REPORT_AUTHOR_VERSION" || { echo "INSTALL/UPGRADE: powerbi-report-author >= $MIN_POWERBI_REPORT_AUTHOR_VERSION required (found ${POWERBI_REPORT_AUTHOR_VERSION:-missing}). Run: npm install -g @microsoft/powerbi-report-authoring-cli@latest"; exit 1; }
> ```
>
> The `npm install -g @microsoft/powerbi-report-authoring-cli@latest` command is shell-neutral; run it unchanged from Bash, PowerShell, or cmd.
> If the `powerbi-report-author >= 0.3.0-beta.0` check fails, stop and install or
> upgrade the CLI. Do not continue with manual jq/base64/find/PowerShell
> directory-walking recipes.

### Deterministic PBIR Transport Helper

Use `powerbi-report-author pack`/`unpack` (see `authoring/powerbi-report-author-cli.md`)
for report definition bodies in every primary workflow. Version 0.3.0-beta.0 or newer
of `powerbi-report-author` is a hard requirement for this skill's executable
create, download, and update definition paths. This skill still owns transport
through `az rest`, LRO polling, and create/update decision; the CLI replaces
the hand-written base64 + directory-walk steps.

- `pack <folder>` accepts a `.pbip` file, a `.Report` directory, or a directory
  containing `definition/`, then emits deterministic PBIR parts from the
  resolved `.Report` boundary. It emits **all qualifying parts** every time,
  with forward-slash paths and `payloadType: "InlineBase64"`.
- Default `pack` output is the standard CLI success envelope
  (`{"data":{...}}`). Use `pack --raw` whenever the output is used as the
  Fabric request body, including both direct pipes and `--out body.json` file
  writes. Do not use the removed envelope opt-in flag; the current request-body
  switch is `--raw`.
- `pack --mode create` requires `--display-name`; `--description` is optional.
  Update payloads use the default update mode and must not include a display
  name.
- `unpack <folder>` reads the Fabric `getDefinition` JSON from stdin by
  default. `--input <file>` supersedes stdin and is the recommended robust
  file-based flow after saving an `az rest` result. The default is no-clobber
  for the first unpack; use `--force` only after confirming the target is the
  intended disposable download workspace, never a durable local source folder.
- `unpack` is PBIR-only. If Fabric returns PBIR-Legacy (or any non-PBIR format),
  it fails early with `UNPACK_FORMAT_UNSUPPORTED` instead of partially decoding
  an unsupported legacy blob.

### Modern-PBIR preflight before pack

`pack` performs no format check, so every `pack` invocation in this skill must
confirm the source is modern PBIR first. Run this preflight before the create,
update, and publish-local flows.

- Confirm a modern `definition/` layout with `definition/report.json` present.
- Run `powerbi-report-author validate "<path-to-.Report>"` and fix every error
  before packing.

A legacy `.Report` that still contains `definition.pbir` packs a partial payload,
and replace-all `updateDefinition` then deletes the omitted parts.

## Authentication

All calls use the Fabric API audience. Using the wrong audience returns a 401.

| API | Audience (`--resource`) |
|---|---|
| Fabric Report Items API | `https://api.fabric.microsoft.com` |

For the shared authentication model, token audiences, and identity types, see
COMMON-CORE.md § Authentication & Token Acquisition (see `../../../common/COMMON-CORE.md`, section `authentication--token-acquisition`).

For full authentication recipes (interactive, device-code, service principal, managed identity),
see COMMON-CLI.md § Authentication Recipes (see `../../../common/COMMON-CLI.md`, section `authentication-recipes`).

## Finding Workspaces and Reports

> **Shared patterns** — workspace and item resolution, pagination, and LRO polling
> are documented in the common skill library.
> Read COMMON-CLI.md § Finding Workspaces and Items in Fabric (see `../../../common/COMMON-CLI.md`, section `finding-workspaces-and-items-in-fabric`)
> **before** using the CRUD operations below.

### Resolve Report ID by Name

Once you have the workspace ID (per COMMON-CLI.md), resolve the report:

```bash
REPORT_NAME="Sales Report"
REPORT_ID=$(az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports" \
  --query "value[?displayName=='$REPORT_NAME'] | [0].id" \
  --output tsv)
```
