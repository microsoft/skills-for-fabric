#!/usr/bin/env python3
"""Render a bar or pie chart in the console. Defaults to horizontal bar chart (ASCII)."""

import argparse
import json
import math
import sys


SLICE_SYMBOLS_UNICODE = ["█", "▓", "▒", "░", "◆", "◇", "●", "○", "■", "□"]
SLICE_SYMBOLS_ASCII = ["#", "@", "*", "+", "=", "~", ":", ".", "^", "&"]


def bar_chart(labels, values, title="Chart", unicode=False):
    """Horizontal bar chart -- works everywhere."""
    if not values:
        print("  (no data)")
        return

    total = sum(values)
    if total == 0:
        print("  (values sum to zero -- cannot compute proportions)")
        return

    sep = "\u2500" if unicode else "-"
    bar_char = "\u2588" if unicode else "#"

    print()
    print(f"  {title}")
    print(f"  {sep * 62}")
    for lbl, val in zip(labels, values):
        pct = val / total * 100
        bar_len = max(1, round(pct))
        bar = bar_char * bar_len
        print(f"  {str(lbl):<15s} {val:>10.1f}  ({pct:5.1f}%)  |{bar}")
    print()


def pie_chart(labels, values, title="Chart", radius=10, unicode=False):
    """Circular pie chart -- best with Unicode."""
    if not values:
        print("  (no data)")
        return

    symbols = SLICE_SYMBOLS_UNICODE if unicode else SLICE_SYMBOLS_ASCII

    total = sum(values)
    if total == 0:
        print("  (values sum to zero -- cannot compute proportions)")
        return
    n = len(values)

    cum_angles = [0.0]
    for v in values:
        cum_angles.append(cum_angles[-1] + (v / total) * 2 * math.pi)

    h = radius * 2 + 1
    w = radius * 4 + 1
    grid = [[" " for _ in range(w)] for _ in range(h)]

    cx, cy = radius * 2, radius

    for gy in range(h):
        for gx in range(w):
            dx = (gx - cx) / (radius * 2)
            dy = (gy - cy) / radius
            dist = math.sqrt(dx * dx + dy * dy)

            if dist <= 1.0:
                angle = math.atan2(-dy, dx)
                if angle < 0:
                    angle += 2 * math.pi

                for s in range(n):
                    if cum_angles[s] <= angle < cum_angles[s + 1]:
                        grid[gy][gx] = symbols[s % len(symbols)]
                        break
                else:
                    grid[gy][gx] = symbols[(n - 1) % len(symbols)]

    print()
    print(f"  {title}")
    sep = "-" if not unicode else "─"
    print(f"  {sep * (w + 4)}")

    for row in grid:
        print("    " + "".join(row))

    print()

    print("  Legend:")
    for i, (lbl, val) in enumerate(zip(labels, values)):
        sym = symbols[i % len(symbols)]
        pct = (val / total) * 100
        bar_len = max(1, round(pct / 2))
        bar = sym * bar_len
        print(f"    {sym}  {str(lbl):<20s} {val:>10.1f}  ({pct:5.1f}%)  {bar}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Console pie/bar chart")
    parser.add_argument("--labels", required=True, help="JSON array of category labels")
    parser.add_argument("--values", required=True, help="JSON array of numeric values")
    parser.add_argument("--title", default="Chart", help="Chart title")
    parser.add_argument("--radius", type=int, default=10, help="Pie radius in rows (circle mode)")
    parser.add_argument("--unicode", action="store_true", help="Use Unicode characters instead of ASCII")
    parser.add_argument("--circle", action="store_true", help="Render as circular pie chart instead of bar chart")
    args = parser.parse_args()

    labels = json.loads(args.labels)
    values = [float(v) for v in json.loads(args.values)]

    if len(labels) != len(values):
        print("Error: labels and values must have the same length.", file=sys.stderr)
        sys.exit(1)

    if args.circle:
        pie_chart(labels, values, title=args.title, radius=args.radius, unicode=args.unicode)
    else:
        bar_chart(labels, values, title=args.title, unicode=args.unicode)


if __name__ == "__main__":
    main()
