#!/usr/bin/env python3
"""
Builds Library/rule.json from:
  1. cdisc-org/core-contributor  rules/CORE-XXXXXX/*.yaml   (fetched via GitHub API)
  2. this repo (cdisc-open-rules) Published/CORE-XXXXXX/*.yaml (local checkout)

On a CORE id collision the core-contributor rule wins.

Output is a flat {core_id: rule} dict of raw rule metadata in the form the
CDISC Library API serves today (YAML keys with spaces replaced by underscores,
every Version value kept as its literal YAML text).
The engine still runs Rule.from_cdisc_metadata on what the Library returns,
so the engine's cached rules are unchanged.

Output is deterministic (sorted keys, no timestamps or commit SHAs) so the file
only changes when rule content changes, which is what drives the PR decision.
"""
import datetime
import io
import json
import os
import re
import sys
import tarfile
import time
from pathlib import Path

import requests
import yaml

CORE_FOLDER = re.compile(r"^CORE-\d{6}$")
YAML_EXTENSIONS = (".yml", ".yaml")
NULL_TAG = "tag:yaml.org,2002:null"
STR_TAG = "tag:yaml.org,2002:str"

OUTPUT_PATH = Path(os.getenv("OUTPUT_PATH", "Library/rule.json"))
OPEN_RULES_DIR = Path(os.getenv("OPEN_RULES_DIR", "Published"))
CORE_REPO = os.getenv("CORE_CONTRIBUTOR_REPO", "cdisc-org/core-contributor")
CORE_REF = os.getenv("CORE_CONTRIBUTOR_REF", "main")
CORE_RULES_DIR = os.getenv("CORE_CONTRIBUTOR_RULES_DIR", "rules")
PR_BODY_PATH = os.getenv("PR_BODY_PATH")
TOKEN = os.getenv("GITHUB_TOKEN")

CORE_SOURCE = "core-contributor"
OPEN_SOURCE = "cdisc-open-rules"


def warn(message: str) -> None:
    print(f"::warning::{message}")


def error(message: str) -> None:
    print(f"::error::{message}")


def load_yaml(text: str):
    """yaml.safe_load, except every `Version:` scalar keeps its literal text.

    Plain safe_load turns unquoted 3.10 into the float 3.1 and 1 into the int 1;
    no later str() can recover "3.10". The document is composed into nodes, each
    Version value node is retagged as a string, then built by the stock SafeLoader.
    """
    loader = yaml.SafeLoader(text)
    try:
        node = loader.get_single_node()
        if node is None:
            return None
        _tag_versions_as_str(node, set())
        return loader.construct_document(node)
    finally:
        loader.dispose()


def _tag_versions_as_str(node, seen: set) -> None:
    if id(node) in seen:  # anchors/aliases share node objects
        return
    seen.add(id(node))
    if isinstance(node, yaml.MappingNode):
        for key, value in node.value:
            if (
                isinstance(key, yaml.ScalarNode)
                and key.value == "Version"
                and isinstance(value, yaml.ScalarNode)
                and value.tag != NULL_TAG
            ):
                value.tag = STR_TAG
            _tag_versions_as_str(value, seen)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            _tag_versions_as_str(item, seen)


def replace_yml_spaces(data):
    if isinstance(data, dict):
        return {key.replace(" ", "_"): replace_yml_spaces(value) for key, value in data.items()}
    if isinstance(data, list):
        return [replace_yml_spaces(item) for item in data]
    return data


def json_safe(data):
    """yaml turns unquoted dates into date objects; JSON can't hold those."""
    if isinstance(data, dict):
        return {key: json_safe(value) for key, value in data.items()}
    if isinstance(data, list):
        return [json_safe(item) for item in data]
    if isinstance(data, (datetime.date, datetime.datetime)):
        return data.isoformat()
    return data


def parse_rule(text: str, origin: str, folder: str):
    try:
        loaded = load_yaml(text)
    except yaml.YAMLError as e:
        warn(f"{origin}: YAML parse error, skipping: {e}")
        return None
    if not isinstance(loaded, dict):
        warn(f"{origin}: not a YAML mapping, skipping")
        return None

    rule = json_safe(replace_yml_spaces(loaded))
    core = rule.get("Core") if isinstance(rule.get("Core"), dict) else {}
    core_id = core.get("Id") or folder
    if core_id != folder:
        warn(f"{origin}: Core.Id {core_id} does not match folder {folder}")
    return core_id, rule


def add_rule(rules: dict, core_id: str, rule: dict, origin: str) -> None:
    if core_id in rules:
        warn(f"{origin}: duplicate {core_id} within the same repo, keeping the first")
        return
    rules[core_id] = rule


