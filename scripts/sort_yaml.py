#!/usr/bin/env python3
"""
Sort and format rule YAML files alphabetically and recursively by key name.

This matches the auto-format/auto-sort behavior of the CDISC conformance rules editor.

Usage:
    # Format files in-place (default: all rule.yml under Published/ and Unpublished/)
    python scripts/sort_yaml.py

    # Format specific files
    python scripts/sort_yaml.py path/to/rule.yml another/rule.yml

    # Check mode: exit with code 1 if any file is not formatted correctly
    python scripts/sort_yaml.py --check [files...]
"""

import sys
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml is not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Custom YAML Dumper
# ---------------------------------------------------------------------------

class _SortedDumper(yaml.Dumper):
    """YAML Dumper that produces consistent, human-readable output."""
    pass


def _str_representer(dumper: yaml.Dumper, data: str):
    """Represent strings: use literal block style for multi-line, plain otherwise.
    Strings that look like YAML scalars (booleans, numbers) are quoted.
    """
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_SortedDumper.add_representer(str, _str_representer)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def sort_recursive(obj):
    """Recursively sort dict keys alphabetically. Lists are preserved as-is."""
    if isinstance(obj, dict):
        return {k: sort_recursive(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, list):
        return [sort_recursive(item) for item in obj]
    return obj


def canonical(content: str) -> str:
    """Return the canonical (sorted + formatted) representation of a YAML string."""
    data = yaml.safe_load(content)
    if data is None:
        return content
    sorted_data = sort_recursive(data)
    return yaml.dump(
        sorted_data,
        Dumper=_SortedDumper,
        default_flow_style=False,
        allow_unicode=True,
        indent=2,
        sort_keys=False,  # we already sorted manually
        width=100,
    )


def find_rule_files(root: Path) -> list[Path]:
    """Find all rule.yml files under Published/ and Unpublished/."""
    files = []
    for folder in ("Published", "Unpublished"):
        folder_path = root / folder
        if folder_path.exists():
            files.extend(folder_path.rglob("rule.yml"))
    return sorted(files)


def process_files(files: list[Path], check_mode: bool) -> int:
    """Format (or check) the given files. Returns exit code."""
    changed = []
    errors = []

    for path in files:
        try:
            original = path.read_text(encoding="utf-8")
            formatted = canonical(original)
        except Exception as exc:
            errors.append(f"  {path}: {exc}")
            continue

        if original != formatted:
            changed.append(path)
            if not check_mode:
                path.write_text(formatted, encoding="utf-8")
                print(f"  Formatted: {path}")

    if errors:
        print("\nERROR: Failed to process the following files:", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    if check_mode:
        if changed:
            print(
                "\nThe following rule.yml files are not correctly sorted/formatted:\n",
                file=sys.stderr,
            )
            for p in changed:
                print(f"  {p}", file=sys.stderr)
            print(
                "\nRun `python scripts/sort_yaml.py` to fix them automatically.",
                file=sys.stderr,
            )
            return 1
        else:
            print("All rule.yml files are correctly sorted and formatted.")
    else:
        if not changed:
            print("All rule.yml files are already correctly sorted and formatted.")

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: exit 1 if any file needs formatting, without modifying files.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="rule.yml files to process. Defaults to all rule.yml files under Published/ and Unpublished/.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    if args.files:
        files = [p.resolve() for p in args.files]
    else:
        files = find_rule_files(repo_root)

    if not files:
        print("No rule.yml files found.")
        return 0

    mode = "Checking" if args.check else "Formatting"
    print(f"{mode} {len(files)} rule.yml file(s)...")

    sys.exit(process_files(files, check_mode=args.check))


if __name__ == "__main__":
    main()


