# Project Osmos use cases

Use this reference when a user asks for concrete examples of Project Osmos work. Each scenario is one complete outcome for one Osmos task; do not split it into separate tasks or phases.

## Summary

| Scenario | What Project Osmos coordinates |
| --- | --- |
| Rebuild tables from shortcut-backed data | Coordinates multiple shortcut-backed source paths and downstream table rebuilds as one outcome. |
| Build a medallion architecture | Carries a dependent, multi-layer Spark implementation through notebooks and Delta tables. |
| Create a repeatable incremental transformation | Combines inspection, data quality, joins, aggregation, rerun behavior, and reusable artifacts. |
| Generate a realistic synthetic dataset | Creates related data at scale while preserving relationships, distributions, tables, and reusable generation code. |

## Rebuild tables from shortcut-backed data

Use Project Osmos to read the current shortcut-backed files and coordinate the downstream Lakehouse rebuilds that depend on them.

```text
Read the current files from `Files/orders_shortcut`,
`Files/customers_shortcut`, and `Files/products_shortcut`. Rebuild the `Orders`,
`Customers`, and `Products` Lakehouse tables from those files, run independent
table rebuilds in parallel, and validate row counts and expected schemas for
each table.
```

This is a strong fit because the outcome spans multiple shortcut-backed source paths and dependent tables and may require a long-running sequence of rebuild operations.

## Build a medallion architecture

Use Project Osmos to carry a multi-layer data engineering outcome from raw data through tested, reusable artifacts.

```text
Build a medallion pipeline for Orders and Customers stored in OneLake. Preserve
the raw source in Bronze Delta tables, clean and standardize the records in
Silver, and create Gold tables for monthly revenue by customer segment. Create
and test the Fabric notebooks for each layer, save them in the workspace, and
verify row counts and expected schemas at each layer.
```

This is a strong fit because the layers depend on one another and require data discovery, Spark implementation, repeated execution, table creation, and multiple notebook artifacts.

## Create a repeatable incremental transformation

Use Project Osmos when an ingestion task combines data quality rules, joins, aggregations, and a durable output.

```text
Load the incremental Orders data from OneLake, remove rows with null
customer_id, join the Customers dimension, calculate monthly order value by
customer segment, and write the result to a Delta table named
monthly_segment_revenue. Save and test the notebook so the workflow can be run
again without duplicating existing results. Validate source and output row
counts and check for negative revenue values.
```

This is a strong fit because the task combines source inspection, transformation logic, rerun behavior, Spark execution, and a reusable notebook and table.

## Generate a realistic synthetic dataset

Use Project Osmos when test, demonstration, or development work needs a substantial dataset with consistent relationships and reproducible generation logic.

```text
Generate a synthetic retail dataset with 100,000 customers, 10,000 products,
and 5 million orders spanning two years. Preserve the relationships between
customers, products, and orders; include realistic seasonality, product
categories, order values, and returns; and write the results to `Customers`,
`Products`, `Orders`, and `Returns` Delta tables. Create and test a reusable
Fabric notebook, then validate table counts, key relationships, and value
distributions.
```

This is a strong fit because the task combines data modeling, large-scale Spark generation, coordinated table creation, reproducibility, and statistical validation.
