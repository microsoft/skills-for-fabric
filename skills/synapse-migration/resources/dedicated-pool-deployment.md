# Dedicated Pool Deployment to Fabric

Create or resolve the target Lakehouse through Fabric REST, execute schema-only artifacts through Lakehouse-bound Livy, and publish generated stored-procedure notebooks to the Fabric workspace without executing them.

## Generated Notebook Publication

Create or update notebooks generated from discovered stored procedures, with one notebook per procedure and an explicit default Lakehouse binding. Publish them as migration outputs without invoking them or using them to orchestrate migration.

## API Flow

1. Acquire a Fabric token for `https://api.fabric.microsoft.com`.
2. Resolve the workspace by display name.
3. List Lakehouses and resolve the target by display name.
4. If absent and approved, create it with `POST /v1/workspaces/{workspaceId}/lakehouses`.
5. Poll any long-running operation to completion.
6. Create a Livy session bound to the target Lakehouse.
7. Submit schema-only artifacts in manifest dependency order. Do not submit row inserts, CTAS materialization, DataFrame writes, or other data-loading statements.
8. Compile each generated `.ipynb`: validate JSON/nbformat, Python cells, parameter declarations, and Spark SQL parser compatibility.
9. Create or update one Fabric Notebook item per stored procedure using an `ipynb` definition and poll each operation to `Succeeded`.
10. Persist Notebook item IDs and deployment statuses in the manifest.
11. Close the Livy session.

Use the Fabric Spark consumption/authoring core documents for the current Livy endpoint and payload shape rather than duplicating version-sensitive API details here.

## Deployment Order

1. Schemas and empty Delta tables
2. Non-materializing view definitions that are supported by the target
3. Converted procedural logic as published Notebook items

Converted procedural logic is published as Notebook items. Do not invoke generated notebooks or transformations as part of this skill.

## Idempotency and Recovery

- Check manifest status before submitting an artifact.
- Use `IF NOT EXISTS` and manifest checkpoints where appropriate.
- Never replace an existing target schema/code artifact without explicit approval.
- On statement failure, capture state, output, and the affected object; stop dependent objects.
- Recreate an expired Livy session and resume from the first incomplete manifest item.
- Do not log access tokens, connection strings, or secrets.

## Completion Gate

Deployment completes only when all required manifest items have terminal success states. Failed or review-required items must be reported explicitly and block cutover.
Deployment success means schema/code artifact readiness only; it does not establish data parity or production cutover readiness.
