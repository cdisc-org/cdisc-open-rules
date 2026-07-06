"""
verisian_report.py

Converts Verisian engine JSON output (-of JSON) into the same
`Dataset,Record,Variable,Value` CSV schema used by cdisc-open-rules'
committed results.csv baselines, and compares the two.

Verisian's JSON "Issue_Details" entries look like (from
cdisc_rules_engine/services/reporting/base_report.py):

    {
        "core_id": "CORE-000001",
        "message": "...",
        "executability": "...",
        "dataset": "IE",
        "USUBJID": "...",
        "row": 1,
        "SEQ": "...",
        "variables": ["IECAT", "IEORRES"],
        "values": ["INCLUSION", "Y"],
    }

Each (variable, value) pair inside one Issue_Details entry becomes one row
of Dataset,Record,Variable,Value — "row" maps to "Record".
"""

import csv
import json
from typing import List, Tuple

Row = Tuple[str, str, str, str]  # (Dataset, Record, Variable, Value)


def load_actual_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def issue_details_to_rows(report: dict) -> List[Row]:
    rows: List[Row] = []
    for item in report.get("Issue_Details", []) or []:
        dataset = item.get("dataset", "")
        record = item.get("row", "")
        variables = item.get("variables", []) or []
        values = item.get("values", []) or []
        for variable, value in zip(variables, values):
            rows.append((str(dataset), str(record), str(variable), str(value)))
    return sorted(rows)


def write_rows_csv(rows: List[Row], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Dataset", "Record", "Variable", "Value"])
        writer.writerows(rows)


def read_rows_csv(path: str) -> List[Row]:
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return []
    return sorted(tuple(r) for r in rows[1:] if r)


def diff_rows(expected: List[Row], actual: List[Row]) -> dict:
    expected_set = set(expected)
    actual_set = set(actual)
    return {
        "match": expected_set == actual_set,
        "missing_from_actual": sorted(expected_set - actual_set),
        "unexpected_in_actual": sorted(actual_set - expected_set),
    }
