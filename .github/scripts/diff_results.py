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
from collections import Counter, defaultdict, deque


def load(path: str) -> list[tuple[int, tuple]]:
    """Load CSV rows as (1-based line number, row tuple), preserving original order."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        return [
            (i, tuple(row[col] for col in header))
            for i, row in enumerate(reader, start=1)
        ]


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

    # Build per-content queues of line numbers; consume matched rows first
    # so remaining entries represent the truly unmatched lines.
    exp_linenos: dict[tuple, deque[int]] = defaultdict(deque)
    for lineno, row in exp_rows:
        exp_linenos[row].append(lineno)

    act_linenos: dict[tuple, deque[int]] = defaultdict(deque)
    for lineno, row in act_rows:
        act_linenos[row].append(lineno)

    for row, count in matched.items():
        for _ in range(count):
            exp_linenos[row].popleft()
            act_linenos[row].popleft()

    diffs = []
    if len(exp_content) != len(act_content):
        diffs.append(
            f"Row count changed: {len(exp_content)} expected -> {len(act_content)} actual"
        )

    for row in sorted(unmatched_exp):
        for _ in range(unmatched_exp[row]):
            lineno = exp_linenos[row].popleft()
            diffs.append(f"  Expected row {lineno} not found in actual: {row}")

    for row in sorted(unmatched_act):
        for _ in range(unmatched_act[row]):
            lineno = act_linenos[row].popleft()
            diffs.append(f"  Actual row {lineno} not found in expected: {row}")

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
