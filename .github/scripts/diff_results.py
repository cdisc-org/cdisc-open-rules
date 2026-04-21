"""
diff_results.py — compares a committed results.csv against a freshly generated one.

Usage:
    python .github/scripts/diff_results.py <committed.csv> <generated.csv> <case_label>

Exit codes:
    0  — results match
    1  — results differ (failure)
    2  — error
"""
import csv
import sys
from itertools import zip_longest


def load(path: str) -> list[tuple]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        rows = [tuple(row[col] for col in header) for row in reader]
    return sorted(rows)


def diff(committed_path: str, generated_path: str) -> list[str]:
    diffs = []
    c_rows = load(committed_path)
    g_rows = load(generated_path)

    if len(c_rows) != len(g_rows):
        diffs.append(
            f"Row count changed: {len(c_rows)} committed -> {len(g_rows)} generated"
        )

    _ABSENT = object()
    for i, (c_row, g_row) in enumerate(zip_longest(c_rows, g_rows, fillvalue=_ABSENT), start=1):
        if c_row is _ABSENT:
            diffs.append(f"  Row {i}: present in generated only -> {g_row}")
        elif g_row is _ABSENT:
            diffs.append(f"  Row {i}: present in committed only -> {c_row}")
        elif c_row != g_row:
            diffs.append(f"  Row {i}: committed={c_row} -> generated={g_row}")

    return diffs


def main():
    if len(sys.argv) != 4:
        print(
            f"Usage: {sys.argv[0]} <committed.csv> <generated.csv> <case_label>",
            file=sys.stderr,
        )
        sys.exit(2)

    committed_path, generated_path, case_label = sys.argv[1], sys.argv[2], sys.argv[3]

    try:
        diffs = diff(committed_path, generated_path)
    except Exception as e:
        print(f"ERROR comparing results for {case_label}: {e}", file=sys.stderr)
        sys.exit(2)

    if diffs:
        print(f"DIFF_FOUND for {case_label}:")
        for line in diffs:
            print(line)
        sys.exit(1)
    else:
        print(f"MATCH - results identical for {case_label}")
        sys.exit(0)


if __name__ == "__main__":
    main()
