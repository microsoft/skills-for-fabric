# TMDL Guidelines

Unified reference for Tabular Model Definition Language (TMDL) - syntax rules, object types, advanced features, and best practices for Power BI semantic model authoring.

---

## TMDL Syntax Rules

- **TMDL uses consistent indentation for nested levels** - use one indentation style consistently across the file; tabs are recommended to align with Power BI tooling. When building TMDL strings in PowerShell, use `` `t `` for tabs; in Bash, use `$'\t'` or literal tabs.
- A TMDL object is declared by specifying the TOM object type followed by its name: `table Customer`, `column ProductId`, `measure 'Total Sales'`
- Objects like partition or measure have default properties that can be assigned after the equals (`=`) sign that specify the PowerQuery expression or DAX expression respectively.
- Names with spaces or special characters (`.`, `=`, `:`, `'`) must be wrapped in **single quotes**: `column 'Order Date'`
- Descriptions use `///` placed **above** the object - do not use the `description` property:
  ```tmdl
  /// Revenue by product category
  measure 'Total Sales' = SUM(Sales[Amount])
  ```
- `//` comments are **not supported** in TMDL. Comments can be within Power Query (M) expressions or DAX expressions code blocks.
- Do **not** add `lineageTag` property when creating new objects - Lineage tags are optional; when authoring new objects you may omit them and the engine will assign GUIDs on first save.
- Multi-line DAX should be enclosed in triple backticks:
  ```tmdl
  measure 'Profit Margin' = ```
          DIVIDE(
              [Total Revenue] - [Total Cost],
              [Total Revenue]
          )
          ```
      formatString: 0.00%
  ```
- Place **measures before columns** in table definitions
- `formatString` is required on every measure
- Always learn from existing examples and patterns in the code (e.g., existing naming conventions)
  
---

## TMDL File Layout

TMDL uses a folder structure where some objects are defined in separate files:

```
definition.pbism                        <- Semantic model connection settings
definition/database.tmdl                <- Database properties (compatibility level)
definition/model.tmdl                   <- Model properties, table/role/culture refs
definition/relationships.tmdl           <- Named/inactive relationships
definition/functions.tmdl               <- DAX functions
definition/tables/<TableName>.tmdl      <- Tables: columns, measures, partitions, hierarchies, calc groups
definition/roles/<RoleName>.tmdl        <- Security roles
definition/cultures/<locale>.tmdl       <- Translations
definition/perspectives/<Name>.tmdl     <- Perspectives
```

### database.tmdl

The database file **must** start with a `database` object declaration (GUID or name), not a bare property:

```tmdl
database 7124f8d8-6199-44fe-b35d-7f7f06b3e1c6
	compatibilityLevel: 1702
	compatibilityMode: powerBI
	language: 1033
```

> **Critical**: Using bare `compatibilityLevel:` without the `database` declaration causes `InvalidLineType: Property!` errors.

### model.tmdl

The model file declares properties and references to all tables, roles, perspectives, and cultures. Use `ref` declarations so the engine discovers the corresponding files:

```tmdl
model Model
	culture: en-US
	defaultPowerBIDataSourceVersion: powerBI_V3	
	sourceQueryCulture: en-US

ref table Sales
ref table Date

ref role RegionalManager

ref perspective 'Internet Sales'

ref cultureInfo en-US
ref cultureInfo fr-FR
```

> **Note**: `defaultPowerBIDataSourceVersion: powerBI_V3` is required for Import-mode models. Without it, the API returns `Import from JSON supported for V3 models only`.

---

## Table Examples by Storage Mode

### Import Table

```tmdl
table Customer

	/// Total number of customers
	measure '# Customers' = COUNTROWS(Customer)
		formatString: #,##0

	column CustomerId
		dataType: int64
		isHidden		
		summarizeBy: none
		sourceColumn: CustomerId

	column 'Customer Name'
		dataType: string
		sourceColumn: CustomerName

	partition Customer = m
		mode: import
		source =
			let
				Source = Sql.Database(#"Server", #"Database"),
				Customer = Source{[Schema="dbo", Item="Customer"]}[Data]
			in
				Customer
```

