# Parameters & Filters

## Report parameters

Declare parameters after `ReportSections`. Populate list parameters from **value datasets** (live
`VALUES()` queries) for both the default and the valid-values list, and set `<MultiValue>true</MultiValue>`
for multi-select.

```xml
<ReportParameter Name="ClaimStatus">
  <DataType>String</DataType>
  <MultiValue>true</MultiValue>
  <DefaultValue>
    <DataSetReference>
      <DataSetName>StatusValues</DataSetName>
      <ValueField>ClaimStatus</ValueField>
    </DataSetReference>
  </DefaultValue>
  <Prompt>Claim Status</Prompt>
  <ValidValues>
    <DataSetReference>
      <DataSetName>StatusValues</DataSetName>
      <ValueField>ClaimStatus</ValueField>
      <LabelField>ClaimStatus</LabelField>
    </DataSetReference>
  </ValidValues>
</ReportParameter>
```

Scalar date parameters:

```xml
<ReportParameter Name="DateFrom">
  <DataType>DateTime</DataType>
  <DefaultValue><Values><Value>=CDate("2024-02-10")</Value></Values></DefaultValue>
  <Prompt>Claim Date From</Prompt>
</ReportParameter>
```

Lay them out with `<ReportParametersLayout>` (grid of `CellDefinition`s by row/column index).

## Two filtering patterns

### 1. RDL-layer filters (robust, recommended)

Return the data in DAX, then filter on the **DataSet** (or Tablix) with report parameters. Dates use
`Between`; multi-value params use `In`.

```xml
<Filters>
  <Filter>
    <FilterExpression>=Fields!ClaimDate.Value</FilterExpression>
    <Operator>Between</Operator>
    <FilterValues>
      <FilterValue>=Parameters!DateFrom.Value</FilterValue>
      <FilterValue>=Parameters!DateTo.Value</FilterValue>
    </FilterValues>
  </Filter>
  <Filter>
    <FilterExpression>=Fields!ClaimStatus.Value</FilterExpression>
    <Operator>In</Operator>
    <FilterValues>
      <FilterValue>=Parameters!ClaimStatus.Value</FilterValue>
    </FilterValues>
  </Filter>
</Filters>
```

With this pattern, compute KPIs as **report aggregates** over the filtered dataset so they honor the
same filters:

```
=Sum(Fields!ClaimAmount.Value, "ClaimDetails")
=CountRows("ClaimDetails")
```

This avoids fragile DAX and is the recommended default.

### 2. DAX-layer filters (`QueryParameters` + `TREATAS`)

More "native", but easy to get wrong for multi-value. Map report params into the query and filter in
DAX:

```xml
<Query>
  <DataSourceName>SemanticModel</DataSourceName>
  <QueryParameters>
    <QueryParameter Name="ClaimStatus">
      <Value>=Parameters!ClaimStatus.Value</Value>
    </QueryParameter>
  </QueryParameters>
  <CommandText>EVALUATE
SUMMARIZECOLUMNS('Claims'[Claim Status],
  TREATAS({ @ClaimStatus }, 'Claims'[Claim Status]),
  "Amount", [Total Claim Amount])</CommandText>
</Query>
```

## Recommendation

Use **pattern 1** for reliability. Reach for pattern 2 only when the model must do the aggregation
server-side over large data and you can validate the multi-value expansion.
