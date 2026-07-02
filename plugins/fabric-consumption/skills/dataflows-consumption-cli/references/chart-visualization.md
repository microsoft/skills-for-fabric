# Preview Data Visualization

Render dataflow preview data as ASCII charts directly in the console. Supports line charts (trends over time) and bar/pie charts (category proportions).

## Chart Types

| Chart | Script | Best For |
|---|---|---|
| Line | `charts/line_chart.py` | Trends over time, sequential numeric values |
| Bar | `charts/bar_chart.py` | Category proportions, distributions (default mode) |
| Pie | `charts/bar_chart.py --circle` | Circular proportions (requires `--circle` flag) |

## Data Preparation

Extract preview data from a decoded dataflow definition into two parallel JSON arrays:

- **labels**: category names or time-axis labels
- **values**: corresponding numeric values

### From Decoded Definition

After decoding `mashup.pq` and running the dataflow queries, aggregate results into labels and values:

```bash
# Example: aggregate sales by country from dataflow output
# Sort first so labels (unique) and values (group_by) align on the same key order.
LABELS=$(echo "$PREVIEW_DATA" | jq '[.[].Country] | unique')
VALUES=$(echo "$PREVIEW_DATA" | jq 'sort_by(.Country) | [group_by(.Country)[] | map(.Amount) | add]')
```

## Running Charts

### Line Chart

```bash
python references/charts/line_chart.py \
  --labels '["Q1","Q2","Q3","Q4"]' \
  --values '[120000,152000,176000,297000]' \
  --title "Quarterly Sales Trend"
```

### Bar Chart (Default)

```bash
python references/charts/bar_chart.py \
  --labels '["USA","UK","DE","FR"]' \
  --values '[244399,229629,128004,106926]' \
  --title "Sales by Country"
```

### Circular Pie Chart

```bash
python references/charts/bar_chart.py --circle \
  --labels '["Desktop","Mobile","Tablet"]' \
  --values '[45,30,15]' \
  --title "Traffic by Device"
```

## Parameters

| Parameter | Default | Applies To | Description |
|---|---|---|---|
| `--title` | `"Chart"` | All | Title displayed above the chart |
| `--height` | `15` | Line | Chart height in terminal rows |
| `--width` | `60` | Line | Chart width in terminal columns |
| `--radius` | `10` | Pie (circle) | Pie chart radius in rows |
| `--unicode` | off | All | Use Unicode box-drawing characters |
| `--circle` | off | Pie | Render circular pie instead of horizontal bars |

## Display Guidelines

Charts render as ASCII by default for maximum compatibility with tool output panes, CI logs, and terminals. After running a chart script, copy the stdout output into the response text inside a fenced code block so the user can see it directly in the conversation.

## Pure Python 3

Both scripts are dependency-free (stdlib only). No `pip install` required.
