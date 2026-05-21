"""
convert_results.py — converts a CORE engine JSON results file to results.csv.

Non-USDM output (Issue_Details has dataset/row/variables/values):
    CSV columns: Dataset, Record, Variable, Value
    One row per variable/value pair per issue.

USDM output (Issue_Details has path/attributes/values):
    CSV columns: Path, Attribute, Value
    One row per attribute/value pair per issue.

Usage:
    python convert_results.py <results.json> <results.csv>

Exit codes:
    0 — success
    1 — error
"""
import csv
import json
import sys


def detect_standard(data: dict) -> str:
    return data.get("Conformance_Details", {}).get("Standard", "").upper()


def convert_non_usdm(issue_details: list) -> tuple[list[str], list[tuple]]:
    header = ["Dataset", "Record", "Variable", "Value"]
    rows = []
    for issue in issue_details:
        dataset   = issue.get("dataset", "")
        record    = str(issue.get("row", ""))
        variables = issue.get("variables") or []
        values    = issue.get("values") or []
        for variable, value in zip(variables, values):
            rows.append((dataset, record, variable, str(value)))
    return header, rows


def convert_usdm(issue_details: list) -> tuple[list[str], list[tuple]]:
    header = ["path", "attribute", "value"]
    rows = []
    for issue in issue_details:
        path       = issue.get("path") or ""
        attributes = issue.get("attributes") or []
        values     = issue.get("values") or []
        # attributes/values may be a plain string on error-type issues
        if isinstance(attributes, str):
            attributes = [attributes]
        if isinstance(values, str):
            values = [values]
        for attribute, value in zip(attributes, values):
            rows.append((path, attribute, str(value)))
    return header, rows


def convert(json_path: str, csv_path: str) -> None:
    with open(json_path) as f:
        data = json.load(f)

    standard = detect_standard(data)
    issue_details = data.get("Issue_Details", [])

    if standard == "USDM":
        header, rows = convert_usdm(issue_details)
    else:
        header, rows = convert_non_usdm(issue_details)

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {csv_path}")


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <results.json> <results.csv>", file=sys.stderr)
        sys.exit(1)

    json_path, csv_path = sys.argv[1], sys.argv[2]

    try:
        convert(json_path, csv_path)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()