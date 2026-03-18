import csv
import re
import shutil
from pathlib import Path
import yaml
import argparse

CORE_PATTERN = re.compile(r"^CORE-(\d{6})$")


def find_rule_file(rule_dir: Path) -> Path | None:
    """Return the rule file path, supporting both .yaml and .yml extensions."""
    for name in ("rule.yaml", "rule.yml"):
        candidate = rule_dir / name
        if candidate.exists():
            return candidate
    return None


def parse_rule(rule_path: Path) -> list[dict]:
    """
    Parse a rule file and return a flat list of standard entries.

    Each entry contains:
        name       – standard name  (e.g. "SDTMIG")
        version    – standard version string  (e.g. "3.4")
        rule_id    – Rule Identifier Id  (e.g. "CG0001")
        rule_version – Rule Identifier Version (may be None)
        organization – raw Organization string from the authority block
    """
    with open(rule_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    standards = []

    for auth in data.get("Authorities", []):
        org = str(auth.get("Organization") or "").strip()
        for std in auth.get("Standards", []):
            name = std.get("Name")
            std_version = str(std.get("Version", ""))

            for ref in std.get("References", []):
                rid_info = ref.get("Rule Identifier") or {}
                rule_id = rid_info.get("Id")
                rule_ver = rid_info.get("Version")

                if rule_id:
                    standards.append(
                        {
                            "name": name,
                            "version": std_version,
                            "rule_id": rule_id,
                            "rule_version": rule_ver,
                            "organization": org,
                        }
                    )

    return standards


# ---------------------------------------------------------------------------
# CORE-ID allocation  (uses mappings/ CSVs as the source of truth)
# ---------------------------------------------------------------------------

def get_next_core_id(mappings_dir: Path, algorithm: str = "max") -> str:
    """
    Scan all *_mappings.csv files in mappings_dir to find the highest
    (or lowest gap) CORE-ID and return the next available one.
    """
    existing_ids: list[int] = []

    for csv_file in mappings_dir.glob("*_mappings.csv"):
        try:
            with open(csv_file, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    core = row.get("CORE-ID", "").strip()
                    match = CORE_PATTERN.match(core)
                    if match:
                        existing_ids.append(int(match.group(1)))
        except Exception as e:
            print(e)  # skip unreadable files gracefully

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


def _version_sort_key(v: str) -> list:
    """Numeric-aware sort key so 3.2 < 3.3 < 3.4 < 3.10."""
    parts = []
    for x in v.split("."):
        try:
            parts.append((0, int(x)))
        except ValueError:
            parts.append((1, x))
    return parts


def _get_fieldnames(existing_fieldnames: list[str], new_versions: set[str]) -> list[str]:
    """
    Merge existing version columns with any new ones and return the full
    ordered fieldnames list: [Rule ID, ...versions..., Status, CORE-ID].
    """
    current_versions = set(existing_fieldnames) - {"Rule ID", "Status", "CORE-ID"}
    all_versions = sorted(current_versions | new_versions, key=_version_sort_key)
    return ["Rule ID"] + all_versions + ["Status", "CORE-ID"]


def update_csv(mapping_file: Path, rule_id: str, versions: set[str], core_id: str) -> str:
    """
    Upsert a single rule row into the mapping CSV.

    - If the rule_id already exists, update its version columns and keep the
      existing CORE-ID (a rule can only have one CORE-ID).
    - If it is new, append it and assign core_id.
    - Returns the actual CORE-ID that ended up in the row.
    """
    rows: list[dict] = []
    existing_fieldnames: list[str] = []

    if mapping_file.exists():
        with open(mapping_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            existing_fieldnames = list(reader.fieldnames or [])
            rows = list(reader)

    fieldnames = _get_fieldnames(existing_fieldnames, versions)

    row = next((r for r in rows if r.get("Rule ID") == rule_id), None)
    if row is None:
        row = {}
        rows.append(row)

    row["Rule ID"] = rule_id
    row["CORE-ID"] = row.get("CORE-ID") or core_id
    row["Status"] = "PUBLISHED"
    for ver in versions:
        row[ver] = ver  # mark the version as applicable

    # Ensure all version columns exist in every row (fill blanks for old rows)
    for r in rows:
        for fn in fieldnames:
            r.setdefault(fn, "")

    mapping_file.parent.mkdir(parents=True, exist_ok=True)
    with open(mapping_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return row["CORE-ID"]


def update_rule_yaml(core_id: str, rule_path: Path) -> None:
    with open(rule_path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if "Core" not in doc:
        doc["Core"] = {}
    doc["Core"]["Id"] = core_id
    doc["Core"]["Status"] = "Published"
    with open(rule_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish rules into the Published/ tree.")
    parser.add_argument(
        "--new-dirs",
        required=True,
        help="Space-separated list of new rule directories (e.g. Unpublished/SDTMIG/my-rule)",
    )
    parser.add_argument(
        "--algorithm",
        choices=["min", "max"],
        default="max",
        help="CORE-ID allocation algorithm (default: max)",
    )
    args = parser.parse_args()

    mappings_dir = Path("mappings")
    mappings_dir.mkdir(exist_ok=True)

    published_root = Path("Published")

    for rule_dir_str in args.new_dirs.split():
        rule_dir = Path(rule_dir_str)

        rule_path = find_rule_file(rule_dir)
        if rule_path is None:
            print(f"[SKIP] No rule.yaml / rule.yml found in {rule_dir}")
            continue

        parts = rule_dir.parts
        if len(parts) < 2 or parts[0].lower() != "unpublished":
            print(f"[SKIP] {rule_dir} is not under Unpublished/<Standard>/")
            continue
        standard_from_path = parts[1]

        try:
            standards = parse_rule(rule_path)
        except Exception as exc:
            print(f"[ERROR] Could not parse {rule_path}: {exc}")
            continue

        if not standards:
            print(f"[WARN] No standard entries found in {rule_path}")

        core_id = get_next_core_id(mappings_dir, args.algorithm)

        grouped: dict[tuple[str, str], dict] = {}
        for item in standards:
            key = (item["name"], item["rule_id"])
            if key not in grouped:
                grouped[key] = {"versions": set(), "organization": item["organization"]}
            grouped[key]["versions"].add(item["version"])

        actual_core_id = core_id
        for (std_name, rule_id), info in grouped.items():
            mapping_file = mappings_dir / f"{std_name}_mappings.csv"
            actual_core_id = update_csv(mapping_file, rule_id, info["versions"], core_id)

            # FDA Business Rules bucket: org==FDA and rule_id starts with "FB"
            if info["organization"].upper() == "FDA" and rule_id.upper().startswith("FB"):
                fda_mapping = mappings_dir / "FDA Business Rules_mappings.csv"
                update_csv(fda_mapping, rule_id, info["versions"], actual_core_id)

        update_rule_yaml(actual_core_id, rule_path)

        # Move folder: Rules/Unpublished/<Std>/X  →  Rules/Published/<Std>/CORE-ID ─
        dest = published_root / standard_from_path / actual_core_id
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            print(f"[WARN] Destination already exists, skipping move: {dest}")
        else:
            shutil.move(str(rule_dir), str(dest))
            print(f"[OK] {rule_dir}  →  {dest}  (CORE-ID: {actual_core_id})")


if __name__ == "__main__":
    main()
