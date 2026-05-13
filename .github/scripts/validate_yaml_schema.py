#!/usr/bin/env python3
"""
validate_yaml_schema.py — Validates one or more rule YAML files against the
CDISC CORE JSON Schema (draft/2020-12).

Usage:
    python validate_yaml_schema.py <schema_url_or_path> <rule_file> [<rule_file> ...]

Exit codes:
    0 — all files are valid
    1 — one or more files failed validation or an unexpected error occurred
"""

import json
import sys
import urllib.request
from pathlib import Path

import yaml

try:
    import jsonschema
    from jsonschema import Draft202012Validator, ValidationError
except ImportError:
    print("ERROR: 'jsonschema' package is not installed. Run: pip install 'jsonschema[format-nongpl]'")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_schema(source: str) -> dict:
    """Load JSON schema from a URL or local file path."""
    if source.startswith("http://") or source.startswith("https://"):
        with urllib.request.urlopen(source, timeout=30) as resp:  # noqa: S310
            return json.loads(resp.read())
    return json.loads(Path(source).read_text(encoding="utf-8"))


def validate_file(path: Path, validator: Draft202012Validator) -> list[str]:
    """
    Validate a YAML file against the schema.
    Returns a list of human-readable error strings (empty == valid).
    """
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"YAML parse error: {exc}"]

    if doc is None:
        return ["File is empty or contains only comments."]

    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    return [f"  [{' > '.join(str(p) for p in err.path) or '/'}] {err.message}" for err in errors]


def github_annotation(level: str, file: str, msg: str) -> str:
    """Produce a GitHub Actions workflow command annotation."""
    # Escape special characters per GHA spec
    msg = msg.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return f"::{level} file={file}::{msg}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <schema_url_or_path> <rule_file> [<rule_file> ...]")
        return 1

    schema_source = sys.argv[1]
    rule_files = [Path(p) for p in sys.argv[2:]]

    # Load schema
    print(f"Loading schema from: {schema_source}")
    try:
        schema = load_schema(schema_source)
    except Exception as exc:
        print(f"ERROR: Failed to load schema — {exc}")
        return 1

    validator = Draft202012Validator(schema)

    total = 0
    failed = 0

    report_lines: list[str] = []

    for rule_path in rule_files:
        if not rule_path.exists():
            print(f"WARNING: File not found — {rule_path}")
            continue

        total += 1
        errors = validate_file(rule_path, validator)

        if errors:
            failed += 1
            print(github_annotation("error", str(rule_path), f"Schema validation failed ({len(errors)} error(s))"))
            print(f"❌  {rule_path}")
            for err in errors:
                print(err)
            report_lines.append(f"### ❌ `{rule_path}`\n")
            report_lines.append("```\n" + "\n".join(errors) + "\n```\n")
        else:
            print(f"✅  {rule_path}")
            report_lines.append(f"### ✅ `{rule_path}`\n")

    # Write markdown report (consumed by the workflow)
    report_path = Path("schema_validation_report.md")
    with report_path.open("w", encoding="utf-8") as fh:
        fh.write("# Schema Validation Report\n\n")
        fh.write(f"**Schema:** `{schema_source}`\n\n")
        fh.write(f"**Files checked:** {total} | **Failed:** {failed}\n\n")
        fh.writelines(report_lines)

    print(f"\nSummary: {total - failed}/{total} file(s) passed schema validation.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

