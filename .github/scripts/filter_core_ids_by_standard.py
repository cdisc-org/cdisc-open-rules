#!/usr/bin/env python3
"""Filter Published CORE rule IDs by Authorities.Standards.Name."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Return space-separated CORE IDs for Published rules matching standards."
    )
    parser.add_argument(
        "--rules-root",
        required=True,
        help="Repository root containing Published/",
    )
    parser.add_argument(
        "--standards",
        nargs="+",
        required=True,
        help="Standards to match from Authorities[].Standards[].Name",
    )
    parser.add_argument(
        "--core-ids",
        default="",
        help="Optional space-separated CORE IDs to intersect with the standard filter.",
    )
    return parser.parse_args()


def iter_published_rule_files(rules_root: Path) -> list[Path]:
    published_dir = rules_root / "Published"
    files: list[Path] = []
    for pattern in ("**/rule.yml", "**/rule.yaml"):
        files.extend(published_dir.glob(pattern))
    return sorted(set(files))


def rule_matches_standard(rule: dict, target_standards: set[str]) -> bool:
    for authority in rule.get("Authorities") or []:
        if not isinstance(authority, dict):
            continue
        for standard in authority.get("Standards") or []:
            if not isinstance(standard, dict):
                continue
            standard_name = str(standard.get("Name") or "").strip().upper()
            if standard_name in target_standards:
                return True
    return False


def collect_filtered_core_ids(rules_root: Path, standards: list[str]) -> list[str]:
    target_standards = {name.strip().upper() for name in standards if name.strip()}
    core_ids: list[str] = []

    for rule_file in iter_published_rule_files(rules_root):
        with rule_file.open("r", encoding="utf-8") as handle:
            rule = yaml.safe_load(handle) or {}
        if not isinstance(rule, dict):
            continue
        if not rule_matches_standard(rule, target_standards):
            continue

        core = rule.get("Core") or {}
        if not isinstance(core, dict):
            continue
        core_id = str(core.get("Id") or "").strip()
        if core_id:
            core_ids.append(core_id)
    return core_ids


def intersect_with_requested(core_ids: list[str], requested_core_ids: str) -> list[str]:
    requested = requested_core_ids.split()
    if not requested:
        return core_ids

    allowed = set(core_ids)
    return [core_id for core_id in requested if core_id in allowed]


def main() -> int:
    args = parse_args()
    rules_root = Path(args.rules_root)
    if not rules_root.is_dir():
        print(f"rules-root does not exist: {rules_root}", file=sys.stderr)
        return 1

    filtered_core_ids = collect_filtered_core_ids(rules_root, args.standards)
    output_core_ids = intersect_with_requested(filtered_core_ids, args.core_ids)
    print(" ".join(output_core_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
