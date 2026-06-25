# Infrastructure & Orchestration — Skill Resource

Essential patterns for workspace provisioning, lakehouse configuration, and pipeline orchestration in Microsoft Fabric.
## Recommended patterns

### Must

1. **Always use version control** for infrastructure definitions and deployment scripts — track changes, enable rollback
2. **Implement environment isolation** — separate dev/test/prod workspaces with distinct configurations
3. **Use parameterized configurations** — avoid hardcoding workspace IDs, names, or environment-specific values
4. **Validate before deployment** — check JSON payloads, test API calls with dry-run where possible
5. **Implement proper RBAC** — assign minimum required permissions to users and service principals

### Prefer

1. **Declarative infrastructure** over imperative scripts — define desired state, let automation converge
2. **Automated CI/CD** over manual deployments — reduce human error, increase consistency
3. **Idempotent operations** — scripts should be safe to run multiple times without side effects

### Avoid

1. **Don't hardcode secrets** in scripts or configurations — use Azure Key Vault, environment variables
2. **Don't skip testing** infrastructure changes — validate in dev before promoting to prod
3. **Don't ignore capacity planning** — understand SKU requirements, concurrent user limits, data volume
4. **Don't create orphaned resources** — track workspace-lakehouse-notebook relationships, clean up on teardown

---

## Workspace Provisioning Principles

### Environment Isolation Strategy
Guide LLM to create workspaces following:
- **Naming convention**: `{project}-{environment}` (e.g., `sales-analytics-dev`, `sales-analytics-prod`)
- **Separate capacity**: Dev uses lower-tier capacity (F2/F4), prod uses dedicated higher-tier (F64+)
- **Access control**: Limit prod access to service principals and specific admins, dev is broader
- **Data segregation**: Dev uses synthetic/sample data, prod uses real data with compliance controls

### Workspace Configuration
Prompt LLM to configure:
1. **Display name**: Human-readable, follows naming convention
2. **Description**: Document purpose, owning team, environment type
3. **Capacity assignment**: Assign to appropriate Fabric capacity for the environment
4. **Default lakehouse**: Create primary lakehouse during workspace setup for consistency

### RBAC Patterns
Tell LLM to assign roles appropriately:
- **Admin**: Full control, can manage access — limit to 2-3 people
- **Member**: Can create and edit items — developers, data engineers
- **Contributor**: Can edit items but not create new — analysts, data scientists
- **Viewer**: Read-only access to reports — business users

### API Approach
Guide LLM to use Fabric REST API:
- **Create workspace**: POST `/v1/workspaces` with `displayName` and optional `description`
- **Assign capacity**: Use capacity assignment endpoint if not using default
- **List workspaces**: GET `/v1/workspaces` to discover existing workspaces

---

## Lakehouse Configuration Guidance

### When to Create Separate Lakehouses
Guide LLM based on use case:

**Single lakehouse** when:
- Small project with <10 tables, single data pipeline
- All data has same security requirements
- Team is small, no cross-team collaboration
- **Medallion architecture with schema-enabled lakehouse** — create `bronze`, `silver`, `gold` schemas within one lakehouse; MLVs with incremental refresh make cross-schema transformations efficient

**Multiple lakehouses** when:
- Large project with distinct data domains (sales, marketing, finance)
- Different security/compliance requirements per domain
- Different retention policies per data type

**Avoid creating separate lakehouses** for:
- Medallion layers (bronze/silver/gold) when using schema-enabled lakehouses — use schemas within one lakehouse instead
- Derived/transformed tables within the same layer/schema — use notebooks, MLVs, or standard tables within the existing lakehouse/schema, not separate lakehouses

### Lakehouse Naming Conventions
Prompt LLM to follow pattern:
- **Medallion architecture with schema-enabled lakehouse**: Single lakehouse named `{project}_lakehouse`, with schemas `bronze`, `silver`, `gold` inside
- **Medallion architecture without schema-enabled lakehouse** (legacy): `{project}_bronze`, `{project}_silver`, `{project}_gold` as separate lakehouses
- **Domain separation**: `sales_lakehouse`, `marketing_lakehouse`, `shared_dimensions`
- **Environment suffix**: Include env if workspace spans environments (rare)

### Configuration Considerations
Tell LLM to think about:
- **OneLake path**: Lakehouse automatically gets `Files/` and `Tables/` folders
- **Shortcuts**: Create shortcuts to external ADLS Gen2 or other OneLake lakehouses for federated queries
- **Default lakehouse**: Set one as default for notebooks to simplify path references
- **SQL endpoint**: Every lakehouse automatically gets SQL Analytics Endpoint for T-SQL queries

### Schema Management
Guide LLM for table organization:
- **Bronze schema**: Raw data, minimal transformation, original data types
- **Silver schema**: Cleaned, validated, conformed types, deduplication
- **Gold schema**: Business-logic enriched, aggregated, optimized for analytics
- **Naming**: Use lowercase with underscores: `customer_transactions`, not `CustomerTransactions`

---

