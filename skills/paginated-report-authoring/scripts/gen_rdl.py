#!/usr/bin/env python3
"""Generate the page_test paginated report RDL bound to autoclaims_sm."""
import base64, json, xml.dom.minidom as minidom, os

NS = "http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition"
RD = "http://schemas.microsoft.com/SQLServer/reporting/reportdesigner"

WORKSPACE = "Amol_dev"
DATASET = "autoclaims_sm"
DATASET_GUID = "15d41ed3-bee4-4f14-a898-b36ab248bc92"

# ---- helpers -------------------------------------------------------------
def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))

def textbox(name, value, *, bold=False, size="9pt", color="Black",
            bg=None, align="Left", valign="Middle", fmt=None,
            can_grow=True, border=True):
    style = []
    style.append("<FontFamily>Segoe UI</FontFamily>")
    style.append(f"<FontSize>{size}</FontSize>")
    if bold:
        style.append("<FontWeight>Bold</FontWeight>")
    style.append(f"<Color>{color}</Color>")
    para_style = f"<TextAlign>{align}</TextAlign>"
    cell_style = []
    if bg:
        cell_style.append(f"<BackgroundColor>{bg}</BackgroundColor>")
    if border:
        cell_style.append("<Border><Color>#d0d0d0</Color><Style>Solid</Style><Width>0.5pt</Width></Border>")
    else:
        cell_style.append("<Border><Style>None</Style></Border>")
    cell_style.append("<PaddingLeft>3pt</PaddingLeft><PaddingRight>3pt</PaddingRight>"
                      "<PaddingTop>2pt</PaddingTop><PaddingBottom>2pt</PaddingBottom>")
    cell_style.append(f"<VerticalAlign>{valign}</VerticalAlign>")
    fmt_xml = f"<Format>{esc(fmt)}</Format>" if fmt else ""
    return f"""<Textbox Name="{name}">
  <CanGrow>{str(can_grow).lower()}</CanGrow>
  <KeepTogether>true</KeepTogether>
  <Paragraphs>
    <Paragraph>
      <TextRuns>
        <TextRun>
          <Value>{esc(value)}</Value>
          <Style>{''.join(style)}{fmt_xml}</Style>
        </TextRun>
      </TextRuns>
      <Style>{para_style}</Style>
    </Paragraph>
  </Paragraphs>
  <rd:DefaultName>{name}</rd:DefaultName>
  <Style>{''.join(cell_style)}</Style>
</Textbox>"""

def cell(tb):
    return f"<TablixCell><CellContents>{tb}</CellContents></TablixCell>"

# ---- detail table definition --------------------------------------------
# (header label, detail expression, width_in, align, format, is_number)
COLS = [
    ("Claim ID",    "=Fields!ClaimID.Value",       0.8, "Center", None, False),
    ("Claim Date",  "=Fields!ClaimDate.Value",     1.0, "Center", "d",  False),
    ("Status",      "=Fields!ClaimStatus.Value",   1.0, "Center", None, False),
    ("Customer",    "=Fields!CustomerName.Value",  1.5, "Left",   None, False),
    ("State",       "=Fields!State.Value",         0.6, "Center", None, False),
    ("Policy Type", "=Fields!PolicyType.Value",    1.2, "Left",   None, False),
    ("Vehicle",     "=Fields!VehicleMake.Value & \" \" & Fields!VehicleModel.Value", 1.5, "Left", None, False),
    ("Adjuster",    "=Fields!Adjuster.Value",      1.3, "Left",   None, False),
    ("Repair Shop", "=Fields!RepairShop.Value",    1.6, "Left",   None, False),
    ("Claim Amount","=Fields!ClaimAmount.Value",   1.2, "Right",  "'$'#,0", True),
]
TOTAL_W = sum(c[2] for c in COLS)

HDR_BG = "#2E5A87"
GRP_BG = "#DCE6F1"
TOT_BG = "#B8CCE4"