### Direct Lake Table

```tmdl
expression DL_Lakehouse =
	let
		Source = AzureStorage.DataLake("https://onelake.dfs.fabric.microsoft.com/<WorkspaceId>/<LakehouseId>", [HierarchicalNavigation=true])
	in
		Source

table Sales

	/// Total revenue
	measure 'Total Sales' = ```
			SUMX(
				Sales,
				Sales[Quantity] * Sales[UnitPrice]
			)
			```
		formatString: $ #,##0.00

	column SalesKey
		dataType: int64
		isHidden		
		summarizeBy: none
		sourceColumn: sales_key

	column Quantity
		dataType: int64
		sourceColumn: quantity

	column UnitPrice
		dataType: decimal
		summarizeBy: none
		sourceColumn: unit_price

	partition Sales = entity
		mode: directLake
		source
			entityName: Sales
			schemaName: dbo
			expressionSource: DL_Lakehouse
```

---

## Relationships

Declared in `relationships.tmdl` or inline in table files.

```tmdl
relationship 'Sales to Date'
	fromColumn: Sales.'Order Date'
	toColumn: Date.Date

/// Inactive - use with USERELATIONSHIP() in DAX
relationship 'Sales - Ship Date to Date'
	isActive: false
	fromColumn: Sales.'Ship Date'
	toColumn: Date.Date
```

### Key Rules

- Create relationships **before** measures that depend on them
- `fromColumn:` = many-side (fact); `toColumn:` = one-side (dimension)
- Default: `crossFilteringBehavior: oneDirection`; add `bothDirections` only when needed
- `isActive: false` for role-playing dimensions; use `USERELATIONSHIP()` in DAX
- Prefer integer keys over string keys for performance
- Both sides must have matching `dataType`
- Hide foreign keys on fact tables (`isHidden: true`)
- No composite keys - use a single surrogate integer key
- No surrogate keys on fact tables - use natural keys where possible
  
---

## Hierarchies

Hierarchies are declared **inside** a table definition. Each level maps to an existing column in the same table.

```tmdl
table Geography

	column Continent
		dataType: string
		sourceColumn: Continent

	column Country
		dataType: string
		sourceColumn: Country

	column City
		dataType: string
		sourceColumn: City

	hierarchy 'Geography Hierarchy'

		level Continent
			column: Continent

		level Country
			column: Country

		level City
			column: City
```

### Key Rules

- A table can have multiple hierarchies
- Levels are ordered top-down (coarsest to finest)
- Each `level` must reference a `column:` that exists in the same table
- Level names can differ from column names
- Use `///` descriptions **above** the level for documentation
- Do not create hierarchies with a single level (no drill-down value)

---

## Calculation Groups

A calculation group is a special table with `calculationGroup` and `calculationItem` entries. The table must also have a column (the calculation group column) and a `calculationGroup` partition.

```tmdl
table 'Time Intelligence'

	calculationGroup

		calculationItem Current = SELECTEDMEASURE()

		calculationItem YTD = CALCULATE(SELECTEDMEASURE(), DATESYTD('Date'[Date]))

		calculationItem PY = CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Date'[Date]))

	column 'Time Intelligence'
		dataType: string

	partition 'Partition_Time Intelligence' = calculationGroup
```

### Key Rules

- `calculationGroup` is declared with **no name** - just the keyword indented under the table
- Each `calculationItem <Name> = <DAX>` is indented under `calculationGroup`
- Use `formatStringDefinition` (not `formatString`) for calculation items that override the measure's format
- The `column` name typically matches the table name
- The partition type must be `= calculationGroup` (not `= m` or `= calculated`)

---

## Security Roles

Each role is a separate file in the `roles/` folder. The file declares access level and DAX filter expressions per table.

### File: `roles/RegionalManager.tmdl`

```tmdl
/// Access restricted to East region
role RegionalManager
	modelPermission: read

	tablePermission Sales = [Region] = "East"
```

