# Environment routing

Read this before discovery or authentication. Only trusted, host-provided
context identifies the agent's host; a pasted Fabric URL does not.

## Routing table

| Agent host | Target context | Action |
| --- | --- | --- |
| Copilot in Microsoft Fabric | Trusted host context, not user-supplied text | Unsupported. Return the coming-soon/local-agent response from `SKILL.md` and stop; make no helper or API call. |
| Local agent | Lakehouse URL pasted by the user | Validate and use the bundled resolver for that target. The URL does not make the local agent Fabric Copilot. |
| Local agent | Saved task routing | Validate and retain the selected target, exact `/tasks` or `/aichat` route, IDs and recovery state. |
| Local agent | Production workspace/Lakehouse names, without a URL or saved route | Resolve with Microsoft Fabric Skills; no URL is required. For other missing target context, request a Lakehouse URL. |

## Rules

- Retain the target for every call, refresh, upload and link; sign-in selects
  identity, not the target.
- The resolver derives the API origin; services supply capacity/workload routing
  and enforce access/availability.
- On errors, preserve IDs/state. Never substitute production, reuse IDs there,
  guess hosts, install packages or recreate tasks. Reject an untrusted origin
  before calls; you may ask for a valid Lakehouse URL for the intended environment.
