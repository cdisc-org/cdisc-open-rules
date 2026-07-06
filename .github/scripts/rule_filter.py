"""
rule_filter.py

Determines whether a rule.yml qualifies for the Verisian validation run,
based on its `Authorities` block.

We only want to run rules that apply to at least one of:
    Authorities:
      - Organization: CDISC
        Standards:
          - Name: SDTMIG
      - Organization: FDA
        Standards:
          - Name: SDTMIG

Any other combination (other organizations, other standard names only) is
excluded.
"""

from pathlib import Path
from typing import Iterable

import yaml

ALLOWED_ORG_STANDARD_PAIRS = {
    ("CDISC", "SDTMIG"),
    ("FDA", "SDTMIG"),
}


def load_rule(rule_yml_path: Path) -> dict:
    with open(rule_yml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def rule_matches_authorities(rule: dict) -> bool:
    """
    True if any (Organization, Standard Name) pair in the rule's Authorities
    block is in ALLOWED_ORG_STANDARD_PAIRS.
    """
    authorities = rule.get("Authorities") or []
    for authority in authorities:
        org = authority.get("Organization")
        standards = authority.get("Standards") or []
        for standard in standards:
            name = standard.get("Name")
            if (org, name) in ALLOWED_ORG_STANDARD_PAIRS:
                return True
    return False


def rule_file_matches(rule_yml_path: Path) -> bool:
    try:
        rule = load_rule(rule_yml_path)
    except Exception:
        # Unparseable rule.yml — treat as non-matching rather than crashing
        # the whole run; the caller can log this separately if desired.
        return False
    return rule_matches_authorities(rule)


def find_matching_rule_dirs(published_root: Path) -> Iterable[Path]:
    """
    Yields the directory of every rule under `published_root` (e.g.
    open-rules/Published) whose rule.yml matches the Authorities filter.
    """
    for rule_dir in sorted(p for p in published_root.iterdir() if p.is_dir()):
        rule_yml = rule_dir / "rule.yml"
        if rule_yml.is_file() and rule_file_matches(rule_yml):
            yield rule_dir
