import csv
import re
from pathlib import Path
import yaml
import argparse
from typing import Optional

CORE_PATTERN = re.compile(r"^CORE-(\d{6})$")

PUBLISHED_DIR = Path("Rules/Published")


def parse_rule(rule_path: Path) -> tuple[Optional[str], list[dict]]:
    """
    Returns (yaml_core_id, standards).

    yaml_core_id is the Core.Id already written in the file, or None if absent.
    standards is the flat list of {name, version, rule_id, rule_version} dicts.
    """
    with open(rule_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    yaml_core_id = None
    core_block = data.get("Core") or {}
    raw_id = str(core_block.get("Id") or "").strip()
    if CORE_PATTERN.match(raw_id):
        yaml_core_id = raw_id

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

    return yaml_core_id, standards


def load_ledger(mappings_dir: Path) -> dict[str, dict[str, str]]:
    """
    Read every *_mappings.csv and return a two-level dict:

        { standard_name: { rule_id: core_id } }

    Only rows with a non-empty CORE-ID are included.
    Standard name is derived from the filename: SDTMIG_mappings.csv -> "SDTMIG".
    """
    ledger: dict[str, dict[str, str]] = {}
    for csv_file in sorted(mappings_dir.glob("*_mappings.csv")):
        std_name = csv_file.stem.replace("_mappings", "")
        ledger[std_name] = {}
        with open(csv_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rule_id = (row.get("Rule ID") or "").strip()
                core_id = (row.get("CORE-ID") or "").strip()
                if rule_id and CORE_PATTERN.match(core_id):
                    ledger[std_name][rule_id] = core_id
    return ledger


def get_next_core_id(mappings_dir: Path, algorithm: str = "max") -> str:
    existing_ids = []
    for csv_file in mappings_dir.glob("*_mappings.csv"):
        with open(csv_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                core = (row.get("CORE-ID") or "").strip()
                m = CORE_PATTERN.match(core)
                if m:
                    existing_ids.append(int(m.group(1)))

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


def collect_ledger_core_ids(
        result: dict,
        ledger: dict,
) -> dict[str, set[tuple[str, str]]]:
    """
    For every (standard, rule_id) pair in *result*, look up whatever
    CORE-ID the ledger already has for that pair.

    Returns:
        { core_id: { (std_name, rule_id), ... } }

    Only CORE-IDs that are actually present in the ledger are included.
    An empty dict means none of the rule_ids have been seen before.
    """
    found: dict[str, set[tuple[str, str]]] = {}
    for (std, rule_id) in result:
        existing = ledger.get(std, {}).get(rule_id)
        if existing:
            found.setdefault(existing, set()).add((std, rule_id))
    return found


def resolve_core_id(
        yaml_core_id: Optional[str],
        result: dict,
        ledger: dict,
        mappings_dir: Path,
        algorithm: str,
) -> str:
    """
    Determine the single CORE-ID to use for this rule, or raise ValueError
    if the yaml and the ledger contradict each other.

    Decision matrix
    ───────────────
    yaml_core_id  │ ledger hits          │ action
    ──────────────┼──────────────────────┼──────────────────────────────────────
    None          │ none                 │ mint a fresh CORE-ID.
    None          │ one unique CORE-ID   │ use that CORE-ID (re-publish).
    None          │ multiple CORE-IDs    │ ERROR – rule_ids are split in ledger.
    present       │ none                 │ ERROR – claimed ID not in any ledger.
    present       │ one, matches yaml    │ use it (clean re-publish).
    present       │ one, differs         │ ERROR – yaml contradicts ledger.
    present       │ multiple             │ ERROR – ledger is inconsistent.
    """
    ledger_hits = collect_ledger_core_ids(result, ledger)

    # No ledger hits
    if not ledger_hits:
        if yaml_core_id is None:
            return get_next_core_id(mappings_dir, algorithm)
        raise ValueError(
            f"rule.yaml declares Core.Id = {yaml_core_id} but that ID does "
            f"not appear in any ledger CSV. Remove it to auto-assign, or fix "
            f"the ledger first."
        )

    # One unique CORE-ID found
    if len(ledger_hits) == 1:
        ledger_core_id = next(iter(ledger_hits))
        if yaml_core_id is None:
            return ledger_core_id
        if yaml_core_id == ledger_core_id:
            return ledger_core_id
        raise ValueError(
            f"rule.yaml declares Core.Id = {yaml_core_id} but the ledger "
            f"has these Rule IDs under {ledger_core_id}. "
            f"Pairs in conflict: {ledger_hits[ledger_core_id]}"
        )

    # Multiple distinct CORE-IDs found
    detail = "; ".join(
        f"{cid} -> {pairs}" for cid, pairs in ledger_hits.items()
    )
    raise ValueError(
        f"Ledger inconsistency: the Rule IDs in this rule.yaml are associated "
        f"with multiple CORE-IDs in the ledger ({detail}). "
        f"Resolve the ledger manually before re-publishing."
    )


def update_csv(
        mapping_file: Path,
        rule_id: str,
        versions: set[str],
        core_id: str,
) -> None:
    """
    Upsert one row for *rule_id* in *mapping_file*.

    *versions* is the plain set of version strings that apply to this
    (standard, rule_id) pair, e.g. {'3.2', '3.3', '3.4'}.

    Version columns that already exist in the CSV are preserved as-is for
    other rows; new version columns from *versions* are appended before
    Status/CORE-ID if they are not already present.
    """
    rows: list[dict] = []
    fieldnames: list[str] = []

    if mapping_file.exists():
        with open(mapping_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)

    existing_ver_cols: list[str] = [
        c for c in fieldnames if c not in ("Rule ID", "Status", "CORE-ID")
    ]

    new_ver_cols = sorted(versions - set(existing_ver_cols))
    all_ver_cols = existing_ver_cols + new_ver_cols
    fieldnames = ["Rule ID"] + all_ver_cols + ["Status", "CORE-ID"]

    row = next((r for r in rows if r.get("Rule ID") == rule_id), {})
    if not row:
        rows.append(row)

    row["Rule ID"] = rule_id
    row["CORE-ID"] = core_id
    row["Status"] = "PUBLISHED"
    for ver in all_ver_cols:
        row[ver] = ver if ver in versions else ""

    with open(mapping_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def update_rule_yaml(core_id: str, rule_path: Path) -> None:
    with open(rule_path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if "Core" not in doc:
        doc["Core"] = {}
    doc["Core"]["Id"] = core_id
    doc["Core"]["Status"] = "Published"
    with open(rule_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, sort_keys=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-dirs", required=True,
                        help="Space-separated rule folders under Rules/Unpublished/")
    parser.add_argument("--algorithm", choices=["min", "max"], default="max",
                        help="CORE-ID assignment algorithm")
    args = parser.parse_args()

    mappings_dir = Path("mappings")
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)

    ledger = load_ledger(mappings_dir)

    for rule_dir in args.new_dirs.split():
        rule_path = Path(rule_dir) / "rule.yaml"
        if not rule_path.exists():
            print(f"[SKIP]  {rule_dir}: no rule.yaml found")
            continue

        print(f"[INFO]  Processing {rule_dir} ...")

        yaml_core_id, standards = parse_rule(rule_path)

        # Group into { (std_name, rule_id): set_of_versions }.
        result: dict[tuple[str, str], set[str]] = {}
        for item in standards:
            key = (item["name"], item["rule_id"])
            result.setdefault(key, set()).add(item["version"])

        # Resolve (or reject) the CORE-ID before touching any file.
        try:
            core_id = resolve_core_id(
                yaml_core_id, result, ledger, mappings_dir, args.algorithm
            )
        except ValueError as exc:
            print(f"[ERROR] {rule_dir}: {exc}")
            print(f"        Skipping — no files were modified.")
            continue

        for (std, rule_id), versions in result.items():
            mapping_file = mappings_dir / f"{std}_mappings.csv"
            update_csv(mapping_file, rule_id, versions, core_id)
            ledger.setdefault(std, {})[rule_id] = core_id

        update_rule_yaml(core_id, rule_path)
        dest = PUBLISHED_DIR / core_id
        Path(rule_dir).rename(dest)
        print(f"[OK]    {rule_dir} -> {dest}  (CORE-ID: {core_id})")


if __name__ == "__main__":
    main()