def load_core_contributor() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    url = f"https://api.github.com/repos/{CORE_REPO}/tarball/{CORE_REF}"
    for attempt in range(3):  # GitHub returns occasional 502/503 on tarball requests
        response = requests.get(url, headers=headers, timeout=300)
        if response.status_code < 500 or attempt == 2:
            break
        warn(f"{url}: HTTP {response.status_code}, retrying")
        time.sleep(10 * (attempt + 1))
    response.raise_for_status()

    rules = {}
    with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
        for member in sorted(tar.getmembers(), key=lambda m: m.name):
            if not member.isfile():
                continue
            # first component is "<owner>-<repo>-<sha>"
            parts = member.name.split("/")[1:]
            if len(parts) != 3:
                continue
            top, folder, filename = parts
            if top != CORE_RULES_DIR or not CORE_FOLDER.match(folder):
                continue
            if not filename.lower().endswith(YAML_EXTENSIONS):
                continue
            origin = f"{CORE_REPO}:{'/'.join(parts)}"
            parsed = parse_rule(tar.extractfile(member).read().decode("utf-8"), origin, folder)
            if parsed:
                add_rule(rules, *parsed, origin=origin)
    return rules


def load_open_rules() -> dict:
    rules = {}
    for path in sorted(OPEN_RULES_DIR.glob("CORE-*/*")):
        if not path.is_file() or path.suffix.lower() not in YAML_EXTENSIONS:
            continue
        if not CORE_FOLDER.match(path.parent.name):
            continue
        parsed = parse_rule(path.read_text(encoding="utf-8"), str(path), path.parent.name)
        if parsed:
            add_rule(rules, *parsed, origin=str(path))
    return rules


def merge(core_rules: dict, open_rules: dict):
    merged, sources = {}, {}
    for core_id, rule in core_rules.items():
        merged[core_id] = rule
        sources[core_id] = CORE_SOURCE
    overridden = []
    for core_id, rule in open_rules.items():
        if core_id in merged:
            overridden.append(core_id)
            continue
        merged[core_id] = rule
        sources[core_id] = OPEN_SOURCE
    return merged, sources, sorted(overridden)


def load_existing_rules() -> dict:
    if not OUTPUT_PATH.exists():
        return {}
    try:
        data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        warn(f"{OUTPUT_PATH} is not valid JSON; treating every rule as new")
        return {}
    return data if isinstance(data, dict) else {}


def id_list(ids, limit=100) -> str:
    if not ids:
        return "_none_"
    shown = ", ".join(f"`{i}`" for i in ids[:limit])
    return shown + (f" … and {len(ids) - limit} more" if len(ids) > limit else "")


def build_summary(old, new, sources, overridden, core_count, open_count) -> str:
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    changed = sorted(k for k in new.keys() & old.keys() if new[k] != old[k])

    return "\n".join([
        "Automated rebuild of `Library/rule.json` from "
        f"`{CORE_REPO}@{CORE_REF}` (`{CORE_RULES_DIR}/`) and this repo's `{OPEN_RULES_DIR}/`.",
        "",
        "| | Count |",
        "|---|---|",
        f"| Rules in output | {len(new)} |",
        f"| From {CORE_SOURCE} | {sum(1 for s in sources.values() if s == CORE_SOURCE)} (of {core_count} parsed) |",
        f"| From {OPEN_SOURCE} | {sum(1 for s in sources.values() if s == OPEN_SOURCE)} (of {open_count} parsed) |",
        f"| Open-rules versions overridden by core-contributor | {len(overridden)} |",
        f"| Added | {len(added)} |",
        f"| Changed | {len(changed)} |",
        f"| Removed | {len(removed)} |",
        "",
        f"<details><summary>Added ({len(added)})</summary>\n\n{id_list(added)}\n</details>",
        f"<details><summary>Changed ({len(changed)})</summary>\n\n{id_list(changed)}\n</details>",
        f"<details><summary>Removed ({len(removed)})</summary>\n\n{id_list(removed)}\n</details>",
        "",
    ])


def main() -> int:
    core_rules = load_core_contributor()
    open_rules = load_open_rules()

    # Guard against a bad download or wrong path wiping the file.
    if not core_rules:
        error(f"No rules found in {CORE_REPO}/{CORE_RULES_DIR}; refusing to write output")
        return 1
    if not open_rules:
        error(f"No rules found in {OPEN_RULES_DIR}/; refusing to write output")
        return 1

    # Source info goes in the PR summary only, not in the file.
    merged, sources, overridden = merge(core_rules, open_rules)
    old_rules = load_existing_rules()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(merged, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    summary = build_summary(old_rules, merged, sources, overridden, len(core_rules), len(open_rules))
    print(summary)
    if PR_BODY_PATH:
        Path(PR_BODY_PATH).write_text(summary, encoding="utf-8")
    step_summary = os.getenv("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
