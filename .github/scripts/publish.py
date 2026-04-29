import csv
import re
import sys
from pathlib import Path
import argparse

CORE_PATTERN = re.compile(r"^CORE-(\d{6})$")
PUBLISHED_DIR = Path("Published")


def get_yaml():
    try:
        from ruamel.yaml import YAML
        return YAML
    except ImportError:
        print("ruamel.yaml is required. Install with: pip install ruamel.yaml")
        sys.exit(1)


def get_next_core_id(mappings_dir: Path, algorithm="max"):
    existing_ids = []

    for file in mappings_dir.glob("*_mapping.csv"):
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


def update_rule_yaml(core_id: str, rule_path: Path):
    yaml = get_yaml()()
    with open(rule_path, encoding="utf-8") as f:
        doc = yaml.load(f)
    if "Core" not in doc:
        doc["Core"] = {}
    doc["Core"]["Id"] = core_id
    doc["Core"]["Status"] = "Published"
    with open(rule_path, "w", encoding="utf-8") as f:
        yaml.dump(doc, f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-dirs", required=True, help="Space-separated rule directories to publish")
    parser.add_argument(
        "--algorithm", choices=["min", "max"], default="max", help="CORE-ID assignment algorithm"
    )
    args = parser.parse_args()

    mappings_dir = Path("mappings")
    PUBLISHED_DIR.mkdir(exist_ok=True)

    for rule_dir in args.new_dirs.split():
        rule_path = Path(rule_dir) / "rule.yaml"
        if not rule_path.exists():
            print(f"[SKIP] No rule.yaml found in {rule_dir}")
            continue

        core_id = get_next_core_id(mappings_dir, args.algorithm)

        update_rule_yaml(core_id, rule_path)

        new_path = PUBLISHED_DIR / core_id
        Path(rule_dir).rename(new_path)
        print(f"[OK] {rule_dir} -> {new_path} ({core_id})")


if __name__ == "__main__":
    main()
