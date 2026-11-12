# RDL Structure — Element Order & Namespaces

The paginated report definition is **RDL 2016 XML** (Report Definition Language). The Fabric and
Power BI Report Builder validators are **strict about element order and namespaces**. Emit the
top-level structure exactly as below.

## Required top-level skeleton

```xml
<?xml version="1.0" encoding="utf-8"?>
<Report MustUnderstand="df"
  xmlns="http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition"
  xmlns:rd="http://schemas.microsoft.com/SQLServer/reporting/reportdesigner"
  xmlns:df="http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition/defaultfontfamily">
  <rd:ReportUnitType>Inch</rd:ReportUnitType>   <!-- near the TOP -->
  <rd:ReportID>{guid}</rd:ReportID>              <!-- near the TOP, not the bottom -->
  <df:DefaultFontFamily>Segoe UI</df:DefaultFontFamily>
  <AutoRefresh>0</AutoRefresh>
  <DataSources> ... </DataSources>
  <DataSets> ... </DataSets>
  <ReportSections>
    <ReportSection>
      <Body> <ReportItems> ... </ReportItems> <Height>..</Height> <Style/> </Body>
      <Width>..</Width>
      <Page> ... margins, PageHeight/PageWidth, header/footer ... </Page>
    </ReportSection>
  </ReportSections>
  <ReportParameters> ... </ReportParameters>          <!-- AFTER ReportSections -->
  <ReportParametersLayout> ... </ReportParametersLayout>
</Report>
```

## Order rules that matter

| Element | Placement |
|---|---|
| `MustUnderstand="df"` (attribute) | On the `<Report>` root |
| `rd:ReportUnitType`, `rd:ReportID` | **First children**, right after `<Report>` |
| `df:DefaultFontFamily` | After the `rd:` elements |
| `AutoRefresh` | Before `DataSources` |
| `DataSources` → `DataSets` → `ReportSections` | In this order |
| `ReportParameters` → `ReportParametersLayout` | **After** `ReportSections` |

## Common validation failures

- Missing `MustUnderstand="df"`, the `df` namespace, or `<df:DefaultFontFamily>`.
- `rd:ReportID` / `rd:ReportUnitType` placed at the **bottom** of the file instead of the top.
- A `<Description>` element as a **direct child of `<Report>`** — omit it; pass the description via
  the create API or import metadata instead.
- Body `ReportItems` out of order relative to the section `Width`/`Page` siblings.

## Page setup (landscape example)

```xml
<Page>
  <PageFooter> ... </PageFooter>
  <PageHeight>8.5in</PageHeight>
  <PageWidth>14in</PageWidth>
  <LeftMargin>0.4in</LeftMargin>
  <RightMargin>0.4in</RightMargin>
  <TopMargin>0.4in</TopMargin>
  <BottomMargin>0.4in</BottomMargin>
  <Style />
</Page>
```

Keep the sum of tablix column widths inside `PageWidth − LeftMargin − RightMargin`, or content spills
to extra physical pages.

## Always validate locally

Parse the generated string before uploading — this catches ordering-independent well-formedness
errors instantly:

```python
import xml.dom.minidom as minidom
minidom.parseString(rdl)   # raises on malformed XML
```
