# Plan Consumption

## Contents

- [Supplied definition workflow](#supplied-definition-workflow)
- [Public definition workflow](#public-definition-workflow)
- [Definition boundaries](#definition-boundaries)
- [Narrative boundaries](#narrative-boundaries)
- [Troubleshooting](#troubleshooting)

Saved definitions and narrative values are different evidence classes.
Use the entry point's Read Plan Definitions or Narrative Summaries workflow;
read their directly indexed references rather than inventing an alternate path.

| Request | Evidence | Permitted access |
|---|---|---|
| Inspect a supplied definition | Saved configuration in the exact supplied file | Local read and strict decoding |
| Inspect a saved Plan | Completed public Get Definition result | Fabric authentication and validated same-host LRO reads |
| Summarize supplied Plan data | User-supplied values and metadata | Local interpretation; no new data request |
| Summarize current visual data not supplied | Completed authorized read results | Optional available registered read capabilities within their actual contracts |

## Supplied definition workflow

Read the exact supplied definition path without authentication or discovery.
Resolve relative paths against the current working directory. If the shell
requires a workspace prefix, use only `cd` with the confirmed absolute workspace
path as a literal, followed by the unchanged read command; never use command
substitution to construct that path. A failed read
stops inspection with the missing path named; it does not authorize a listing,
search, existence probe or conditional fallback.
Use a user-specified permitted decoder unchanged, without output truncation,
redirections or extra extraction commands. A partial display is not validation
of the complete envelope. Reuse successfully decoded parts on unchanged
follow-up questions rather than reading them again.

Decode every supplied part with the documented offline helper or a permitted
local decoder. Validate the complete envelope before reporting saved sheets,
visuals, sources or properties. Return the requested report only: a JSON-only
report has no code fences, progress prose or endpoint notes, including on
follow-up turns.

## Public definition workflow

1. Resolve the exact workspace and Plan through public Fabric item APIs and
   exact filtering, following the shared guidance indexed in `SKILL.md`.
2. Confirm the workspace and Plan IDs from the supplied URL. Any Fabric portal
   link for a Plan uses the public API origin `https://api.fabric.microsoft.com`
   (`FABRIC_API_BASE` in `COMMON-CLI.md`). Do not ask for a separate origin and
   do not derive a host from the portal name.
3. Acquire a standard Fabric-audience token following `COMMON-CLI.md`.
   Get Definition requires Plan read/write permissions and `Item.ReadWrite.All`;
   the inspection itself remains read-only.
4. Call `POST {PUBLIC_BASE}/v1/workspaces/{workspaceId}/plans/{planId}/getDefinition`
   with `x-ms-fabric-skill: plan-cli` and an explicit empty JSON body (`{}`).
   Do not send a bodyless POST without length framing.
5. Accept a complete 200 envelope or follow the shared LRO guidance for 202,
   using the initiating public host. Prefer `x-ms-operation-id`
   to construct status/result routes on the initiating public host. A
   cluster-host `Location` is not a blocker when a valid matching operation ID
   exists; never forward credentials to that host. Honor `Retry-After` and
   validate operation identity throughout.
6. Follow HTTP JSON handling, indexed in `SKILL.md`, to decode the HTTP response before
   decoding each `InlineBase64` part as strict
   UTF-8 JSON. HTTP gzip and part base64 are separate encodings; do not
   decompress an already decoded body again. Reject duplicate paths,
   unsupported payload types, invalid base64/JSON or missing `definition.json`.
7. Resolve saved sheet and visual identity from `definition.json` and exact part
   paths. Report missing parts and export gaps without runtime discovery.

For offline decoding and validation, run the bundled helper from the skill
directory with Python 3.9 or later:

```bash
python3 scripts/plan_definition.py <envelope.json>
```

This reads the supplied envelope and prints a normalized summary without
authenticating, querying values or changing the Plan.

## Definition boundaries

The root and matching part paths establish saved sheet, visual and source
identities. Preserve exact identities and report export gaps. A saved definition
does not contain measured rows, prove refresh status or reproduce unsaved editor
state. Schema URLs describe formats, not current Plan contents.

A missing or invalid part blocks inspection of that part; do not repair it,
search for a replacement or query runtime/private APIs to fill the gap.
An acknowledgement is not a completed definition. Use the validated initiating
host for status and result retrieval without forwarding credentials to another
host.

## Narrative boundaries

Supplied data is sufficient for narration; an open Plan and tools are optional.
Do not authenticate, fetch again or imply live retrieval when the user asks to
summarize supplied values. Preserve its coverage, formats and attribution.

When current visual data is requested but absent, use Data Fetcher's registered
read procedure if available. Otherwise ask for the data or explain the missing
capability. Do not use saved definitions, private proxies, runtime token
exchange, REST, SQL or independent semantic-model queries as a fallback.

Never change filters, selection, content or persisted state. Report missing,
empty, partial, failed and cancelled evidence distinctly. Summaries explain
verified values; they do not authorize a write or a new source of data.

## Troubleshooting

| Condition | Action |
|---|---|
| Plan not found in the requested environment | Reconfirm its URL, identity and approved host; do not switch silently |
| 202 has a valid operation ID and absent or different-host Location | Construct the same-host operation route; reject conflicting IDs |
| 202 has neither a valid ID nor a safe same-host status Location | Stop and report the incomplete LRO contract |
| Redirect, malformed URL or changed operation identity | Stop without forwarding credentials or replaying the request |
| Definition part is malformed or missing | Report the exact part/path failure; do not fall back to runtime inventory |
| Current narrative values are absent | Use a suitable registered read if available; otherwise request data or report the missing capability |
| Supplied rows only | Interpret locally without login, Plan IDs or network |
| 403 or missing permission | Report that Get Definition needs Plan read/write permission and `Item.ReadWrite.All`; do not retry with another identity |
| 429 throttling | Wait for `Retry-After`, then retry the same request once the interval passes |
| Plan protected by an encrypted sensitivity label | Report that the definition cannot be read without usage rights to remove the label |

## Microsoft Learn

- [Get Plan Definition](https://learn.microsoft.com/en-us/rest/api/fabric/plan/items/get-plan-definition)
- [Plan definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/plan-definition)
- [Long running operations](https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation)
