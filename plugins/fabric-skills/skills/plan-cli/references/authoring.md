<!-- Mode reference for the `plan-cli` skill. Loaded on demand from `skills/plan-cli/SKILL.md` when the request matches the `authoring` mode. -->

> **PRE-MUTATION REQUIREMENTS GATE (mandatory)**
> Before any create, rename/re-describe, or delete, confirm the request identifies
> the target workspace and the specific Plan. If the request is generic or
> ambiguous, such as "set up a plan for me" or "clean up the old plans", ask a
> clarifying question and stop before mutation. Delete has no documented recovery
> for a Plan -- always echo the resolved `displayName` + `id` for the audit trail.
> When the request already names the target item AND the destructive action
> explicitly (for example "delete the Budget 2027 Plan"), that instruction IS
> the confirmation: proceed with the single write after echoing. Ask for a
> separate yes/no confirmation only when the target or intent is ambiguous
> (a partial name match, more than one match, "clean up my workspace", or a
> bulk/wildcard delete).

# plan-cli authoring mode — Plan Item Authoring via CLI

> **Scope**: this mode creates, renames/re-describes and deletes the Plan
> **item** itself. By design it does not write sheets, visuals, the saved
> definition, or any narrative/visual data. Fabric does document an
> `updateDefinition` API for Plan items, but definition writes are out of
> scope for this skill, and `consumption` mode's narrative refusal still
> applies to them.
>
> **Permissions**: Create requires a workspace **Contributor** role (or
> higher) and `Item.ReadWrite.All`. Update requires read and write permission
> on the Plan; Delete requires write permission on the Plan; both need
> `Item.ReadWrite.All`. Every operation supports
> user, service-principal and managed-identity callers. Creating a Plan
> requires the workspace to be on a supported Fabric capacity.

