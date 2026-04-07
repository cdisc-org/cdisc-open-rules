"""
Script to create a new rule directory with the required structure and template files for testing.
"""
import sys
import shutil
from pathlib import Path

RULES_DIR = Path("Unpublished")
PLACEHOLDER_RULE_ID = "NEW-RULE"

ENV_TEMPLATE = """\
PRODUCT=
VERSION=
SUBSTANDARD=
DEFINE_XML=
CT=
"""

VARIABLES_HEADERS = ["dataset", "variable", "label", "type", "length"]
TABLES_HEADERS = ["Filename", "Label"]


def create_csv(filepath: Path, headers: list[str]):
    with open(filepath, "w", newline="") as f:
        f.write(",".join(headers) + "\n")


def create_test_cases(rule_dir: Path, test_type: str, count: int):
    for i in range(1, count + 1):
        case_id = f"{i:02d}"
        case_dir = rule_dir / test_type / case_id

        data_dir = case_dir / "data"
        results_dir = case_dir / "results"
        data_dir.mkdir(parents=True, exist_ok=True)
        results_dir.mkdir(parents=True, exist_ok=True)

        env_path = data_dir / ".env"
        env_path.write_text(ENV_TEMPLATE)

        create_csv(data_dir / "variables.csv", VARIABLES_HEADERS)
        create_csv(data_dir / "tables.csv", TABLES_HEADERS)


def main():
    rule_dir = RULES_DIR / PLACEHOLDER_RULE_ID
    if rule_dir.exists():
        do_wipe: bool = (
            input(
                "Another new rule folder already exists. Would you like to erase it and make a new one? (Y/N) "
            ).lower()
            == "y"
        )
        if not do_wipe:
            print("Aborting.")
            sys.exit(0)
        shutil.rmtree(rule_dir, ignore_errors=False)

    rule_dir.mkdir(parents=True, exist_ok=True)

    yml_file = rule_dir / "rule.yml"
    shutil.copy("template/template-rule.yml", yml_file)

    n_pos_cases = int(input("Enter the number of positive test cases to create: "))
    n_neg_cases = int(input("Enter the number of negative test cases to create: "))

    if n_pos_cases > 0:
        create_test_cases(rule_dir, "positive", n_pos_cases)
    if n_neg_cases > 0:
        create_test_cases(rule_dir, "negative", n_neg_cases)

    print(f"\nSuccess!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
