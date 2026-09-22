---
name: fabric-map-cli
description: "Creates, configures, deletes, lists, and explains first-class Microsoft Fabric Map items and map.json definitions. Clarifies ambiguous map requests before construction. Not Azure Maps applications/APIs or Power BI map visuals."
---

> **Telemetry -- MANDATORY.** Every `api.fabric.microsoft.com` request,
> including pagination, LRO polls, results, and retries, must carry
> `x-ms-fabric-skill: fabric-map-cli`.

# Fabric Map -- CLI Skill

This is a mode dispatcher. Procedures belong in the mode references; source
configuration belongs in the source adapters.

## Product boundary

Fabric Map is a workspace item of type `Map`. Azure Maps is an application/API
service; a Power BI map visual belongs to a report, not a Fabric Map item.

If neither the request nor prior user context identifies the experience, use
the host's question tool to offer **Fabric Map, Power BI map visual, Azure Maps
application/API, or another map experience**, without a default. Wait for the
answer before loading mode references, selecting sources, discovering
resources, generating definitions, or constructing anything. An unanswered
question is not permission to assume Fabric. Do not re-ask when the user has
already identified Fabric Map.
Ask only about the experience at this gate; workspace, naming, and data-source
questions belong after that choice.

| Selected experience | Next action |
|---|---|
| Fabric Map | Continue to mode selection below. |
| Power BI map visual | Hand off to the Power BI report workflow and exit this skill. |
| Azure Maps application/API | Hand off to the Azure Maps application/API workflow and exit this skill. |
| Another experience | Ask which experience, then route to its owning workflow and exit this skill. |

**Only a confirmed Fabric Map may proceed below.** A non-Fabric selection ends
this skill: do not load its mode/source references, issue Map commands, or
generate a definition. Load the available owning workflow before doing that
product's work. If none is available, explain the scope limitation and stop;
do not implement the other product or collect its configuration in this skill.
Announcing a handoff without changing workflows is not a handoff.

## Mode selection

| Mode | Intent | Read first |
|---|---|---|
| `authoring` | Create, configure, restyle, rename, change description, update definition, or delete | [references/authoring.md](references/authoring.md) |
| `consumption` | List, inspect, explain, compare, or discuss capabilities without changes | [references/consumption.md](references/consumption.md) |

Read the selected reference end to end before acting. Resolve links relative
to the file containing them, not the working directory. If a reference is
missing, report its resolved path and stop that workflow.

Consumption permits discovery and get-definition, never mutation. An explicit
no-change instruction takes precedence over authoring verbs. A read-modify-write
request is authoring, including its prerequisite reads. Announce a mode switch
and load the new reference when the user's intent changes.

## Source adapters

Load only adapters relevant to the requested sources or capability question.
Blank creation, metadata, basemap edits, and deletion require no source setup.
Capability summaries are documentation reads, not permission to discover or
configure a source.

For blank creation, all three capability summaries below are required reading
before the final response. Follow the authoring reference's **Required blank-Map
completion response**; metadata and "data can be added later" alone are
incomplete.

| Source | Reference |
|---|---|
| Lakehouse / OneLake | [references/authoring/lakehouse.md](references/authoring/lakehouse.md) |
| Eventhouse / KQL Database | [references/authoring/eventhouse.md](references/authoring/eventhouse.md) |
| External Fabric Connections | [references/authoring/connections.md](references/authoring/connections.md) |

## Shared rules

- Ask for missing workspace, Map identity/name, or requested values; never
  fabricate them. Resolve names with paginated exact-match lookups; verify IDs.
- Use public type-specific Map REST endpoints. Default new definitions to
  schema `2.0.0`; preserve the schema and unrelated content on edits.
- Keep source-data and connection administration separate from Map mutations.
- A local definition is not deployment. Complete the terminal write and its
  readback before claiming persistence; report rendering as unverified unless
  independently observed.
- Preserve unknown fields, IDs, and definition parts. Do not replace a Map
  from a partial model or silently discard unsupported content.
- Treat API errors, failed operations, and readback mismatches as failures,
  not successful completion.