## Contents

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | COMMON-CLI.md § Finding Workspaces and Items in Fabric (linked from SKILL.md) | **Mandatory** -- resolve the workspace and, for rename/delete, the Plan id by listing and filtering; never guess a GUID |
| Fabric Control-Plane API via `az rest` | COMMON-CLI.md § Fabric Control-Plane API via az rest (linked from SKILL.md) | **Always pass `--resource https://api.fabric.microsoft.com`** |
| Item CRUD Operations | COMMON-CLI.md § Item CRUD Operations (linked from SKILL.md) | Generic create/PATCH/DELETE shape; Plan follows it exactly, with no `definition` and no `updateMetadata` in this mode |
| Long-Running Operations (LRO) | COMMON-CLI.md § Long-Running Operations (LRO) Pattern, `fabric_lro` (linked from SKILL.md) | Create may return `202 Accepted` on a **different host** than the initiating one; prefer `x-ms-operation-id` and poll the public host |
| Create a Plan | [Create a Plan](#create-a-plan) | Empty item only in this mode; no `definition` in the body |
| Rename or re-describe a Plan | [Rename or re-describe a Plan](#rename-or-re-describe-a-plan) | `displayName` and/or `description` via PATCH; synchronous, no LRO |
| Delete a Plan | [Delete a Plan](#delete-a-plan) | No `hardDelete` parameter; no documented recovery |
| Errors and troubleshooting | [Errors and troubleshooting](#errors-and-troubleshooting) | `ItemDisplayNameAlreadyInUse`, `ItemDisplayNameNotAvailableYet`, capacity and permission errors |
| Must / Prefer / Avoid | [Must / Prefer / Avoid](#must--prefer--avoid) | |
| Examples | [Examples](#examples) | |

---

## Create a Plan

Create a new Plan item with the
[Create Plan](https://learn.microsoft.com/en-us/rest/api/fabric/plan/items/create-plan)
operation (scope `Item.ReadWrite.All`, workspace **Contributor**). The request body
takes a required `displayName` and an optional `description` (**max 256 characters**).
This mode never sends a `definition` in the create body -- an empty Plan only.

Before calling, list the workspace's Plans and resolve an exact `displayName` match.
If one already exists, stop and report the conflict (see
[Errors and troubleshooting](#errors-and-troubleshooting)) -- do not silently
auto-rename or reuse the existing item.

```bash
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/plans" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "x-ms-fabric-skill=plan-cli" \
  --body '{"displayName":"Budget 2027","description":"FY27 planning cycle"}'
```

The call returns **`201 Created`** with the new item on the synchronous path, or
**`202 Accepted`** (LRO) while provisioning continues. On a live test-tenant
trial, Create actually returned `202` with the `Location` header pointing at a
**different (cluster) host** than `api.fabric.microsoft.com` -- this is exactly
the case the shared LRO guidance exists for: prefer `x-ms-operation-id` and
construct the status/result route on the **public** host
(`https://api.fabric.microsoft.com/v1/operations/{id}`), never forward
credentials to the cluster host in `Location`. Poll with `Retry-After`
until `status` is `Succeeded`, then `GET .../operations/{id}/result` for the
created `Plan` object. Confirm the new item's `id` from that result (or from
the `201` body) before reporting success -- an acknowledgement is not completion.

After a transient failure mid-create, re-list the workspace's Plans before
considering any resubmit; never send a second create blindly.

**Readback:** `GET /v1/workspaces/{workspaceId}/plans/{planId}` and report `id`,
`displayName`, `description` and `workspaceId` from the response.

---

## Rename or re-describe a Plan

Change an existing Plan's `displayName` and/or `description` with the
[Update Plan](https://learn.microsoft.com/en-us/rest/api/fabric/plan/items/update-plan)
operation. This is a **PATCH** on the item endpoint, is **always synchronous**
(`200 OK`, no LRO), and only touches these two fields -- it does not alter
sheets, visuals or the saved definition.

```bash
az rest --method PATCH \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/plans/${PLAN_ID}" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "x-ms-fabric-skill=plan-cli" \
  --body '{"displayName":"Budget 2027 v2","description":"Revised FY27 planning cycle"}'
```

Send only the fields you intend to change. Resolve `${PLAN_ID}` by listing the
workspace's Plans and filtering on `displayName` -- never hardcode it. Confirm
the updated fields from the response before reporting success.

---

## Delete a Plan

Remove a Plan with the
[Delete Plan](https://learn.microsoft.com/en-us/rest/api/fabric/plan/items/delete-plan)
operation. It is a plain **DELETE** with **no query parameters** -- Microsoft Learn
documents no `hardDelete` flag and no recovery path for a Plan, unlike some other
item types. Treat every delete as **permanent**.

```bash
az rest --method DELETE \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/plans/${PLAN_ID}" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "x-ms-fabric-skill=plan-cli"
```

Resolve `${PLAN_ID}` by name first and echo back the resolved `displayName` + `id`.
When the request already named the item and the delete explicitly, that IS the
confirmation -- proceed; otherwise ask the user to confirm before issuing the
DELETE. Never delete on a partial name match, more than one match, or a
bulk/wildcard request ("clean up my workspace") without asking which item(s).

A `200` response is not itself proof of completion -- confirm with a readback:
`GET` on the deleted id should now fail (see
[Errors and troubleshooting](#errors-and-troubleshooting)), or the item should
no longer appear in a fresh List Plans.

**The display name is held for a few minutes after delete.** A live trial
against the public API returned `409 ItemDisplayNameNotAvailableYet` ("...is
not available yet and is expected to become available in the upcoming
minutes") when immediately recreating a Plan under the name just deleted. If
the user wants to reuse the same name right away, say so rather than retrying
in a loop -- it is a documented-by-observation wait, not a failure to fix.

---

## Errors and troubleshooting

| Condition | Action |
|---|---|
| `401` | Wrong token audience; re-authenticate against `https://api.fabric.microsoft.com` (see COMMON-CORE authentication guidance) |
| `403` | Report the missing Contributor role or missing read/write permission on the Plan; do not switch identity or retry |
| `404` on Get/Update/Delete | The service may return this as `ItemNotFound` or `EntityNotFound` depending on the call; treat any 404 on a resolved id as "not found" and re-resolve the workspace/Plan rather than matching one literal error string |
| `409 ItemDisplayNameAlreadyInUse` (create) | Stop and report the conflict. Do not auto-rename, append a suffix, or reuse the existing item without being asked |
| `409 ItemDisplayNameNotAvailableYet` (create, soon after a delete) | The name is held for a few minutes after deleting a Plan with that name. `isRetriable: true` -- say so and offer to wait or use a different name; do not spin-retry |
| `WorkspaceItemsLimitExceeded` (create) | Report the workspace item limit; do not retry |
| `InvalidItemType` / capacity error (create) | Report that the workspace needs a supported Fabric capacity |
| `CorruptedPayload` (create) | Only possible if a definition was supplied; this mode never sends one, so treat this as an unexpected service error and report it verbatim |
| `429` | Wait for `Retry-After`, then retry the **same** request once |
| Plan protected by an encrypted sensitivity label | Report that removing/working around the label needs separate usage rights (see `consumption` mode); authoring does not bypass this |

---

## Must / Prefer / Avoid

### Must

- **Confirm destructive actions before executing** -- Delete has no documented
  recovery for a Plan. Always echo the resolved `displayName` + `id`; a request
  that already names the target item AND the destructive action IS the
  confirmation, so proceed with the single write after echoing. Ask for a
  separate confirmation only when the target or intent is ambiguous.
- **Always pass `--resource https://api.fabric.microsoft.com`** and the
  `x-ms-fabric-skill: plan-cli` header on every call, including LRO polls.
- **Always resolve workspace and Plan ids by listing and filtering** -- never
  hardcode or guess a GUID.
- **Preflight create against the exact display name** -- list first; stop and
  report `ItemDisplayNameAlreadyInUse`-style conflicts rather than resubmitting
  under a different name.
- **Handle LRO on create** -- a `202` may carry a `Location` on a different
  host than the one you called; prefer `x-ms-operation-id` and poll the public
  host. Capture the result before reporting success.
- **Readback after every write** -- GET the item (or confirm it is gone, for
  delete) before telling the user the change landed.

### Prefer

- Resolving the Plan id once per request and reusing it across a rename-then-readback
  or delete-then-readback sequence, instead of re-listing.
- Sending only the changed field(s) in a rename PATCH.
- Reporting the resolved `displayName` + `id` in the same message as the result,
  for auditability.

### Avoid

- Do NOT send a `definition` or any sheet/visual/writeback payload from this
  mode -- that is out of scope for the current authoring surface.
- Do NOT append `?updateMetadata=true` or any other undocumented query
  parameter to a Plan item route.
- Do NOT auto-rename or reuse an existing item on a display-name conflict.
- Do NOT delete on a partial name match, more than one match, or a bulk/wildcard
  request without asking which item(s) first.
- Do NOT spin-retry a `409 ItemDisplayNameNotAvailableYet` in a tight loop --
  it clears after a few minutes, not immediately.
- Do NOT use this mode to save a narrative, visual data, sheet or definition
  change -- that remains unsupported; see `consumption` mode's refusal wording.

---

## Examples

### Example 1 — Create an empty Plan

**Prompt:** "Create a Plan called `Budget 2027` in my `Finance` workspace."

**Flow:**
1. Resolve the workspace name -> id via `GET /v1/workspaces` and filtering.
2. List the workspace's Plans; if `Budget 2027` already exists, report the
   conflict and stop.
3. `POST /v1/workspaces/${WORKSPACE_ID}/plans` with `{"displayName":"Budget 2027"}`.
4. If `202 Accepted`, poll on the public host until `Succeeded`, then fetch the
   result. Report the new item's `id`.

### Example 2 — Rename a Plan and change its description

**Prompt:** "Rename the `Budget 2027` Plan to `Budget 2027 v2` and update its
description to `Revised FY27 planning cycle`."

**Flow:**
1. Resolve the workspace id, then the Plan id by filtering on
   `displayName=='Budget 2027'`. If none matches, report not found and stop.
2. `PATCH /v1/workspaces/${WORKSPACE_ID}/plans/${PLAN_ID}` with the new
   `displayName` and `description`.
3. Confirm both fields in the response.

### Example 3 — Delete a Plan

**Prompt:** "Delete the `Budget 2026` Plan from `Finance`."

**Flow:**
1. Resolve the workspace id and the Plan id by filtering on
   `displayName=='Budget 2026'`. If none matches, report not found and stop.
2. Echo the resolved `displayName` + `id`. The prompt already named the item
   and the delete, so that instruction IS the confirmation -- proceed.
3. `DELETE /v1/workspaces/${WORKSPACE_ID}/plans/${PLAN_ID}`.
4. Report success (HTTP `200`), and that there is no documented recovery.

### Example 4 — Name conflict on create

**Prompt:** "Create a Plan called `Budget 2027` in `Finance`." (one already
exists with that name)

**Flow:**
1. Resolve the workspace id and list its Plans.
2. Find the existing `Budget 2027`. Report the conflict with its `id` and stop
   -- do not create a second item under a modified name and do not delete or
   reuse the existing one without being asked.

### Example 5 — Ambiguous delete

**Prompt:** "Clean up the old plans in my workspace."

**Flow:**
1. This names no specific item. Ask which Plan(s) to delete rather than
   listing and deleting anything. Issue no `DELETE` call.
2. Reply with one direct question, for example: "Which Plan(s) do you want me
   to delete? I won't delete anything until you name them."

---

## Agent Integration Notes

- This mode performs **writes**: Create, Update (rename/re-describe) and Delete
  of the Plan item itself.
- It never writes sheets, visuals, the saved definition, or narrative/visual
  data -- for those, `consumption` mode's read-only and narrative-refusal
  guidance still applies.
- For cross-workload orchestration, delegate to the **FabricDataEngineer** agent.
