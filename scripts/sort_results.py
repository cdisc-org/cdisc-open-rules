#!/usr/bin/env python3
"""
sort_results.py — sorts every results.csv in the Published/, Unpublished/,
and Deprecated/ trees in-place.

Uses a numeric-aware sort key: integer fields are sorted numerically
(so record 2 < 10) and string fields are sorted lexicographically.
This mirrors the CORE engine's column-order sort while fixing the
alphabetic-vs-numeric ordering issue for Record numbers and similar fields.

Usage:
    python scripts/sort_results.py [--dry-run] [--root <repo_root>]
"""

import argparse
import csv
import sys
from pathlib import Path


def _sort_key(row: list[str]) -> tuple:
    """
    Sort key that matches the engine's column order but sorts numeric fields
    numerically rather than lexicographically.

    Each field becomes (0, int_value) for pure integers or (1, str_value)
    for everything else, so numbers sort before strings and 2 < 10.
    """
    parts = []
    for field in row:
        try:
            parts.append((0, int(field), ""))
        except ValueError:
            parts.append((1, 0, field))
    return tuple(parts)


def sort_csv(path: Path, dry_run: bool) -> bool:
    """Sort a single results.csv in-place. Returns True if the file changed."""
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if len(rows) < 2:
        return False  # header-only or empty — nothing to sort

    header, data = rows[0], rows[1:]
    sorted_data = sorted(data, key=_sort_key)

    if sorted_data == data:
        return False  # already in order

    if not dry_run:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(sorted_data)

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Sort all results.csv files in Published/.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Repository root (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report which files would change without writing",
    )
    args = parser.parse_args()

    search_dirs = [args.root / "Published", args.root / "Unpublished", args.root / "Deprecated"]
    missing = [d for d in search_dirs if not d.is_dir()]
    if missing:
        for d in missing:
            print(f"WARNING: {d} does not exist — skipping", file=sys.stderr)
    search_dirs = [d for d in search_dirs if d.is_dir()]
    if not search_dirs:
        print("ERROR: no search directories found", file=sys.stderr)
        return 1

    changed = []
    unchanged = []
    for search_dir in search_dirs:
        for csv_path in sorted(search_dir.rglob("results.csv")):
            if sort_csv(csv_path, args.dry_run):
                changed.append(csv_path)
                label = "would change" if args.dry_run else "sorted"
                print(f"  {label}: {csv_path.relative_to(args.root)}")
            else:
                unchanged.append(csv_path)

    total = len(changed) + len(unchanged)
    action = "would be sorted" if args.dry_run else "sorted"
    print(f"\n{total} file(s) scanned — {len(changed)} {action}, {len(unchanged)} already in order.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
