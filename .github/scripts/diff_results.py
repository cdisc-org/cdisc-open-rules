"""
diff_results.py — compares an actual results.csv against an expected one.

Usage:
    python .github/scripts/diff_results.py <expected.csv> <actual.csv> <case_label>

Exit codes:
    0  — results match
    1  — results differ (failure)
    2  — error
"""

import csv
import sys
from collections import Counter


def load(path: str) -> list[tuple[int, tuple]]:
    """Load CSV rows as (1-based line number, row tuple), preserving original order."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        return [
            (i, tuple(row[col] for col in header))
            for i, row in enumerate(reader, start=1)
        ]


def _filter_unmatched(
    rows: list[tuple[int, tuple]], unmatched: Counter
) -> list[tuple[int, tuple]]:
    """Return rows (in original order) that belong to the unmatched set."""
    remaining_counts = Counter(unmatched)
    result = []
    for lineno, row in rows:
        if remaining_counts[row] > 0:
            result.append((lineno, row))
            remaining_counts[row] -= 1
    return result


def diff(expected_path: str, actual_path: str) -> list[str]:
    exp_rows = load(expected_path)
    act_rows = load(actual_path)

    exp_content = [row for _, row in exp_rows]
    act_content = [row for _, row in act_rows]

    exp_counter = Counter(exp_content)
    act_counter = Counter(act_content)
    matched = exp_counter & act_counter  # rows present in both (min count)

    unmatched_exp = exp_counter - matched  # rows only in expected
    unmatched_act = act_counter - matched  # rows only in actual

    if not unmatched_exp and not unmatched_act:
        if exp_content != act_content:
            return [
                "Row order changed: rows are identical but appear in a different order"
            ]
        return []

    # Rebuild remaining unmatched rows in their original file order.
    remaining_exp = _filter_unmatched(exp_rows, unmatched_exp)
    remaining_act = _filter_unmatched(act_rows, unmatched_act)

    diffs = []
    if len(exp_content) != len(act_content):
        diffs.append(
            f"Row count changed: {len(exp_content)} expected -> {len(act_content)} actual"
        )

    # Merge both unmatched lists by post-filter index; exp before act when tied.
    # Sort key: (post_filter_row, 0=Expected/1=Actual)
    entries = [
        (post_idx, 0, "Expected", src_lineno, row)
        for post_idx, (src_lineno, row) in enumerate(remaining_exp, start=1)
    ] + [
        (post_idx, 1, "Actual", src_lineno, row)
        for post_idx, (src_lineno, row) in enumerate(remaining_act, start=1)
    ]
    entries.sort(key=lambda e: (e[0], e[1]))

    for _, _, label, src_lineno, row in entries:
        diffs.append(f"  [{label:8}] Row {src_lineno}: {row}")

    return diffs


def main():
    if len(sys.argv) != 4:
        print(
            f"Usage: {sys.argv[0]} <expected.csv> <actual.csv> <case_label>",
            file=sys.stderr,
        )
        sys.exit(2)

    expected_path, actual_path, case_label = sys.argv[1], sys.argv[2], sys.argv[3]

    try:
        diffs = diff(expected_path, actual_path)
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