## Pipeline Design Patterns

### Orchestration vs Transformation Logic
Critical principle for LLM to understand:

**Pipelines (orchestration)**: Define **when** and **what order** to run tasks
- Schedule/trigger configuration
- Activity dependencies (Task A → Task B → Task C)
- Parameter flow between activities
- Retry and error handling policies
- Notifications on success/failure

**Notebooks (transformation)**: Contain **what** to transform and **how**
- Read data from source
- Apply business logic transformations
- Write to destination
- No orchestration concerns

Guide LLM to separate these: Don't put scheduling logic in notebooks; don't put transformation logic in pipelines.

### Activity Types and When to Use

**Notebook Activity**:
- Use for: Data ingestion, transformation, ML training, custom PySpark logic
- Parameterization: Pass date ranges, paths, table names from pipeline
- Output: Can output values for downstream activities to consume

**Copy Activity**:
- Use for: Simple data movement without transformation (ADLS → Lakehouse, Lakehouse → Azure SQL)
- Efficient for large-volume copies with schema mapping
- Built-in retry and throttling handling

**ForEach Activity**:
- Use for: Batch processing multiple files, tables, or partitions
- Iterates over array, executes nested activity for each item
- Can run sequentially or in parallel (set batchCount)

**If/Switch Conditions**:
- Use for: Conditional logic (e.g., different processing for weekday vs weekend)
- Evaluate expressions based on pipeline parameters or activity outputs

**Wait/Webhook**:
- Use for: External system coordination, delays between activities
- Webhook calls external REST endpoint, waits for callback before proceeding

### Parameter Flow Pattern
Guide LLM to design parameter flow:
1. **Pipeline parameters**: Define at pipeline level (e.g., `ProcessingDate`, `Environment`)
2. **Pass to activities**: Map pipeline params to notebook params in activity configuration
3. **Default values**: Notebooks should have sensible defaults if pipeline doesn't override
4. **Expressions**: Use `@formatDateTime(utcnow(), 'yyyy-MM-dd')` for dynamic values
5. **Output consumption**: Capture notebook outputs, use in downstream activities

### Error Handling Strategy
Prompt LLM to configure:
- **Activity retry**: Set retry count (3) and interval (30s) for transient failures
- **Timeout**: Set max execution time to prevent runaway processes
- **On failure paths**: Use activity dependencies to execute cleanup/notification on error
- **Dead letter**: Write failed records to error table for investigation
- **Alerting**: Configure pipeline failure notifications to Teams/email

---

## CI/CD Integration Strategy

### Infrastructure as Code Benefits
Explain to LLM why IaC matters:
- **Reproducibility**: Deploy same config across dev/test/prod consistently
- **Version control**: Track changes, review PRs, rollback bad changes
- **Automation**: Reduce manual steps, increase deployment frequency
- **Testing**: Validate infrastructure changes before production deployment

### Deployment Patterns

**Pattern 1: API-Driven Deployment**
- Use Fabric REST API to create/update notebooks, lakehouses, pipelines
- Store item definitions in Git repository
- CI/CD pipeline reads definitions, calls API to deploy
- Best for: Notebooks, pipelines, simple infrastructure

**Pattern 2: ARM/Bicep Templates**
- Define Azure resources declaratively (capacity, workspace assignments)
- Use Azure DevOps or GitHub Actions to deploy templates
- Best for: Azure-level resources, capacity management

**Pattern 3: Hybrid Approach**
- ARM templates for Azure resources and capacity
- Fabric REST API for workspace items (notebooks, pipelines, lakehouses)
- Separation of concerns: infrastructure vs data artifacts

### Git Workflow
Guide LLM for branching strategy:
- **Main branch**: Protected, reflects production state
- **Feature branches**: Develop changes in isolation, PR review before merge
- **Environment branches**: Optional dev/test/prod branches for staged deployments
- **Tag releases**: Tag commits with version numbers for rollback reference

### Automated Testing in CI/CD
Prompt LLM to implement:
1. **Lint/validate**: Check JSON syntax, YAML format, notebook structure
2. **Unit tests**: Run local PySpark tests with sample data
3. **Integration tests**: Deploy to dev workspace, execute pipeline, validate output
4. **Smoke tests**: Post-deployment checks (workspace accessible, pipelines runnable)
5. **Rollback capability**: Automated rollback if deployment tests fail

### Deployment Stages
Typical progression LLM should generate:
1. **Dev deployment**: Automatic on every commit to feature branch
2. **Test deployment**: Automatic on merge to main, runs full integration tests
3. **Prod deployment**: Manual approval gate, requires test pass + human review
4. **Monitoring**: Post-deployment validation, alerting on anomalies

### Secrets Management
Tell LLM to handle secrets via:
- **Azure Key Vault**: Store connection strings, SAS tokens, API keys
- **Service principals**: Use for automation authentication, not personal accounts
- **Environment variables**: Pass secrets to pipelines at runtime, never hardcode
- **Audit logging**: Track who accessed secrets, when, for what purpose
