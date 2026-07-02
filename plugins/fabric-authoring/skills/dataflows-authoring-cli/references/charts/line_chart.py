#!/usr/bin/env python3
"""Render a line chart in the console. Defaults to ASCII for maximum compatibility."""

import argparse
import json
import sys


def line_chart(labels, values, title="Chart", height=15, width=60, unicode=False):
    if not values:
        print("  (no data)")
        return

    n = len(values)
    v_min, v_max = min(values), max(values)
    v_range = v_max - v_min or 1

    POINT = "●" if unicode else "*"
    H_LINE = "─" if unicode else "-"
    V_LINE = "│" if unicode else "|"
    UP_SLOPE = "╱" if unicode else "/"
    DN_SLOPE = "╲" if unicode else "\\"
    CORNER = "└" if unicode else "+"

    col_positions = []
    for i in range(n):
        col_positions.append(int(i * (width - 1) / max(n - 1, 1)))

    grid_width = width
    grid = [[" " for _ in range(grid_width)] for _ in range(height + 1)]

    for i, v in enumerate(values):
        row = round((v - v_min) / v_range * height)
        col = col_positions[i]
        if 0 <= row <= height and 0 <= col < grid_width:
            grid[row][col] = POINT

        if i < n - 1:
            next_row = round((values[i + 1] - v_min) / v_range * height)
            col_next = col_positions[i + 1]

            if next_row == row:
                for c in range(col + 1, col_next):
                    if 0 <= c < grid_width:
                        grid[row][c] = H_LINE
            else:
                step = 1 if next_row > row else -1
                steps = abs(next_row - row)
                for s in range(1, steps + 1):
                    mid_col = col + round(s * (col_next - col) / steps)
                    mid_row = row + s * step
                    if 0 <= mid_row <= height and 0 <= mid_col < grid_width:
                        grid[mid_row][mid_col] = UP_SLOPE if step > 0 else DN_SLOPE

    print()
    print(f"  {title}")
    print(f"  {H_LINE * (grid_width + 12)}")

    for row in range(height, -1, -1):
        val = v_min + (v_range * row / height)
        prefix = f"{val:>8.1f} {V_LINE} "
        print(prefix + "".join(grid[row]))

    print(f"{'':>9} {CORNER}{H_LINE}" + H_LINE * grid_width)

    if labels:
        max_lbl = max((len(str(lbl)) for lbl in labels), default=0)
        axis_line = [" "] * (grid_width + 11 + max_lbl)
        for i, lbl in enumerate(labels):
            pos = col_positions[i] + 11
            lbl_str = str(lbl)
            for j, ch in enumerate(lbl_str):
                idx = pos + j
                if idx < len(axis_line):
                    axis_line[idx] = ch
        print("".join(axis_line))

    print()


def main():
    parser = argparse.ArgumentParser(description="Console line chart")
    parser.add_argument("--labels", required=True, help="JSON array of x-axis labels")
    parser.add_argument("--values", required=True, help="JSON array of numeric values")
    parser.add_argument("--title", default="Chart", help="Chart title")
    parser.add_argument("--height", type=int, default=15, help="Chart height in rows")
    parser.add_argument("--width", type=int, default=60, help="Chart width in columns")
    parser.add_argument("--unicode", action="store_true", help="Use Unicode characters instead of ASCII")
    args = parser.parse_args()

    labels = json.loads(args.labels)
    values = [float(v) for v in json.loads(args.values)]

    if len(labels) != len(values):
        print("Error: labels and values must have the same length.", file=sys.stderr)
        sys.exit(1)

    line_chart(labels, values, title=args.title, height=args.height, width=args.width,
               unicode=args.unicode)


if __name__ == "__main__":
    main()
