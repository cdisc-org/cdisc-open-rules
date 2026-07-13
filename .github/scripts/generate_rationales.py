#!/usr/bin/env python3
"""
Reads summary_table.md and writes rationales.csv.

The output CSV contains one row per failed test case (Match = ❌) with blank
Fixed and Reason columns, ready to be filled in by reviewer.

Usage:
    python generate_rationales.py <summary_table.md> <rationales.csv>
"""

import argparse
import csv
import re
import sys
from pathlib import Path


def generate(summary_path: Path, output_path: Path) -> int:
    if not summary_path.exists():
        print(f"ERROR: {summary_path} not found", file=sys.stderr)
        return 1

    failed = []
    for line in summary_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 6:
            continue
        rule, typ, num, match = cols[0], cols[1], cols[2], cols[5]
        if not re.match(r"CORE-\d+", rule):
            continue
        if "\u274c" in match:  # ❌
            failed.append((rule, typ, num))

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Rule", "Type", "Number", "Fixed", "Reason"])
        for rule, typ, num in failed:
            writer.writerow([rule, typ, num, "", ""])

    print(f"Wrote {len(failed)} rationales to {output_path}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a rationales.csv template from summary_table.md."
    )
    parser.add_argument("summary", type=Path, help="Path to summary_table.md")
    parser.add_argument("output", type=Path, help="Path for the output rationales.csv")
    args = parser.parse_args()
    sys.exit(generate(args.summary, args.output))
