import argparse
import os
import re
import shutil
import yaml

CORE_PATTERN = re.compile(r"^CORE-\d{6}$")

def extract_numeric_ids(coreids):
    numbers = []
    for cid in coreids:
        match = CORE_PATTERN.match(cid)
        if match:
            numbers.append(int(match.group(1)))
    return numbers


def max_next_id(existing_coreids):
    nums = extract_numeric_ids(existing_coreids)
    max_id = max(nums) if nums else 0
    return f"CORE-{str(max_id + 1).zfill(6)}"


def min_next_id(existing_coreids):
    nums = sorted(extract_numeric_ids(existing_coreids))
    expected = 1
    for num in nums:
        if num != expected:
            return f"CORE-{str(expected).zfill(6)}"
        expected += 1
    return f"CORE-{str(expected).zfill(6)}"


def generate_core_id(existing_coreids, algorithm):
    if algorithm == "min":
        return min_next_id(existing_coreids)
    return max_next_id(existing_coreids)


def publish_rule_yaml(yaml_path, existing_coreids, algorithm):
    with open(yaml_path, "r") as f:
        content = yaml.safe_load(f)

    if content is None:
        content = {}

    if "Core" not in content or content["Core"] is None:
        content["Core"] = {}

    core = content["Core"]

    if not CORE_PATTERN.match(str(core.get("Id", ""))):
        new_id = generate_core_id(existing_coreids, algorithm)
        core["Id"] = new_id
    else:
        new_id = core["Id"]

    core["Status"] = "Published"

    with open(yaml_path, "w") as f:
        yaml.safe_dump(content, f, sort_keys=False)

    return new_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-dirs", required=True)
    parser.add_argument("--existing", required=True)
    parser.add_argument("--algorithm", choices=["min", "max"], default="min")
    args = parser.parse_args()

    new_dirs = [d.strip() for d in args.new_dirs.split() if d.strip()]
    existing_coreids = [d.strip() for d in args.existing.split() if d.strip()]

    for directory in new_dirs:
        if not os.path.isdir(directory):
            continue

        yaml_path = os.path.join(directory, "rule.yaml")
        if not os.path.exists(yaml_path):
            continue

        new_core_id = publish_rule_yaml(
            yaml_path,
            existing_coreids,
            args.algorithm,
        )

        if directory != new_core_id:
            shutil.move(directory, new_core_id)

        if new_core_id not in existing_coreids:
            existing_coreids.append(new_core_id)

        print(f"Published {directory} -> {new_core_id}")


if __name__ == "__main__":
    main()