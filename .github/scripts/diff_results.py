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

from tabulate import tabulate


def load(path: str) -> tuple[list[str], list[tuple[int, tuple]]]:
    """Return (header, [(1-based line number, row tuple)]), preserving original order."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        rows = [
            (i, tuple(row[col] for col in header))
            for i, row in enumerate(reader, start=1)
        ]
    return header, rows


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


def _similarity(a: tuple, b: tuple) -> float:
    """Fraction of fields that match between two rows (0.0 – 1.0)."""
    if not a and not b:
        return 1.0
    n = max(len(a), len(b))
    matches = sum(x == y for x, y in zip(a, b))
    return matches / n


def _pair_closest(
    exp_rows: list[tuple[int, tuple]],
    act_rows: list[tuple[int, tuple]],
) -> tuple[
    list[tuple[tuple[int, tuple], tuple[int, tuple]]],  # paired (exp, act)
    list[tuple[int, tuple]],  # unpaired expected
    list[tuple[int, tuple]],  # unpaired actual
]:
    """Greedily pair rows from the smaller side with the closest match on the larger side."""
    exp_is_smaller = len(exp_rows) <= len(act_rows)
    smaller = exp_rows if exp_is_smaller else act_rows
    remaining_larger = list(act_rows if exp_is_smaller else exp_rows)

    pairs: list[tuple[tuple[int, tuple], tuple[int, tuple]]] = []
    unpaired_smaller: list[tuple[int, tuple]] = []

    for item in smaller:
        if not remaining_larger:
            unpaired_smaller.append(item)
            continue
        best_idx = max(
            range(len(remaining_larger)),
            key=lambda i: _similarity(item[1], remaining_larger[i][1]),
        )
        matched = remaining_larger.pop(best_idx)
        pairs.append((item, matched) if exp_is_smaller else (matched, item))

    unpaired_exp = unpaired_smaller if exp_is_smaller else remaining_larger
    unpaired_act = remaining_larger if exp_is_smaller else unpaired_smaller
    return pairs, unpaired_exp, unpaired_act


def diff(expected_path: str, actual_path: str) -> list[str]:
    exp_header, exp_rows = load(expected_path)
    _, act_rows = load(actual_path)

    exp_content = [row for _, row in exp_rows]
    act_content = [row for _, row in act_rows]

    exp_counter = Counter(exp_content)
    act_counter = Counter(act_content)
    matched = exp_counter & act_counter

    unmatched_exp = exp_counter - matched
    unmatched_act = act_counter - matched

    if not unmatched_exp and not unmatched_act:
        if exp_content != act_content:
            return [
                "Row order changed: rows are identical but appear in a different order"
            ]
        return []

    remaining_exp = _filter_unmatched(exp_rows, unmatched_exp)
    remaining_act = _filter_unmatched(act_rows, unmatched_act)

    diffs = []
    if len(exp_content) != len(act_content):
        diffs.append(
            f"Row count changed: {len(exp_content)} expected -> {len(act_content)} actual\n"
        )

    pairs, unpaired_exp, unpaired_act = _pair_closest(remaining_exp, remaining_act)

    table_headers = ["Exp/Act", "Result Row"] + exp_header

    records = []
    for (exp_lineno, exp_row), (act_lineno, act_row) in pairs:
        exp_record = {"Exp/Act": "Expected", "Result Row": str(exp_lineno)}
        act_record = {"Exp/Act": "Actual", "Result Row": str(act_lineno)}
        for col, ev, av in zip(exp_header, exp_row, act_row):
            exp_record[col] = f"**{ev}**" if ev != av and ev != "" else ev
            act_record[col] = f"**{av}**" if ev != av and av != "" else av
        records.append(exp_record)
        records.append(act_record)

    for lineno, row in unpaired_exp:
        record = {"Exp/Act": "Expected only", "Result Row": str(lineno)}
        record.update(zip(exp_header, row))
        records.append(record)

    for lineno, row in unpaired_act:
        record = {"Exp/Act": "Actual only", "Result Row": str(lineno)}
        record.update(zip(exp_header, row))
        records.append(record)

    table = tabulate(
        [[r.get(h, "") for h in table_headers] for r in records],
        headers=table_headers,
        tablefmt="github",
    )
    diffs.append(table)

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
        print(f"### DIFF_FOUND for {case_label}:\n")
        for line in diffs:
            print(line)
        sys.exit(1)
    else:
        print(f"MATCH - results identical for {case_label}")
        sys.exit(0)


if __name__ == "__main__":
    main()
