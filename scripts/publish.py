import csv
import re
from pathlib import Path
import yaml
import argparse

CORE_PATTERN = re.compile(r"^CORE-(\d{6})$")


def parse_rule(rule_path: Path):
    with open(rule_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    standards = []

    for auth in data.get("Authorities", []):
        for std in auth.get("Standards", []):
            name = std.get("Name")
            rule_id = None
            rule_ver = None

            refs = std.get("References", [])
            if refs:
                rid_info = refs[0].get("Rule Identifier")
                if rid_info:
                    rule_id = rid_info.get("Id")
                    rule_ver = rid_info.get("Version")

            std_version = str(std.get("Version"))

            standards.append(
                {
                    "name": name,
                    "version": std_version,
                    "rule_id": rule_id,
                    "rule_version": rule_ver,
                }
            )

    return standards


def get_next_core_id(mappings_dir: Path, algorithm="max"):
    existing_ids = []

    for file in mappings_dir.glob("*_mappings.csv"):
        with open(file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                core = row.get("CORE-ID", "").strip()
                match = CORE_PATTERN.match(core)
                if match:
                    existing_ids.append(int(match.group(1)))

    existing_ids.sort()

    if algorithm == "min":
        next_id = 1
        for eid in existing_ids:
            if eid != next_id:
                break
            next_id += 1
    else:
        next_id = max(existing_ids, default=0) + 1

    return f"CORE-{next_id:06d}"


def _get_field_names(grouped_standard):
    all_versions = set(grouped_standard.keys()) - {'rule_id', 'name'}
    version_columns = sorted(all_versions)
    fieldnames = ["Rule ID"] + version_columns + ["Status", "CORE-ID"]
    return fieldnames


def update_csv(mapping_file: Path, grouped_standard: dict, core_id: str) -> str:
    rows = []
    fieldnames = []
    if mapping_file.exists():
        with open(mapping_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                rows.append(row)
    if not fieldnames:
        fieldnames = _get_field_names(grouped_standard)
    row = next((x for x in rows if x.get('Rule ID') == grouped_standard['rule_id']), {})
    if not row:
        rows.append(row)
    row.update({col: grouped_standard.get(col) for col in set(fieldnames) - {"Status", "CORE-ID"}})
    row["Rule ID"] = grouped_standard['rule_id']
    row["CORE-ID"] = row.get("CORE-ID") or core_id
    row["Status"] = "PUBLISHED"

    with open(mapping_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return row.get("CORE-ID")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-dirs", required=True, help="Папки правил через пробел")
    parser.add_argument(
        "--algorithm", choices=["min", "max"], default="max", help="Алгоритм CORE-ID"
    )
    args = parser.parse_args()

    mappings_dir = Path("mappings")

    for rule_dir in args.new_dirs.split():
        rule_path = Path(rule_dir) / "rule.yaml"
        if not rule_path.exists():
            continue
        standards = parse_rule(rule_path)

        core_id = get_next_core_id(mappings_dir, args.algorithm)

        result = {}
        for item in standards:
            key = (item['name'], item['rule_id'])
            if key not in result:
                result[key] = {
                    'name': item['name'],
                    'rule_id': item['rule_id']
                }

            result[key][item['version']] = item['version']

        actual_core_id = core_id
        for (std, rule_id), versions in result.items():
            mapping_file = mappings_dir / f"{std}_mappings.csv"
            actual_core_id = update_csv(mapping_file, versions, core_id)

        update_rule_yaml(actual_core_id, rule_path)

        new_path = Path(actual_core_id)
        Path(rule_dir).rename(new_path)


def update_rule_yaml(actual_core_id: str, rule_path: Path):
    with open(rule_path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if "Core" not in doc:
        doc["Core"] = {}
    doc["Core"]["Id"] = actual_core_id
    doc["Core"]["Status"] = "Published"
    with open(rule_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, sort_keys=False)


if __name__ == "__main__":
    main()
