#!/usr/bin/env python3
"""
generate_mappings.py

Walks ALL rule.yml files under Published/ and Unpublished/ (regardless of
which standard folder they live in) and produces one mapping CSV per
standard found in the YAML content, e.g.:

    mappings/SDTMIG_mapping.csv
    mappings/SENDIG_mapping.csv
    mappings/TIG_mapping.csv
    ...

Usage:
    python generate_mappings.py <root_dir>

    <root_dir> is the directory containing Published/ and Unpublished/.
    Output CSVs are written to <root_dir>/mappings/.
"""

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path


def get_yaml():
    try:
        from ruamel.yaml import YAML
        return YAML
    except ImportError:
        print("ruamel.yaml is required. Install with: pip install ruamel.yaml")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

def get_core_id(data: dict) -> str:
    """Return Core.Id if published, otherwise empty string."""
    core = data.get("Core") or {}
    status = str(core.get("Status") or "").strip().lower()
    if status == "published":
        return str(core.get("Id") or "").strip()
    return ""


def get_status(data: dict) -> str:
    core = data.get("Core") or {}
    return str(core.get("Status") or "DRAFT").strip().upper()


def extract_by_standard(data: dict) -> dict[str, dict[str, set[str]]]:
    """
    Walk all Authorities -> Standards -> References and return:

        { standard_name: { rule_id: {version, ...} } }

    Each standard name gets its own dict of rule_id -> set of versions.
    A single rule.yml can contribute to multiple standards.

    Additionally, if Organization is FDA and a Rule Identifier Id starts
    with "FB", that rule is also bucketed under "FDA Business Rules".
    """
    result: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    authorities = data.get("Authorities") or []
    for authority in authorities:
        if not isinstance(authority, dict):
            continue
        org = str(authority.get("Organization") or "").strip().upper()
        is_fda = org == "FDA"
        for standard in (authority.get("Standards") or []):
            if not isinstance(standard, dict):
                continue
            std_name = str(standard.get("Name") or "").strip().upper()
            if not std_name:
                continue
            version = str(standard.get("Version") or "").strip()
            for ref in (standard.get("References") or []):
                if not isinstance(ref, dict):
                    continue
                rule_id_block = (
                    ref.get("Rule Identifier")
                    or ref.get("Rule_Identifier")
                    or ref.get("rule_identifier")
                    or {}
                )
                if isinstance(rule_id_block, dict):
                    rid = str(rule_id_block.get("Id") or "").strip()
                    if rid:
                        result[std_name][rid].add(version)
                        # Also bucket FB-prefixed rules under "FDA BUSINESS RULES"
                        if is_fda and rid.upper().startswith("FB"):
                            result["FDA BUSINESS RULES"][rid].add(version)

    return result


# ---------------------------------------------------------------------------
# Flat file walker
# ---------------------------------------------------------------------------

def collect_all_rule_files(root: Path) -> list[Path]:
    """
    Recursively find every .yml/.yaml file under Published/ and Unpublished/.
    The folder a file lives in does NOT affect which standard CSV it feeds —
    that is determined entirely by the YAML content.
    """
    files: list[Path] = []
    for status_dir in ["Published", "Unpublished"]:
        status_path = root / status_dir
        if not status_path.is_dir():
            continue
        for pattern in ("*.yml", "*.yaml"):
            files.extend(status_path.rglob(pattern))
    return sorted(set(files))


# ---------------------------------------------------------------------------
# Accumulate rows per standard
# ---------------------------------------------------------------------------

def build_standard_rows(rule_files: list[Path]) -> dict[str, list[dict]]:
    """
    Parse every rule file and accumulate rows keyed by standard name.

    Returns:
        { standard_name: [ {rule_id, versions, status, core_id}, ... ] }

    """
    accumulator: dict[str, dict[str, dict]] = defaultdict(dict)
    yaml = get_yaml()()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    for rule_file in rule_files:
        raw = rule_file.read_text(encoding="utf-8")
        try:
            data = yaml.load(raw)
        except Exception as exc:
            print(f"  [WARN] Could not parse {rule_file}: {exc}")
            continue
        if not isinstance(data, dict):
            continue

        core_id = get_core_id(data)
        status = get_status(data)
        by_standard = extract_by_standard(data)

        for std_name, rule_id_versions in by_standard.items():
            for rid, versions in rule_id_versions.items():
                if rid not in accumulator[std_name]:
                    accumulator[std_name][rid] = {
                        "rule_id": rid,
                        "versions": set(),
                        "status": status,
                        "core_id": core_id,
                    }
                accumulator[std_name][rid]["versions"].update(versions)

    def _rule_id_sort_key(r: dict) -> tuple:
        m = re.match(r'^([A-Za-z]*)(\d+)(.*)', r["rule_id"])
        if m:
            return (m.group(1).upper(), int(m.group(2)), m.group(3))
        return (r["rule_id"].upper(), 0, "")

    return {
        std: sorted(rows.values(), key=_rule_id_sort_key)
        for std, rows in accumulator.items()
    }


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------

def write_csv(rows: list[dict], output_path: Path) -> None:
    if not rows:
        return

    def _version_key(v: str) -> list:
        parts = []
        for x in v.split("."):
            try:
                parts.append((0, int(x)))
            except ValueError:
                parts.append((1, x))
        return parts

    all_versions: list[str] = sorted(
        {v for r in rows for v in r["versions"] if v},
        key=_version_key,
    )

    fieldnames = ["Rule ID"] + all_versions + ["Status", "CORE-ID"]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out: dict = {
                "Rule ID": row["rule_id"],
                "Status": row["status"],
                "CORE-ID": row["core_id"],
            }
            for ver in all_versions:
                out[ver] = ver if ver in row["versions"] else ""
            writer.writerow(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: python {Path(__file__).name} <root_dir>")
        sys.exit(1)

    root = Path(sys.argv[1]).expanduser().resolve()
    if not root.is_dir():
        print(f"Error: '{root}' is not a directory.")
        sys.exit(1)

    mappings_dir = root / "mappings"
    mappings_dir.mkdir(exist_ok=True)

    rule_files = collect_all_rule_files(root)
    if not rule_files:
        print("No .yml/.yaml files found under Published/ or Unpublished/.")
        sys.exit(0)

    print(f"Found {len(rule_files)} rule file(s). Building mappings...")

    rows_by_standard = build_standard_rows(rule_files)

    for std_name, rows in sorted(rows_by_standard.items()):
        out_path = mappings_dir / f"{std_name}_mapping.csv"
        write_csv(rows, out_path)

    print(f"Done. CSVs written to '{mappings_dir}'.")


if __name__ == "__main__":
    main()
