"""
diff_results.py — compares a committed results.json against a freshly generated one.

Usage:
    python .github/scripts/diff_results.py <committed.json> <generated.json> <case_label>

Exit codes:
    0  — results match
    1  — results differ  (not a hard failure; flagged for human review)
    2  — error loading / parsing files
"""

import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def dataset_results(data: dict) -> dict:
    """
    Results JSON is a dict of  dataset_name -> [result_object, ...]
    Returns that dict, or an empty dict if the shape is unexpected.
    """
    if isinstance(data, dict):
        return data
    return {}


def flatten_errors(data: dict) -> list:
    """Normalised flat list of all errors across all datasets, sorted for stable comparison."""
    rows = []
    for ds_name, ds_list in dataset_results(data).items():
        for ds in ds_list:
            for err in ds.get("errors", []):
                rows.append(
                    {
                        "dataset": err.get("dataset", ds_name),
                        "row": err.get("row"),
                        "value": err.get("value") or {},
                    }
                )
    return sorted(
        rows,
        key=lambda r: (
            r["dataset"],
            r["row"] or 0,
            str(sorted(r["value"].items())),
        ),
    )


def error_counts_by_domain(data: dict) -> dict:
    counts = {}
    for ds_name, ds_list in dataset_results(data).items():
        for ds in ds_list:
            key = ds.get("domain") or ds.get("dataset") or ds_name
            counts[key] = len(ds.get("errors", []))
    return counts


def diff(committed: dict, generated: dict) -> list[str]:
    diffs = []

    committed_errors = flatten_errors(committed)
    generated_errors = flatten_errors(generated)

    if len(committed_errors) != len(generated_errors):
        diffs.append(
            f"Total error count changed: "
            f"{len(committed_errors)} committed → {len(generated_errors)} generated"
        )

    # Per-domain counts
    c_counts = error_counts_by_domain(committed)
    g_counts = error_counts_by_domain(generated)
    all_domains = sorted(set(c_counts) | set(g_counts))
    for domain in all_domains:
        c = c_counts.get(domain, 0)
        g = g_counts.get(domain, 0)
        if c != g:
            diffs.append(f"  {domain}: {c} errors committed → {g} generated")

    # Field-level diff on normalised error list
    for i, (c_err, g_err) in enumerate(zip(committed_errors, generated_errors)):
        if c_err == g_err:
            continue
        diffs.append(
            f"  Error {i + 1} "
            f"(dataset={c_err['dataset']}, row={c_err['row']}): value mismatch"
        )
        all_keys = sorted(set(c_err["value"]) | set(g_err["value"]))
        for k in all_keys:
            cv = c_err["value"].get(k, "<absent>")
            gv = g_err["value"].get(k, "<absent>")
            if cv != gv:
                diffs.append(f"    Field '{k}': '{cv}' → '{gv}'")

    return diffs


def main():
    if len(sys.argv) != 4:
        print(
            f"Usage: {sys.argv[0]} <committed.json> <generated.json> <case_label>",
            file=sys.stderr,
        )
        sys.exit(2)

    committed_path, generated_path, case_label = sys.argv[1], sys.argv[2], sys.argv[3]

    try:
        committed = load(committed_path)
        generated = load(generated_path)
    except Exception as e:
        print(f"ERROR loading result files for {case_label}: {e}", file=sys.stderr)
        sys.exit(2)

    diffs = diff(committed, generated)

    if diffs:
        print(f"DIFF_FOUND for {case_label}:")
        for line in diffs:
            print(line)
        sys.exit(1)
    else:
        print(f"MATCH — results identical for {case_label}")
        sys.exit(0)


if __name__ == "__main__":
    main()
