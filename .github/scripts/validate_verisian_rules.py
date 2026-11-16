#!/usr/bin/env python3
"""
validate_verisian_rules.py

Runs the Verisian fork of the CDISC Rules Engine against every applicable
rule + test case in cdisc-open-rules' Published/ folder, and compares the
actual output against the committed results.csv baselines.

Only rules whose `Authorities` block includes at least one of:
    Organization: CDISC, Standard: SDTMIG
    Organization: FDA,   Standard: SDTMIG
are run (see lib/rule_filter.py).

For each qualifying rule's positive/negative test cases:
    1. Convert the CSV+.env fixture into the single-xlsx dataset format
       Verisian's engine expects (lib/csv_to_excel_dataset.py).
    2. Run `core.py validate` against that Excel file with the rule loaded
       via -lr, output format JSON.
    3. Convert the JSON output's Issue_Details into the same
       Dataset,Record,Variable,Value CSV schema as the committed
       results.csv (lib/verisian_report.py), and diff the two.

Writes:
    <output-dir>/summary_table.md   - one row per rule
    <output-dir>/detail_report.md   - full diff detail for every non-passing case
    <output-dir>/actual_results/... - the converted actual.csv for every case run (artifact)

Exits non-zero if any case FAILed or ERRORed.
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from tabulate import tabulate


from rule_filter import find_matching_rule_dirs  # noqa: E402
from csv_to_excel_dataset import convert_test_case_to_excel, ConversionError  # noqa: E402
from verisian_report import (  # noqa: E402
    load_actual_json,
    issue_details_to_rows,
    write_rows_csv,
    read_rows_csv,
    diff_rows,
)

TEST_TYPES = ("positive", "negative")


def get_test_cases(rule_dir: Path):
    """Yields (test_type, case_dir) for every case that has a data/ folder."""
    for test_type in TEST_TYPES:
        type_dir = rule_dir / test_type
        if not type_dir.is_dir():
            continue
        for case_dir in sorted(p for p in type_dir.iterdir() if p.is_dir()):
            if (case_dir / "data").is_dir():
                yield test_type, case_dir


def run_engine_validate(
    python_cmd: str,
    engine_dir: Path,
    rule_yml: Path,
    dataset_xlsx: Path,
    output_path: Path,
    env: dict,
) -> tuple[bool, str]:
    if "PRODUCT" not in env or "VERSION" not in env:
        return False, ".env missing PRODUCT and/or VERSION"

    cmd = [
        python_cmd,
        "core.py",
        "validate",
        "-s",
        env["PRODUCT"].lower(),
        "-v",
        env["VERSION"],
        "-dp",
        str(dataset_xlsx.resolve()),
        "-lr",
        str(rule_yml.resolve()),
        "-of",
        "JSON",
        "-o",
        str(output_path.resolve()),
        "-p",
        "disabled",
        "-l",
        "disabled",
    ]
    if env.get("SUBSTANDARD"):
        cmd += ["-ss", env["SUBSTANDARD"]]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(engine_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return False, "engine validate call timed out after 300s"
    except Exception as e:
        return False, f"failed to invoke engine: {e}"

    json_path = Path(str(output_path) + ".json")
    if result.returncode != 0 or not json_path.is_file():
        tail = (result.stdout or "") + "\n" + (result.stderr or "")
        return False, tail.strip()[-4000:]
    return True, ""


def run_case(python_cmd: str, engine_dir: Path, rule_yml: Path, case_dir: Path, actual_out_dir: Path) -> dict:
    """
    Runs one test case end-to-end. Returns a result dict with keys:
        status: PASS | FAIL | ERROR | SKIPPED
        message: human-readable detail (empty for PASS)
        diff: dict from diff_rows(), only present for FAIL
    """
    data_dir = case_dir / "data"
    expected_csv = case_dir / "results" / "results.csv"

    if not expected_csv.is_file():
        return {"status": "SKIPPED", "message": f"no expected results.csv at {expected_csv}"}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        dataset_xlsx = tmp_path / "dataset.xlsx"
        try:
            env = convert_test_case_to_excel(str(data_dir), str(dataset_xlsx))
        except ConversionError as e:
            return {"status": "ERROR", "message": f"preprocessing failed: {e}"}

        output_path = tmp_path / "actual"
        ok, message = run_engine_validate(python_cmd, engine_dir, rule_yml, dataset_xlsx, output_path, env)
        if not ok:
            return {"status": "ERROR", "message": f"engine run failed: {message}"}

        try:
            report = load_actual_json(str(output_path) + ".json")
            actual_rows = issue_details_to_rows(report)
        except Exception as e:
            return {"status": "ERROR", "message": f"could not parse engine JSON output: {e}"}

        actual_out_dir.mkdir(parents=True, exist_ok=True)
        write_rows_csv(actual_rows, str(actual_out_dir / "actual.csv"))

        expected_rows = read_rows_csv(str(expected_csv))
        diff = diff_rows(expected_rows, actual_rows)
        if diff["match"]:
            return {"status": "PASS", "message": ""}
        return {"status": "FAIL", "message": "actual output does not match expected results.csv", "diff": diff}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules-root", required=True, help="Path to cdisc-open-rules checkout")
    parser.add_argument("--engine-dir", required=True, help="Path to verisianHQ/cdisc-rules-engine checkout")
    parser.add_argument("--python-cmd", required=True, help="Python executable to run core.py with")
    parser.add_argument("--output-dir", required=True, help="Where to write reports and actual results")
    parser.add_argument(
        "--core-ids",
        nargs="*",
        default=None,
        help="Restrict to these rule IDs (space-separated). Still subject to the Authorities filter.",
    )
    args = parser.parse_args()

    rules_root = Path(args.rules_root)
    engine_dir = Path(args.engine_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    published_root = rules_root / "Published"
    matching_dirs = list(find_matching_rule_dirs(published_root))
    if args.core_ids:
        wanted = set(args.core_ids)
        matching_dirs = [d for d in matching_dirs if d.name in wanted]

    summary_rows = []
    detail_sections = []
    any_failure = False

    for rule_dir in matching_dirs:
        rule_id = rule_dir.name
        rule_yml = rule_dir / "rule.yml"

        case_results = []
        for test_type, case_dir in get_test_cases(rule_dir):
            case_label = f"{test_type}/{case_dir.name}"
            actual_out_dir = output_dir / "actual_results" / rule_id / test_type / case_dir.name
            result = run_case(args.python_cmd, engine_dir, rule_yml, case_dir, actual_out_dir)
            case_results.append((case_label, result))

            if result["status"] in ("FAIL", "ERROR"):
                any_failure = True
                detail = [f"### {rule_id} — {case_label} — {result['status']}", "", result["message"]]
                if "diff" in result:
                    diff = result["diff"]
                    if diff["missing_from_actual"]:
                        detail.append("\n**Expected but missing from actual output:**")
                        detail += [f"- {row}" for row in diff["missing_from_actual"]]
                    if diff["unexpected_in_actual"]:
                        detail.append("\n**Present in actual output but not expected:**")
                        detail += [f"- {row}" for row in diff["unexpected_in_actual"]]
                detail_sections.append("\n".join(detail))

        if not case_results:
            status = "NO TEST CASES"
        elif all(r["status"] == "PASS" for _, r in case_results):
            status = "PASS"
        elif any(r["status"] == "ERROR" for _, r in case_results):
            status = "ERROR"
        else:
            status = "FAIL"

        passed = sum(1 for _, r in case_results if r["status"] == "PASS")
        summary_rows.append([rule_id, status, f"{passed}/{len(case_results)}"])

    summary_table = tabulate(summary_rows, headers=["Core ID", "Status", "Cases Passed"], tablefmt="github")
    (output_dir / "summary_table.md").write_text(
        f"# Verisian Engine Validation Summary\n\n"
        f"Rules evaluated (matching CDISC/FDA SDTMIG Authorities filter): {len(matching_dirs)}\n\n"
        f"{summary_table}\n",
        encoding="utf-8",
    )

    detail_report = "\n\n---\n\n".join(detail_sections) if detail_sections else "All cases passed — no details to show."
    (output_dir / "detail_report.md").write_text(
        f"# Verisian Engine Validation — Detail Report\n\n{detail_report}\n",
        encoding="utf-8",
    )

    print(summary_table)
    sys.exit(1 if any_failure else 0)


if __name__ == "__main__":
    main()
