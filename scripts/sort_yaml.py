#!/usr/bin/env python3
"""
Sort rule YAML files alphabetically and recursively by key name, preserving comments.

This matches the auto-sort behavior of the CDISC conformance rules editor.
Prettier formatting is handled separately (via the VS Code extension locally,
or in CI) — this script only handles key sorting.

Check mode (--check) verifies key order structurally, independent of exact
formatting bytes, so it agrees regardless of whether Prettier, ruamel, or an
editor last touched the file's whitespace/quotes/wrapping.

Usage:
    # Sort files in-place (default: all rule.yml under Published/ and Unpublished/)
    python scripts/sort_yaml.py

    # Sort specific files
    python scripts/sort_yaml.py path/to/rule.yml another/rule.yml

    # Check mode: exit with code 1 if any file's keys are not sorted
    python scripts/sort_yaml.py --check [files...]
"""

import sys
import argparse
from io import StringIO
from pathlib import Path

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
except ImportError:
    print("ERROR: ruamel.yaml is not installed. Run: pip install ruamel.yaml", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# YAML round-trip instance (loader + dumper), configured once
# ---------------------------------------------------------------------------

_yaml = YAML(typ="rt")
_yaml.preserve_quotes = True
_yaml.width = 100
_yaml.indent(mapping=2, sequence=2, offset=0)
_yaml.allow_unicode = True


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def sort_recursive(obj):
    """Recursively sort dict keys alphabetically. Lists are preserved as-is."""
    if isinstance(obj, CommentedMap):
        sorted_map = CommentedMap()
        for key in sorted(obj.keys(), key=str):
            sorted_map[key] = sort_recursive(obj[key])
        sorted_map.ca.items.update(obj.ca.items)
        if obj.ca.comment is not None:
            sorted_map.ca.comment = obj.ca.comment
        sorted_map.ca.end = obj.ca.end
        return sorted_map

    if isinstance(obj, CommentedSeq):
        new_seq = CommentedSeq(sort_recursive(item) for item in obj)
        new_seq.ca.items.update(obj.ca.items)
        if obj.ca.comment is not None:
            new_seq.ca.comment = obj.ca.comment
        new_seq.ca.end = obj.ca.end
        return new_seq

    return obj


def is_sorted_recursive(obj) -> bool:
    """Check whether dict keys are already alphabetically sorted at every level.

    This is a structural check on key order only — it says nothing about
    whitespace, quote style, or line wrapping, so it agrees with the file
    regardless of which tool (Prettier, ruamel, an editor) last formatted it.
    """
    if isinstance(obj, CommentedMap):
        keys = list(obj.keys())
        if [str(k) for k in keys] != sorted(str(k) for k in keys):
            return False
        return all(is_sorted_recursive(v) for v in obj.values())

    if isinstance(obj, CommentedSeq):
        return all(is_sorted_recursive(item) for item in obj)

    return True


def canonical(content: str) -> str:
    """Return the canonical (sorted) representation of a YAML string."""
    data = _yaml.load(content)
    if data is None:
        return content
    sorted_data = sort_recursive(data)
    stream = StringIO()
    _yaml.dump(sorted_data, stream)
    return stream.getvalue()


def find_rule_files(root: Path) -> list[Path]:
    """Find all rule.yml files under Published/ and Unpublished/."""
    files = []
    for folder in ("Published", "Unpublished"):
        folder_path = root / folder
        if folder_path.exists():
            files.extend(folder_path.rglob("rule.yml"))
    return sorted(files)


def process_files(files: list[Path], check_mode: bool) -> int:
    """Sort (or check) the given files. Returns exit code."""
    changed = []
    errors = []

    for path in files:
        try:
            original = path.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(f"  {path}: {exc}")
            continue

        if check_mode:
            try:
                data = _yaml.load(original)
            except Exception as exc:
                errors.append(f"  {path}: {exc}")
                continue

            if data is None:
                continue

            if not is_sorted_recursive(data):
                changed.append(path)
        else:
            try:
                formatted = canonical(original)
            except Exception as exc:
                errors.append(f"  {path}: {exc}")
                continue

            if original != formatted:
                changed.append(path)
                path.write_text(formatted, encoding="utf-8")
                print(f"  Sorted: {path}")

    if errors:
        print("\nERROR: Failed to process the following files:", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    if check_mode:
        if changed:
            print(
                "\nThe following rule.yml files are not correctly sorted:\n",
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
            print("All rule.yml files are correctly sorted.")
    else:
        if not changed:
            print("All rule.yml files are already correctly sorted.")

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: exit 1 if any file's keys are not sorted, without modifying files.",
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

    mode = "Checking" if args.check else "Sorting"
    print(f"{mode} {len(files)} rule.yml file(s)...")

    sys.exit(process_files(files, check_mode=args.check))


if __name__ == "__main__":
    main()
