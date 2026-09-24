# Parsing Fabric URLs to extract IDs
Use the intake-parsing sections only when the user chooses **Provide a Lakehouse URL**. Workspace/Lakehouse names and Fabric page context are separate valid context paths owned by `SKILL.md`; do not redirect those paths here or require a URL.

Task page URL construction applies after every task starts, regardless of how its workspace and Lakehouse were selected. Read its reference directly from `SKILL.md`.
## Ask for the Lakehouse URL
Prompt the user with:
> Open Fabric in your browser, navigate to the Lakehouse where you want the Project Osmos run to be stored, copy the full URL from the address bar, and paste it here.
Run the URL parser example linked directly from `SKILL.md`. When both IDs are valid and the host is supported, use the parsed context directly. Do not add a second confirmation step for values derived from the URL the user just supplied.
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

If neither path pattern matches, treat the URL as malformed and ask the user to repaste it or choose the workspace/Lakehouse names path.
## Supported URL hosts
Accept only HTTPS URLs for the public Fabric browser hosts below, with no
credentials and either the default port or port 443. Validate this before
authentication or task creation so the later task-link launch uses the same
portal policy. Ask for corrected context when validation fails.

| Host | Notes |
|---|---|
| `app.fabric.microsoft.com` | Fabric portal host. |
| `app.powerbi.com` | Power BI portal host. |

If the host is not supported, ask the user to repaste a Lakehouse URL from the public Fabric portal or choose the workspace/Lakehouse names path.
## Validated context

IDs are always UUIDs. A supported host plus valid workspace and Lakehouse UUIDs is sufficient to continue. If parsing or validation fails, let the user repaste the URL or choose the workspace/Lakehouse names path.

Use the inline parser example in the agent's intake step; no separate script is required. An unsupported host or invalid path is rejected. A valid workspace-only path returns `lakehouse_id: None` to the context choices in `SKILL.md`; do not proceed to auth or task creation until a Lakehouse is selected.