### Key Rules

- `role <Name>` is the top-level declaration
- `modelPermission:` is required - use `read` (most common) or `readRefresh`
- `tablePermission <TableName> = <DAX filter>` - the DAX filter expression restricts rows
- One `tablePermission` per table; multiple tables can be filtered in the same role
- In `model.tmdl`, add `ref role <Name>` for each role
- When creating new roles, never include the `PBI_Id` annotation
- If possible, analyze the patterns of existing roles first

---

## Translations / Cultures

Each culture is a separate file in the `cultures/` folder.

### File: `cultures/fr-FR.tmdl`

```tmdl
cultureInfo fr-FR
	translations
		model Model
			table Sales
				caption: Ventes
				column Amount
					caption: Montant
```

### Key Rules

- `cultureInfo <locale>` is the top-level declaration (e.g., `fr-FR`, `zh-CN`, `ja-JP`)
- `translations` -> `model Model` -> table/column/measure nesting
- Use `caption:` for display name, `description:` for tooltips
- In `model.tmdl`, add `ref cultureInfo <locale>` for each culture

---

## Perspectives

Each perspective is a separate file in the `perspectives/` folder.

### File: `perspectives/Internet Sales.tmdl`

```tmdl
perspective 'Internet Sales'

	perspectiveTable 'Internet Sales'
		includeAll

	perspectiveTable Customer
		perspectiveColumn 'Marital Status'
		perspectiveColumn Education

	perspectiveTable _Measures
		perspectiveMeasure 'Internet Sales Amount'
```

### Key Rules

- `perspective <Name>` is the top-level declaration
- `perspectiveTable <TableName>` lists each included table
- Use `includeAll` to include every column/measure; otherwise list specific `perspectiveColumn` / `perspectiveMeasure`
- In `model.tmdl`, add `ref perspective <Name>` for each perspective

---

## DAX User-Defined Functions (UDFs)

DAX user-defined functions are DAX-defined reusable calculations declared in `functions.tmdl`.

Example of DAX function in `functions.tmdl`: 

```tmdl
/// Returns double the input value
function DoubleValue = DoubleValue(Value) = Value * 2

/// Year-to-date cumulative total
function YTDTotal = ```
		YTDTotal(Measure) =
		CALCULATE(
		    Measure,
		    DATESYTD('Date'[Date])
		)
		```
```

### Key Rules

- `function <Name> = <Signature> = <DAX>` for single-line; triple backticks for multi-line
- Declared in `definition/functions.tmdl` (top-level file, not inside a table)

---

## Calculated Tables

Tables can be sourced from DAX expressions using a calculated partition:

```tmdl
table _Measures

	measure 'Total Sales' = SUM(Sales[Amount])
		formatString: $#,##0.00

	column Dummy
		isHidden
		sourceColumn: [Dummy]

	partition _Measures = calculated
		mode: import
		source = ROW("Dummy", BLANK())
```

### Key Rules

- Use `partition <Name> = calculated` with `source = <DAX>`
- Calculated partitions use `mode: import`
- Useful for measures-only tables (`ROW("Dummy", BLANK())`) and computed date tables

---

## Date/Calendar Table

- Prefer an existing date table from the source over auto-generated
- Ensure **contiguous date range** with no gaps
- Set `dataCategory: Time` on the date table
- Configure `sortByColumn` for month name columns (sort by month number)
- Disable auto-date tables if a proper calendar table exists
- Create DAX calculated date table only if source table unavailable

---

## Parameters

Use named expressions for connection parameters (Server, Database):

```tmdl
expression Server = "myserver.database.windows.net" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression Database = "MyDatabase" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
```

Reference in partition M expressions via `#"Server"` and `#"Database"`.

---

## Annotations

Annotations store metadata as key-value pairs. They can appear on tables, columns, measures, relationships, roles, and perspectives.

Examples of auto-generated annotations (read-only — do not author) `PBI_FormatHint`, `PBI_ResultType`:

