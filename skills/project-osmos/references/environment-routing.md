# Environment routing

Read this reference after the host-routing gate in `SKILL.md` and before workspace/Lakehouse name discovery, metadata lookup, token acquisition, or any other Fabric API call.

Project Osmos public runs target production Fabric. Workspace and Lakehouse IDs may come from Fabric page context, Microsoft Fabric Skills discovery, or a validated Lakehouse browser URL.

## Routing table

| Context | Family | Use when | Required extras |
| --- | --- | --- | --- |
| Local agent | Production-shape | GitHub Copilot CLI or another local agent | Azure CLI access to the tenant, workspace/lakehouse permissions |
| Copilot in Microsoft Fabric | Unavailable | Trusted portal context identifies Fabric Copilot | Return the coming-soon/local-agent guidance from `SKILL.md`; make no helper or API call |


## Rules

- Do not ask for context, workspace ID, or lakehouse ID as separate startup questions.
- For public production runs, resolve supplied workspace and Lakehouse names with Microsoft Fabric Skills; a browser URL is optional.
- Never route a Fabric portal request into the production MWC flow.