def build_tablix():
    tcols = "".join(f"<TablixColumn><Width>{w}in</Width></TablixColumn>"
                    for (_, _, w, *_ ) in COLS)

    # Header row
    hdr_cells = "".join(
        cell(textbox(f"h_{i}", lbl, bold=True, color="White", bg=HDR_BG,
                     align="Center", size="9pt"))
        for i, (lbl, *_ ) in enumerate(COLS))

    # Group header row (Claim Type banner spanning all columns)
    grp_cells = [cell(textbox("g_type",
                              "=\"Claim Type:  \" & Fields!ClaimType.Value",
                              bold=True, bg=GRP_BG, align="Left", size="10pt"))]
    for i in range(1, len(COLS)):
        grp_cells.append(cell(textbox(f"g_pad_{i}", "", bg=GRP_BG)))
    grp_cells = "".join(grp_cells)
    col_span = f"""<ColSpan>{len(COLS)}</ColSpan>"""  # applied on first cell below

    # Detail row
    det_cells = ""
    for i, (lbl, expr, w, align, fmt, isnum) in enumerate(COLS):
        det_cells += cell(textbox(f"d_{i}", expr, align=align, fmt=fmt,
                                  size="8.5pt"))

    # Group footer (subtotal) row
    gf_cells = [cell(textbox("gf_lbl", "=\"Subtotal (\" & CountRows() & \" claims)\"",
                             bold=True, bg=GRP_BG, align="Right"))]
    for i in range(1, len(COLS) - 1):
        gf_cells.append(cell(textbox(f"gf_pad_{i}", "", bg=GRP_BG)))
    gf_cells.append(cell(textbox("gf_amt", "=Sum(Fields!ClaimAmount.Value)",
                                 bold=True, bg=GRP_BG, align="Right", fmt="'$'#,0")))
    gf_cells = "".join(gf_cells)

    # Grand total row
    gt_cells = [cell(textbox("gt_lbl",
                             "=\"GRAND TOTAL (\" & CountRows() & \" claims)\"",
                             bold=True, bg=TOT_BG, align="Right", size="9.5pt"))]
    for i in range(1, len(COLS) - 1):
        gt_cells.append(cell(textbox(f"gt_pad_{i}", "", bg=TOT_BG)))
    gt_cells.append(cell(textbox("gt_amt", "=Sum(Fields!ClaimAmount.Value)",
                                 bold=True, bg=TOT_BG, align="Right", fmt="'$'#,0",
                                 size="9.5pt")))
    gt_cells = "".join(gt_cells)

    return f"""<Tablix Name="ClaimsTablix">
  <TablixBody>
    <TablixColumns>{tcols}</TablixColumns>
    <TablixRows>
      <TablixRow>
        <Height>0.28in</Height>
        <TablixCells>{hdr_cells}</TablixCells>
      </TablixRow>
      <TablixRow>
        <Height>0.28in</Height>
        <TablixCells>{grp_cells}</TablixCells>
      </TablixRow>
      <TablixRow>
        <Height>0.24in</Height>
        <TablixCells>{det_cells}</TablixCells>
      </TablixRow>
      <TablixRow>
        <Height>0.26in</Height>
        <TablixCells>{gf_cells}</TablixCells>
      </TablixRow>
      <TablixRow>
        <Height>0.30in</Height>
        <TablixCells>{gt_cells}</TablixCells>
      </TablixRow>
    </TablixRows>
  </TablixBody>
  <TablixColumnHierarchy>
    <TablixMembers>{''.join('<TablixMember />' for _ in COLS)}</TablixMembers>
  </TablixColumnHierarchy>
  <TablixRowHierarchy>
    <TablixMembers>
      <TablixMember>
        <KeepWithGroup>After</KeepWithGroup>
        <RepeatOnNewPage>true</RepeatOnNewPage>
        <FixedData>true</FixedData>
      </TablixMember>
      <TablixMember>
        <Group Name="ClaimTypeGroup">
          <GroupExpressions>
            <GroupExpression>=Fields!ClaimType.Value</GroupExpression>
          </GroupExpressions>
        </Group>
        <SortExpressions>
          <SortExpression><Value>=Fields!ClaimType.Value</Value></SortExpression>
        </SortExpressions>
        <TablixMembers>
          <TablixMember>
            <KeepWithGroup>After</KeepWithGroup>
          </TablixMember>
          <TablixMember>
            <Group Name="ClaimDetailGroup" />
            <SortExpressions>
              <SortExpression><Value>=Fields!ClaimDate.Value</Value></SortExpression>
            </SortExpressions>
          </TablixMember>
          <TablixMember>
            <KeepWithGroup>Before</KeepWithGroup>
          </TablixMember>
        </TablixMembers>
      </TablixMember>
      <TablixMember>
        <KeepWithGroup>Before</KeepWithGroup>
      </TablixMember>
    </TablixMembers>
  </TablixRowHierarchy>
  <DataSetName>ClaimDetails</DataSetName>
  <Top>2.35in</Top>
  <Left>0in</Left>
  <Height>1.36in</Height>
  <Width>{TOTAL_W}in</Width>
  <Style>
    <Border><Style>None</Style></Border>
  </Style>
</Tablix>"""

