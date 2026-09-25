# Layout — KPIs, Tablix, Grouping

## KPI band

Render KPI cards as textboxes (optionally inside a `Rectangle`) using **report aggregates** over the
filtered detail dataset so they respect parameters:

| KPI | Expression |
|---|---|
| Total Claim Amount | `=Sum(Fields!ClaimAmount.Value, "ClaimDetails")` |
| Claim Count | `=CountRows("ClaimDetails")` |
| Open Claim Rate | `=Sum(IIf(Fields!ClaimStatus.Value="Open",1,0),"ClaimDetails") / CountRows("ClaimDetails")` |
| Average Claim Amount | `=Avg(Fields!ClaimAmount.Value, "ClaimDetails")` |

Apply number/currency/percent formatting via the textbox `<Format>` (e.g. `'$'#,0`, `#,0`, `0.0%`) —
model measures often have no `FormatString`, so format in the report.

## Grouped detail tablix with subtotals

A correct `TablixRowHierarchy` for **header + group header + detail + group footer + grand total**
produces **5 body rows**, in this order:

```
row0  column headers   (static, top)      RepeatOnNewPage=true
row1  group header      (static in group) "Claim Type: " & Fields!ClaimType.Value
row2  detail            (Group grpDetail)
row3  group footer      (static in group) subtotal: Sum(...)/CountRows()
row4  grand total       (static, bottom)  Sum(...) over whole dataset
```

Row hierarchy shape (leaf order must match the 5 body rows):

```xml
<TablixRowHierarchy>
  <TablixMembers>
    <TablixMember>                       <!-- header -->
      <KeepWithGroup>After</KeepWithGroup>
      <RepeatOnNewPage>true</RepeatOnNewPage>
    </TablixMember>
    <TablixMember>                       <!-- Claim Type group -->
      <Group Name="grpType">
        <GroupExpressions>
          <GroupExpression>=Fields!ClaimType.Value</GroupExpression>
        </GroupExpressions>
      </Group>
      <SortExpressions><SortExpression><Value>=Fields!ClaimType.Value</Value></SortExpression></SortExpressions>
      <TablixMembers>
        <TablixMember><KeepWithGroup>After</KeepWithGroup></TablixMember>   <!-- group header -->
        <TablixMember>                                                     <!-- detail -->
          <Group Name="grpDetail" />
          <SortExpressions><SortExpression><Value>=Fields!ClaimDate.Value</Value></SortExpression></SortExpressions>
        </TablixMember>
        <TablixMember><KeepWithGroup>Before</KeepWithGroup></TablixMember>  <!-- group footer -->
      </TablixMembers>
    </TablixMember>
    <TablixMember><KeepWithGroup>Before</KeepWithGroup></TablixMember>      <!-- grand total -->
  </TablixMembers>
</TablixRowHierarchy>
```

The `TablixColumnHierarchy` has one `<TablixMember/>` per column, and `TablixColumns` has one
`<TablixColumn><Width>..</Width></TablixColumn>` per column. Counts must line up.

## Aggregate scope

- Inside a group footer, `Sum(...)` / `CountRows()` (no scope) = that group's total.
- In the outer static footer, add a dataset scope for the grand total: `Sum(Fields!X.Value)` there
  aggregates the whole tablix dataset.

## Page setup

- Landscape: set `<PageWidth>` > `<PageHeight>` (e.g. 14in x 8.5in).
- Keep total column width ≤ `PageWidth − LeftMargin − RightMargin`.
- Put page number + execution time in the `<PageFooter>`:
  `=Globals!PageNumber & " of " & Globals!TotalPages`, `=Globals!ExecutionTime`.
