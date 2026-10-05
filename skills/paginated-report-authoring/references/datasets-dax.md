# Datasets & DAX

Every dataset in a semantic-model-bound paginated report is a **DAX query** and **must start with
`EVALUATE`** (it returns a table).

## Detail grain — prefer `SELECTCOLUMNS` + `RELATED()`

For a predictable one-row-per-record table, `SELECTCOLUMNS` lets you name every output column, and
`RELATED()` pulls dimension attributes across the star schema:

```dax
EVALUATE
SELECTCOLUMNS('Claims',
  "ClaimID",      'Claims'[Claim ID],
  "ClaimDate",    'Claims'[Claim Date],
  "ClaimStatus",  'Claims'[Claim Status],
  "ClaimAmount",  'Claims'[Claim Amount],
  "ClaimType",    RELATED('Claim Type'[Claim Type Name]),
  "CustomerName", RELATED('Customer'[Customer Name]),
  "State",        RELATED('Customer'[State]),
  "PolicyType",   RELATED('Policy'[Policy Type]),
  "VehicleMake",  RELATED('Vehicle'[Make]),
  "VehicleModel", RELATED('Vehicle'[Model]),
  "Adjuster",     RELATED('Adjuster'[Adjuster Name]),
  "RepairShop",   RELATED('Repair Shop'[Shop Name])
)
```

`RELATED()` works because each fact row has exactly one related dimension row (many-to-one).
Use `SUMMARIZECOLUMNS` instead only when you specifically want grouped aggregates.

## The `<DataField>` bracketing trap (blank-report cause)

DAX/ADOMD result column names are **bracketed**, and grouping columns are **table-qualified**. The
RDL `<Field>` must map `<DataField>` to the **result** column name — not the friendly name:

| DAX construct                                  | Result column name  | `<DataField>`        |
|------------------------------------------------|---------------------|----------------------|
| Named column: `"ClaimID", ...`                 | `[ClaimID]`         | `[ClaimID]`          |
| Measure: `"Sales", [Sales Amount]`             | `[Sales]`           | `[Sales]`            |
| Grouping column: `VALUES('Product'[Category])` | `Product[Category]` | `Product[Category]`  |

```xml
<Field Name="ClaimID">
  <DataField>[ClaimID]</DataField>       <!-- bracketed to match SELECTCOLUMNS output -->
  <rd:TypeName>System.Int64</rd:TypeName>
</Field>
```

- The friendly `Field Name="ClaimID"` stays simple — that is what report expressions reference as
  `Fields!ClaimID.Value`.
- Only `<DataField>` gets the brackets / table-qualification.
- Get this wrong and columns render **blank** (no error).

## `rd:TypeName` mapping

| Column | `rd:TypeName` |
|---|---|
| Integer key/amount | `System.Int64` |
| Decimal / currency | `System.Decimal` |
| Date | `System.DateTime` |
| Text | `System.String` |

## Value datasets for parameter dropdowns

Strip blanks and sort so the picker is clean:

```dax
EVALUATE
SELECTCOLUMNS(
  FILTER(VALUES('Claims'[Claim Status]), NOT ISBLANK('Claims'[Claim Status])),
  "ClaimStatus", 'Claims'[Claim Status]
)
ORDER BY [ClaimStatus]
```

## Text-typed dates

Only true **Date** columns range-filter cleanly. If a date is stored as **Text**, convert it in the
query before filtering/formatting:

```dax
"CloseDate", DATEVALUE('Claims'[Claim Close Date])
```