# ---- KPI band ------------------------------------------------------------
def kpi_box(name, top_left, label, value_expr, fmt):
    left = top_left
    return f"""<Rectangle Name="{name}_rect">
  <ReportItems>
    <Textbox Name="{name}_lbl">
      <CanGrow>true</CanGrow><KeepTogether>true</KeepTogether>
      <Paragraphs><Paragraph><TextRuns><TextRun>
        <Value>{esc(label)}</Value>
        <Style><FontFamily>Segoe UI</FontFamily><FontSize>9pt</FontSize><Color>White</Color></Style>
      </TextRun></TextRuns><Style><TextAlign>Left</TextAlign></Style></Paragraph></Paragraphs>
      <Top>0.06in</Top><Left>0.1in</Left><Height>0.25in</Height><Width>2.1in</Width>
      <Style><Border><Style>None</Style></Border></Style>
    </Textbox>
    <Textbox Name="{name}_val">
      <CanGrow>true</CanGrow><KeepTogether>true</KeepTogether>
      <Paragraphs><Paragraph><TextRuns><TextRun>
        <Value>{esc(value_expr)}</Value>
        <Style><FontFamily>Segoe UI</FontFamily><FontSize>20pt</FontSize><FontWeight>Bold</FontWeight><Color>White</Color><Format>{esc(fmt)}</Format></Style>
      </TextRun></TextRuns><Style><TextAlign>Left</TextAlign></Style></Paragraph></Paragraphs>
      <Top>0.32in</Top><Left>0.1in</Left><Height>0.4in</Height><Width>2.1in</Width>
      <Style><Border><Style>None</Style></Border></Style>
    </Textbox>
  </ReportItems>
  <KeepTogether>true</KeepTogether>
  <Top>1.55in</Top><Left>{left}in</Left><Height>0.8in</Height><Width>2.3in</Width>
  <Style><BackgroundColor>{HDR_BG}</BackgroundColor><Border><Style>None</Style></Border></Style>
</Rectangle>"""

def build_kpis():
    kpis = [
        ("kpiAmount", 0.0,  "Total Claim Amount",
         "=Sum(Fields!ClaimAmount.Value, \"ClaimDetails\")", "'$'#,0"),
        ("kpiCount",  2.45, "Claim Count",
         "=CountRows(\"ClaimDetails\")", "#,0"),
        ("kpiOpen",   4.9,  "Open Claim Rate",
         "=Sum(IIf(Fields!ClaimStatus.Value=\"Open\",1,0),\"ClaimDetails\")/CountRows(\"ClaimDetails\")", "0.0%"),
        ("kpiAvg",    7.35, "Average Claim Amount",
         "=Avg(Fields!ClaimAmount.Value, \"ClaimDetails\")", "'$'#,0"),
    ]
    return "".join(kpi_box(*k) for k in kpis)