```tmdl
table Sales

	column 'Unit Price'
		dataType: decimal
		sourceColumn: UnitPrice

		annotation SummarizationSetBy = Automatic
		annotation PBI_FormatHint = {"currencyCulture":"en-US"}

	partition Sales = m
		mode: import
		source = ...

	annotation PBI_ResultType = Table
```

### Key Rules

- `annotation <Key> = <Value>` - indented under the object it annotates
- Do **not** add `PBI_*` annotations manually - they are Power BI internal metadata
- Custom annotations can be used for documentation or tooling metadata

---

## Calendar Objects

Calendar objects provide date intelligence metadata on a Date table, declared inside the table after hierarchies.

```tmdl
table Date

	calendar 'Gregorian Calendar'

		calendarColumnGroup = year
			primaryColumn: Year

		calendarColumnGroup = month
			primaryColumn: 'Year Month Number'
			associatedColumn: Month

		calendarColumnGroup = date
			primaryColumn: Date
			associatedColumn: Day
```

### Key Rules

- `calendar '<Name>'` is declared inside the table definition
- `calendarColumnGroup = <granularity>` maps levels (year, quarter, month, week, date, monthOfYear, dayOfWeek)
- `primaryColumn:` = sort/numeric column; `associatedColumn:` = display/text columns
- Calendar objects are optional - they enhance time intelligence auto-detection

---

## TMDL Scripts

TMDL scripts are produced by TMDL view and are normally under the `TMDLScripts` folder of a semantic model.

A TMDL script always includes a command at the top followed by one or more objects with at least one level of indentation.

```tmdl
<TMDL Command name>
  <TMDL object>
  
  <TMDL object>
```
- The semantics of TMDL language are applied to objects within the command
- TMDL scripts only support one command today: `createOrReplace`

Example of a TMDL script using `createOrReplace`:

```tmdl
createOrReplace

    table Product

        measure '# Products' = COUNTROWS('Product')
            formatString: #,##0

        column 'Product Name'
            dataType: string

        ...
```

---

## Task: Setting Descriptions in TMDL Objects

**DO:**
- The format should be `/// Description` placed right above each object such as `table`, `column`, or `measure` identifier in the TMDL code:
    ```tmdl    
    /// Description line 1
    /// Description line 2
    measure 'Measure1' = [DAX Expression]
        formatString: #,##0
    
    /// Description line 1
    column 'Column1'
        formatString: #,##0
        dataType: string
    ```
- Ensure descriptions provide clear explanations of the definitions and purpose
- Enhance existing descriptions but use them as baseline
- Use concise and meaningful descriptions

**DON'T:**
- Don't use the `description` property - use `///` syntax instead
- Don't change any other property while inserting descriptions

---

## Task: Creating Measures in TMDL

- Always include a `formatString` property appropriate for the measure type
- Always include a description following the `///` rules above
- Don't create measures for non-aggregatable columns (keys, descriptions) unless they specify a `summarizeBy` property different than `none`
- Multi-line DAX expression should be enclosed within triple backticks
- The DAX expression should appear after the measure name preceded with the `=` sign
- If it's a single line DAX expression, add it immediately after the measure name and `=` sign
- Measures should go to the top of the table object, before any column declaration

### Format String Reference

| Type | Format | Output |
|---|---|---|
| Currency | `$#,##0.00` | $1,234.56 |
| Percentage | `0.00%` | 45.67% |
| Integer | `#,##0` | 1,234 |
| Decimal | `#,##0.00` | 1,234.56 |
| Thousands | `#,##0,K` | 1,234K |
| Millions | `#,##0,,M` | 1M |

---

## Task: Setting Descriptions in Power Query / M Code

- Insert a comment above the code explaining what that piece of code is doing
- Do not start the comment with the word Step or a number
- Do not copy code into the comment
- Keep the comments to a maximum of 225 characters
- Update the step name explaining what that piece of code is doing
- The step name should be enclosed in double quotes and preceded by the `#`
- The step name should always start with a verb in the past tense
- The step name should have spaces between words
- Keep the step name to a maximum of 50 characters
