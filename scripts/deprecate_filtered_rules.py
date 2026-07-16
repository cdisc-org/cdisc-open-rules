#!/usr/bin/env python3
"""
Moves CORE-XXXXXX folders from Published/ to Deprecated/ when rule.yml
does not contain the required standards

Usage:
    python deprecate_filtered_rules.py [--dry-run]
"""

import argparse
import shutil
import sys
from pathlib import Path

import jmespath
import yaml

PUBLISHED_DIR = Path("Published")
DEPRECATED_DIR = Path("Deprecated")
REQUIRED_STDS = {"USDM", "TIG"}


def lacks_required_standards(rule_yml: Path) -> bool:
    """Return True if rule.yml has no Authorities.Standards.Name with a value in REQUIRED_STDS."""
    try:
        with rule_yml.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"  [WARN] Could not parse {rule_yml}: {e}")
        return False

    standard_names = jmespath.search("Authorities[].Standards[].Name | []", data) or []
    return not any(name in REQUIRED_STDS for name in standard_names)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without moving anything.",
    )
    args = parser.parse_args()

    if not PUBLISHED_DIR.is_dir():
        print(f"Error: '{PUBLISHED_DIR}' directory not found.")
        sys.exit(1)

    to_move = []
    for rule_dir in sorted(PUBLISHED_DIR.iterdir()):
        if not rule_dir.is_dir():
            continue
        rule_yml = rule_dir / "rule.yml"
        if not rule_yml.exists():
            continue
        if lacks_required_standards(rule_yml):
            to_move.append(rule_dir)

    if not to_move:
        print("No rules found without required standards.")
        return

    print(
        f"{'[DRY RUN] ' if args.dry_run else ''}"
        f"Rules to deprecate (missing required standards, {len(to_move)}):"
    )
    for rule_dir in to_move:
        print(f"  {rule_dir.name}")

    if args.dry_run:
        return

    DEPRECATED_DIR.mkdir(exist_ok=True)
    moved, skipped = 0, 0
    for rule_dir in to_move:
        dest = DEPRECATED_DIR / rule_dir.name
        if dest.exists():
            print(
                f"  [SKIP] {rule_dir.name} — destination already exists in Deprecated/"
            )
            skipped += 1
            continue
        shutil.move(str(rule_dir), str(dest))
        print(f"  Moved {rule_dir.name} → Deprecated/")
        moved += 1

    print(f"\nDone: {moved} moved, {skipped} skipped.")


if __name__ == "__main__":
    main()