# ---- datasets ------------------------------------------------------------
MAIN_DAX = ("EVALUATE SELECTCOLUMNS('Claims', "
            "\"ClaimID\", 'Claims'[Claim ID], "
            "\"ClaimDate\", 'Claims'[Claim Date], "
            "\"ClaimStatus\", 'Claims'[Claim Status], "
            "\"ClaimAmount\", 'Claims'[Claim Amount], "
            "\"ClaimType\", RELATED('Claim Type'[Claim Type Name]), "
            "\"CustomerName\", RELATED('Customer'[Customer Name]), "
            "\"State\", RELATED('Customer'[State]), "
            "\"PolicyType\", RELATED('Policy'[Policy Type]), "
            "\"VehicleMake\", RELATED('Vehicle'[Make]), "
            "\"VehicleModel\", RELATED('Vehicle'[Model]), "
            "\"Adjuster\", RELATED('Adjuster'[Adjuster Name]), "
            "\"RepairShop\", RELATED('Repair Shop'[Shop Name]))")

MAIN_FIELDS = [
    ("ClaimID", "System.Int64"), ("ClaimDate", "System.DateTime"),
    ("ClaimStatus", "System.String"), ("ClaimAmount", "System.Int64"),
    ("ClaimType", "System.String"), ("CustomerName", "System.String"),
    ("State", "System.String"), ("PolicyType", "System.String"),
    ("VehicleMake", "System.String"), ("VehicleModel", "System.String"),
    ("Adjuster", "System.String"), ("RepairShop", "System.String"),
]

def fields_xml(fields):
    out = []
    for name, typ in fields:
        out.append(f"<Field Name=\"{name}\"><DataField>[{name}]</DataField>"
                   f"<rd:TypeName>{typ}</rd:TypeName></Field>")
    return "<Fields>" + "".join(out) + "</Fields>"

def value_dataset(name, col_dax, colname):
    dax = (f"EVALUATE SELECTCOLUMNS(FILTER(VALUES({col_dax}), "
           f"NOT ISBLANK({col_dax})), \"{colname}\", {col_dax}) "
           f"ORDER BY [{colname}]")
    return f"""<DataSet Name="{name}">
  <Query>
    <DataSourceName>PowerBIDataset</DataSourceName>
    <CommandType>Text</CommandType>
    <CommandText>{esc(dax)}</CommandText>
  </Query>
  {fields_xml([(colname, "System.String")])}
</DataSet>"""

def main_dataset():
    filters = """<Filters>
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
      <Filter>
        <FilterExpression>=Fields!ClaimType.Value</FilterExpression>
        <Operator>In</Operator>
        <FilterValues>
          <FilterValue>=Parameters!ClaimType.Value</FilterValue>
        </FilterValues>
      </Filter>
      <Filter>
        <FilterExpression>=Fields!State.Value</FilterExpression>
        <Operator>In</Operator>
        <FilterValues>
          <FilterValue>=Parameters!State.Value</FilterValue>
        </FilterValues>
      </Filter>
    </Filters>"""
    return f"""<DataSet Name="ClaimDetails">
  <Query>
    <DataSourceName>PowerBIDataset</DataSourceName>
    <CommandType>Text</CommandType>
    <CommandText>{esc(MAIN_DAX)}</CommandText>
  </Query>
  {fields_xml(MAIN_FIELDS)}
  {filters}
</DataSet>"""

