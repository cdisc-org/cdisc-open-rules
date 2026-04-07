"""
diff_results.py — compares the PR results.json against a freshly generated one.

Usage:
    python .github/scripts/diff_results.py <committed.json> <generated.json> <case_label>

Exit codes:
    0  — results match
    1  — results differ (failure)
    2  — error
"""

import json
import sys


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def extract_issues(data: dict) -> list:
    rows = []
    for issue in data.get("Issue_Details", []):
        rows.append({
            "core_id":       issue.get("core_id"),
            "dataset":       issue.get("dataset"),
            "row":           issue.get("row"),
            "USUBJID":       issue.get("USUBJID"),
            "SEQ":           issue.get("SEQ"),
            "variables":     sorted(issue.get("variables") or []),
            "values":        issue.get("values"),
            "message":       issue.get("message"),
            "executability": issue.get("executability"),
        })
    return sorted(rows, key=lambda r: (
        r["core_id"] or "",
        r["dataset"] or "",
        r["row"] or 0,
        r["USUBJID"] or "",
    ))


def extract_summary(data: dict) -> list:
    rows = []
    for entry in data.get("Issue_Summary", []):
        rows.append({
            "dataset": entry.get("dataset"),
            "core_id": entry.get("core_id"),
            "issues":  entry.get("issues"),
        })
    return sorted(rows, key=lambda r: (r["dataset"] or "", r["core_id"] or ""))


def diff(committed: dict, generated: dict) -> list:
    diffs = []

    c_issues = extract_issues(committed)
    g_issues = extract_issues(generated)
    c_summary = extract_summary(committed)
    g_summary = extract_summary(generated)

    if len(c_issues) != len(g_issues):
        diffs.append(
            f"Issue count changed: {len(c_issues)} committed -> {len(g_issues)} generated"
        )

    if c_summary != g_summary:
        c_map = {(r["dataset"], r["core_id"]): r["issues"] for r in c_summary}
        g_map = {(r["dataset"], r["core_id"]): r["issues"] for r in g_summary}
        all_keys = sorted(set(c_map) | set(g_map))
        for key in all_keys:
            c_val = c_map.get(key, 0)
            g_val = g_map.get(key, 0)
            if c_val != g_val:
                diffs.append(
                    f"  {key[0]} / {key[1]}: {c_val} issue(s) committed -> {g_val} generated"
                )

    for i, (c_issue, g_issue) in enumerate(zip(c_issues, g_issues)):
        if c_issue == g_issue:
            continue
        diffs.append(
            f"  Issue {i + 1} "
            f"(dataset={c_issue['dataset']}, row={c_issue['row']}, "
            f"USUBJID={c_issue['USUBJID']}): mismatch"
        )
        for k in sorted(set(c_issue) | set(g_issue)):
            cv = c_issue.get(k, "<absent>")
            gv = g_issue.get(k, "<absent>")
            if cv != gv:
                diffs.append(f"    Field '{k}': '{cv}' -> '{gv}'")

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
        print(f"MATCH - results identical for {case_label}")
        sys.exit(0)


if __name__ == "__main__":
    main()
