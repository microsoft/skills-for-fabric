# Explain Project Osmos to me

**Content owner:** Project Osmos PM/product content owner

Project Osmos is a long-running data engineering agent for Microsoft Fabric. Give it an outcome that may require multiple data-engineering steps or extended runtime. It can inspect data, write and run Spark, create notebooks and outputs, and keep working as one task when execution requires iteration.

Use Project Osmos for Lakehouse, OneLake, Spark, and notebook work that benefits from an agent carrying an outcome through multiple steps. It can explore data, create and test Fabric notebooks, clean and transform data, and create or update Delta tables and workspace artifacts. Use the other installed Fabric skills for Power BI, Warehouses and T-SQL, Eventhouse and KQL, Eventstreams, Dataflows Gen2, Data Factory pipelines, or workspace and capacity administration.

## Example use cases

Project Osmos supports complex outcomes including dependent table rebuilds, medallion architectures, repeatable transformations, and synthetic data generation.

Ask for more examples to see expanded scenarios and ready-to-adapt prompts.

## Before work starts

1. **Describe the outcome.** Explain the result you need and include any important constraints or context.
2. **Provide Lakehouse context.** Project Osmos uses a Fabric Lakehouse to start Spark in the correct workspace and use that workspace's capacity. The Lakehouse is the default Spark context, not an access boundary, required source, required destination, or scope limit.
3. **Review the task settings.** Project Osmos recommends settings for what it may change, safe write behavior, reruns, schema changes, output format and destination, and reasoning effort. Adjust any setting before explicitly starting the task.

Once started, Project Osmos keeps working as one Fabric task. It may ask for input before continuing and reports whether the task succeeds or fails.

## Why do I need to attach a Lakehouse?

Project Osmos needs a Lakehouse to start Spark in the right Fabric workspace and use that workspace's capacity. The Lakehouse is only the default Spark context. It does not determine what the task can access or where outputs are saved.