# ---- report parameters ---------------------------------------------------
def parameters_xml():
    return f"""<ReportParameters>
  <ReportParameter Name="DateFrom">
    <DataType>DateTime</DataType>
    <DefaultValue><Values><Value>=CDate("2024-02-10")</Value></Values></DefaultValue>
    <Prompt>Claim Date From</Prompt>
  </ReportParameter>
  <ReportParameter Name="DateTo">
    <DataType>DateTime</DataType>
    <DefaultValue><Values><Value>=CDate("2026-03-30")</Value></Values></DefaultValue>
    <Prompt>Claim Date To</Prompt>
  </ReportParameter>
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
  <ReportParameter Name="ClaimType">
    <DataType>String</DataType>
    <MultiValue>true</MultiValue>
    <DefaultValue>
      <DataSetReference>
        <DataSetName>TypeValues</DataSetName>
        <ValueField>ClaimType</ValueField>
      </DataSetReference>
    </DefaultValue>
    <Prompt>Claim Type</Prompt>
    <ValidValues>
      <DataSetReference>
        <DataSetName>TypeValues</DataSetName>
        <ValueField>ClaimType</ValueField>
        <LabelField>ClaimType</LabelField>
      </DataSetReference>
    </ValidValues>
  </ReportParameter>
  <ReportParameter Name="State">
    <DataType>String</DataType>
    <MultiValue>true</MultiValue>
    <DefaultValue>
      <DataSetReference>
        <DataSetName>StateValues</DataSetName>
        <ValueField>State</ValueField>
      </DataSetReference>
    </DefaultValue>
    <Prompt>Customer State</Prompt>
    <ValidValues>
      <DataSetReference>
        <DataSetName>StateValues</DataSetName>
        <ValueField>State</ValueField>
        <LabelField>State</LabelField>
      </DataSetReference>
    </ValidValues>
  </ReportParameter>
</ReportParameters>
<ReportParametersLayout>
  <GridLayoutDefinition>
    <NumberOfColumns>5</NumberOfColumns>
    <NumberOfRows>1</NumberOfRows>
    <CellDefinitions>
      <CellDefinition><RowIndex>0</RowIndex><ColumnIndex>0</ColumnIndex><ParameterName>DateFrom</ParameterName></CellDefinition>
      <CellDefinition><RowIndex>0</RowIndex><ColumnIndex>1</ColumnIndex><ParameterName>DateTo</ParameterName></CellDefinition>
      <CellDefinition><RowIndex>0</RowIndex><ColumnIndex>2</ColumnIndex><ParameterName>ClaimStatus</ParameterName></CellDefinition>
      <CellDefinition><RowIndex>0</RowIndex><ColumnIndex>3</ColumnIndex><ParameterName>ClaimType</ParameterName></CellDefinition>
      <CellDefinition><RowIndex>0</RowIndex><ColumnIndex>4</ColumnIndex><ParameterName>State</ParameterName></CellDefinition>
    </CellDefinitions>
  </GridLayoutDefinition>
</ReportParametersLayout>"""

