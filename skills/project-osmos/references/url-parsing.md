# Parsing Fabric URLs to extract IDs
Use the intake-parsing sections only when the user chooses **Provide a Lakehouse URL**. Workspace/Lakehouse names and Fabric page context are separate valid context paths owned by `SKILL.md`; do not redirect those paths here or require a URL.

**Untrusted-origin rejection:** explain why the supplied URL cannot be used and
that no authentication, API calls or task changes occurred. Wording is flexible.
You may ask for a valid Lakehouse URL for the user's intended environment.
Do not automatically switch targets, reuse the supplied IDs elsewhere, execute
with invalid context or request a plugin installation. Preserve the original
request and saved state until corrected context is provided.

Check the origin **before** classifying the path; an invalid path never overrides an untrusted-origin stop.

| Origin | Path | Response |
| --- | --- | --- |
| Untrusted | Any, including malformed IDs | Reject the URL before calls. May request a valid URL for the intended environment; do not select a replacement target. |
| Trusted | Malformed or incomplete | Request corrected context using the paths below. |

Task page URL construction applies after every task starts, regardless of how its workspace and Lakehouse were selected. Read its reference directly from `SKILL.md`.
## Ask for the Lakehouse URL
Prompt the user with:
> Open Fabric in your browser, navigate to the Lakehouse where you want the Project Osmos run to be stored, copy the full URL from the address bar, and paste it here.
Run the URL parser example linked directly from `SKILL.md`. The bundled resolver repeats validation using `task_routes.parse_lakehouse_url()`. When both IDs are valid and the portal origin is trusted, use the parsed context directly. Do not add a second confirmation step for values derived from the URL the user just supplied.
## Path patterns
Parse the URL first, then apply these patterns to `urlsplit(...).path` only. Never search the raw URL, query, or fragment for IDs.
```text
UUID = [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}
workspace = ^/groups/(?P<ws>{UUID})(?:/|$)
lakehouse = ^/groups/(?P<ws>{UUID})/lakehouses/(?P<lh>{UUID})(?:/|$)
```
- `ws` → workspace ID
- `lh` → Lakehouse ID when the path is Lakehouse-scoped
- Both GUIDs are 36 characters with the standard `8-4-4-4-12` hyphen layout.
- If the path begins with `/groups/<workspace-id>/lakehouses/` but the Lakehouse segment is not a strict UUID, reject the URL rather than treating it as workspace-only.

### Supported URL shapes
| Shape | Example | Yields |
|---|---|---|
| Lakehouse home | `https://app.fabric.microsoft.com/groups/<ws>/lakehouses/<lh>?experience=power-bi` | workspace + lakehouse |
| Lakehouse explorer with table path | `https://app.fabric.microsoft.com/groups/<ws>/lakehouses/<lh>/tables/Invoice` | workspace + lakehouse |
| SQL endpoint of the same lakehouse | `https://app.fabric.microsoft.com/groups/<ws>/sqlendpoints/<sql>` | workspace only — return to the context choices |
| Notebook | `https://app.fabric.microsoft.com/groups/<ws>/synapsenotebooks/<nb>` | workspace only — return to the context choices |
| Workspace home | `https://app.fabric.microsoft.com/groups/<ws>/list` | workspace only — return to the context choices |

If the Lakehouse pattern matches and the host is supported, proceed. If only the workspace pattern matches, return to the context choices in `SKILL.md` with that workspace as the candidate instead of requiring another URL.

If neither path pattern matches **on a trusted origin**, treat the URL as malformed and ask the user to repaste it or choose the workspace/Lakehouse names path. For an untrusted origin, reject it first and request corrected context without automatically selecting another target.
## Supported URL hosts
Accept only HTTPS URLs for Fabric or Power BI browser hosts, with no
credentials and either the default port or port 443. Validate this before
authentication or task creation so the later task-link launch uses the same
portal policy. A rejected origin must not be used; corrected context may be requested.

| Host | Notes |
|---|---|
| `app.fabric.microsoft.com` | Fabric portal host. |
| `app.powerbi.com` | Power BI portal host. |
| `<target>.fabric.microsoft.com` or `<target>.powerbi.com` | A single DNS label selects the target. The helper derives its matching API origin; service access and availability are verified by the endpoint, not a local environment registry. |

Reject origins outside these portal families before authentication.
Do not reuse IDs from a rejected URL on another target or silently enter production
name discovery. You may request a valid URL for the user's intended environment.
Endpoint access failures retain the selected target and IDs.
Only a request independently established as production may use production
name discovery. Unknown targets are not silently mapped to production.
## Validated context

IDs are always UUIDs. A supported host plus valid workspace and Lakehouse UUIDs is sufficient to continue. For malformed production context, let the user repaste the URL or choose the workspace/Lakehouse names path; an untrusted origin must be rejected before requesting corrected context.

Use the inline parser example in the agent's intake step; no separate script is required. An unsupported host or invalid path is rejected. A valid workspace-only path returns `lakehouse_id: None` to the context choices in `SKILL.md`; do not proceed to auth or task creation until a Lakehouse is selected.

Before replying, recheck the origin classification. A request for corrected context never authorizes using the rejected URL, changing environments or bypassing task confirmation gates.
