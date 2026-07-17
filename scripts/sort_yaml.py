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
import subprocess
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


def run_prettier(content: str, path: Path) -> str:
    """Format a YAML string through Prettier. `path` is only used so Prettier
    can infer the parser/config (via --stdin-filepath); the file itself is
    not read or written here."""
    try:
        result = subprocess.run(
            ["npx", "--no-install", "prettier", "--stdin-filepath", str(path)],
            input=content,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Prettier not found. Run `npm ci` (or `npm install`) in the repo root first."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Prettier failed on {path}:\n{exc.stderr}") from exc
    return result.stdout


def canonical(content: str, path: Path, format_with_prettier: bool = True) -> str:
    """Return the canonical representation of a YAML string: keys sorted, and
    (unless format_with_prettier is False) passed through Prettier."""
    data = _yaml.load(content)
    if data is None:
        return content
    sorted_data = sort_recursive(data)
    stream = StringIO()
    _yaml.dump(sorted_data, stream)
    result = stream.getvalue()
    if format_with_prettier:
        result = run_prettier(result, path)
    return result


def find_rule_files(root: Path) -> list[Path]:
    """Find all rule.yml files under Published/ and Unpublished/."""
    files = []
    for folder in ("Published", "Unpublished"):
        folder_path = root / folder
        if folder_path.exists():
            files.extend(folder_path.rglob("rule.yml"))
    return sorted(files)


def process_files(files: list[Path], check_mode: bool, format_with_prettier: bool = True) -> int:
    """Format (or check) the given files. Returns exit code."""
    changed = []
    errors = []

    for path in files:
        try:
            original = path.read_text(encoding="utf-8")
            formatted = canonical(original, path, format_with_prettier=format_with_prettier)
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
        "--no-format",
        action="store_true",
        help="Sort keys only; skip the Prettier formatting pass. Doesn't require Node — "
        "intended for the pre-commit hook, where format-on-save already covers styling.",
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

    sys.exit(process_files(files, check_mode=args.check, format_with_prettier=not args.no_format))


if __name__ == "__main__":
    main()