# ---- body / page ---------------------------------------------------------
def build_report():
    title = textbox("ReportTitle", "Auto Claims Detail Report", bold=True,
                    size="22pt", color=HDR_BG, border=False)
    subtitle = textbox("ReportSubtitle",
                       "=\"Claim Date \" & Format(Parameters!DateFrom.Value,\"d\") & \" to \" & Format(Parameters!DateTo.Value,\"d\") & \"   |   Source model: autoclaims_sm\"",
                       size="10pt", color="#555555", border=False)
    title_item = title.replace("<rd:DefaultName>ReportTitle</rd:DefaultName>",
        "<Top>0.15in</Top><Left>0in</Left><Height>0.45in</Height><Width>8in</Width><rd:DefaultName>ReportTitle</rd:DefaultName>")
    sub_item = subtitle.replace("<rd:DefaultName>ReportSubtitle</rd:DefaultName>",
        "<Top>0.75in</Top><Left>0in</Left><Height>0.3in</Height><Width>10in</Width><rd:DefaultName>ReportSubtitle</rd:DefaultName>")

    body_items = title_item + sub_item + build_kpis() + build_tablix()

    footer_left = textbox("FooterExec",
        "=\"Generated: \" & Format(Globals!ExecutionTime,\"g\")",
        size="8pt", color="#777777", border=False)
    footer_left = footer_left.replace("<rd:DefaultName>FooterExec</rd:DefaultName>",
        "<Top>0.05in</Top><Left>0in</Left><Height>0.2in</Height><Width>4in</Width><rd:DefaultName>FooterExec</rd:DefaultName>")
    footer_right = textbox("FooterPage",
        "=\"Page \" & Globals!PageNumber & \" of \" & Globals!TotalPages",
        size="8pt", color="#777777", align="Right", border=False)
    footer_right = footer_right.replace("<rd:DefaultName>FooterPage</rd:DefaultName>",
        "<Top>0.05in</Top><Left>6in</Left><Height>0.2in</Height><Width>4in</Width><rd:DefaultName>FooterPage</rd:DefaultName>")

    datasets = (main_dataset()
                + value_dataset("StatusValues", "'Claims'[Claim Status]", "ClaimStatus")
                + value_dataset("TypeValues", "'Claim Type'[Claim Type Name]", "ClaimType")
                + value_dataset("StateValues", "'Customer'[State]", "State"))

    rdl = f"""<?xml version="1.0" encoding="utf-8"?>
<Report MustUnderstand="df" xmlns="{NS}" xmlns:rd="{RD}" xmlns:df="{NS}/defaultfontfamily">
  <rd:ReportUnitType>Inch</rd:ReportUnitType>
  <rd:ReportID>a1b2c3d4-0000-4a00-9000-000000000001</rd:ReportID>
  <df:DefaultFontFamily>Segoe UI</df:DefaultFontFamily>
  <AutoRefresh>0</AutoRefresh>
  <DataSources>
    <DataSource Name="PowerBIDataset">
      <ConnectionProperties>
        <DataProvider>PBIDATASET</DataProvider>
        <ConnectString>Data Source=pbiazure://api.powerbi.com/;Identity Provider="https://login.microsoftonline.com/organizations, https://analysis.windows.net/powerbi/api, f0b72488-7082-488a-a7e8-eada97bd842d";Initial Catalog=sobe_wowvirtualserver-{DATASET_GUID};Integrated Security=ClaimsToken</ConnectString>
      </ConnectionProperties>
      <rd:SecurityType>None</rd:SecurityType>
      <rd:DataSourceID>9f2c1b40-3a55-4e88-bb21-c0e8d7f43e21</rd:DataSourceID>
      <rd:PowerBIWorkspaceName>{WORKSPACE}</rd:PowerBIWorkspaceName>
      <rd:PowerBIDatasetName>{DATASET}</rd:PowerBIDatasetName>
    </DataSource>
  </DataSources>
  <DataSets>
    {datasets}
  </DataSets>
  <ReportSections>
    <ReportSection>
      <Body>
        <ReportItems>
          {body_items}
        </ReportItems>
        <Height>3.8in</Height>
        <Style><Border><Style>None</Style></Border></Style>
      </Body>
      <Width>14.2in</Width>
      <Page>
        <PageFooter>
          <Height>0.3in</Height>
          <PrintOnFirstPage>true</PrintOnFirstPage>
          <PrintOnLastPage>true</PrintOnLastPage>
          <ReportItems>
            {footer_left}
            {footer_right}
          </ReportItems>
          <Style><Border><Style>None</Style></Border></Style>
        </PageFooter>
        <PageHeight>8.5in</PageHeight>
        <PageWidth>14in</PageWidth>
        <LeftMargin>0.4in</LeftMargin>
        <RightMargin>0.4in</RightMargin>
        <TopMargin>0.4in</TopMargin>
        <BottomMargin>0.4in</BottomMargin>
        <Style />
      </Page>
    </ReportSection>
  </ReportSections>
  {parameters_xml()}
</Report>"""
    return rdl

def main():
    rdl = build_report()
    # validate well-formed
    dom = minidom.parseString(rdl)
    here = os.path.dirname(os.path.abspath(__file__))
    rdl_path = os.path.join(here, "page_test.rdl")
    with open(rdl_path, "w", encoding="utf-8") as f:
        f.write(rdl)
    payload = base64.b64encode(rdl.encode("utf-8")).decode("ascii")
    req = {
        "displayName": "page_test",
        "description": "Sample auto-claims detail paginated report over the autoclaims_sm semantic model.",
        "definition": {
            "format": "PaginatedReportDefinition",
            "parts": [
                {"path": "page_test.rdl", "payload": payload, "payloadType": "InlineBase64"}
            ]
        }
    }
    req_path = os.path.join(here, "create_request.json")
    with open(req_path, "w", encoding="utf-8") as f:
        json.dump(req, f)
    print("RDL bytes:", len(rdl))
    print("RDL well-formed: OK")
    print("Datasets:", rdl.count("<DataSet "))
    print("Parameters:", rdl.count("<ReportParameter "))
    print("Wrote:", rdl_path)
    print("Wrote:", req_path)

if __name__ == "__main__":
    main()

