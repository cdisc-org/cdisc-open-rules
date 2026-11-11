#!/usr/bin/env python3
"""
Rebuilds mappings/<Standard>_mapping.csv from Library/rule.json.

rule.json is the flat {core_id: rule} file written by build_library_rules.py
Every Authorities -> Standards -> References entry becomes a
row in that standard's CSV:

    Rule ID,<version>,<version>,...,Status,CORE-ID

FDA references whose Rule_Identifier starts with "FB" are also bucketed into
"FDA Business Rules", matching the existing YAML-based generator.
"""
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RULES_PATH = Path(os.getenv("RULES_PATH", "Library/rule.json"))
MAPPINGS_DIR = Path(os.getenv("MAPPINGS_DIR", "mappings"))
PRUNE_STALE = os.getenv("PRUNE_STALE", "true").strip().lower() == "true"
PR_BODY_PATH = os.getenv("PR_BODY_PATH")

SUFFIX = "_mapping.csv"
FDA_BUCKET = "FDA Business Rules"


def warn(message: str) -> None:
    print(f"::warning::{message}")


def error(message: str) -> None:
    print(f"::error::{message}")


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def rule_identifier(ref: dict) -> str:
    block = ref.get("Rule_Identifier") or ref.get("Rule Identifier") or {}
    if not isinstance(block, dict):
        return ""
    return str(block.get("Id") or "").strip()


def collect(rules: dict):
    """
    Returns:
        rows:       {STANDARD_KEY: {rule_id: row}}
        spellings:  {STANDARD_KEY: Counter(original spellings)}
        collisions: [(standard, rule_id, [core ids])]
    """
    rows: dict[str, dict[str, dict]] = defaultdict(dict)
    spellings: dict[str, Counter] = defaultdict(Counter)
    owners: dict[tuple, list] = defaultdict(list)

    for core_key in sorted(rules):  # deterministic: lowest CORE id wins ties
        rule = rules[core_key]
        if not isinstance(rule, dict):
            continue
        core = rule.get("Core") if isinstance(rule.get("Core"), dict) else {}
        status = str(core.get("Status") or "DRAFT").strip().upper()
        core_id = str(core.get("Id") or core_key).strip() if status == "PUBLISHED" else ""

        for authority in rule.get("Authorities") or []:
            if not isinstance(authority, dict):
                continue
            is_fda = str(authority.get("Organization") or "").strip().upper() == "FDA"
            for standard in authority.get("Standards") or []:
                if not isinstance(standard, dict):
                    continue
                name = str(standard.get("Name") or "").strip()
                if not name:
                    continue
                version = str(standard.get("Version") or "").strip()
                for ref in standard.get("References") or []:
                    if not isinstance(ref, dict):
                        continue
                    rid = rule_identifier(ref)
                    if not rid:
                        continue
                    targets = [name]
                    if is_fda and rid.upper().startswith("FB"):
                        targets.append(FDA_BUCKET)
                    for target in targets:
                        key = target.upper()
                        spellings[key][target] += 1
                        if core_key not in owners[(key, rid)]:
                            owners[(key, rid)].append(core_key)
                        row = rows[key].get(rid)
                        if row is None:
                            row = rows[key][rid] = {
                                "rule_id": rid,
                                "versions": set(),
                                "status": status,
                                "core_id": core_id,
                            }
                        elif row["status"] != "PUBLISHED" and status == "PUBLISHED":
                            # prefer a published owner over a draft one
                            row["status"], row["core_id"] = status, core_id
                        if version:
                            row["versions"].add(version)

    collisions = [
        (key, rid, ids) for (key, rid), ids in sorted(owners.items()) if len(ids) > 1
    ]
    return rows, spellings, collisions


# ---------------------------------------------------------------------------
# Ordering (identical to generate_mappings.py)
# ---------------------------------------------------------------------------

def rule_id_sort_key(rid: str) -> tuple:
    m = re.match(r"^([A-Za-z]*)(\d+)(.*)", rid)
    if m:
        return (m.group(1).upper(), int(m.group(2)), m.group(3))
    return (rid.upper(), 0, "")


def version_sort_key(v: str) -> list:
    parts = []
    for x in v.split("."):
        try:
            parts.append((0, int(x)))
        except ValueError:
            parts.append((1, x))
    return parts


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------

def render(rows: dict[str, dict]) -> tuple[list[str], list[dict]]:
    ordered = sorted(rows.values(), key=lambda r: rule_id_sort_key(r["rule_id"]))
    versions = sorted({v for r in ordered for v in r["versions"]}, key=version_sort_key)
    fieldnames = ["Rule ID"] + versions + ["Status", "CORE-ID"]
    out = []
    for r in ordered:
        line = {"Rule ID": r["rule_id"], "Status": r["status"], "CORE-ID": r["core_id"]}
        for v in versions:
            line[v] = v if v in r["versions"] else ""
        out.append(line)
    return fieldnames, out


def read_csv(path: Path) -> dict[str, tuple]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        return {
            row["Rule ID"]: tuple(sorted(row.items()))
            for row in reader
            if row.get("Rule ID")
        }


def write_csv(path: Path, fieldnames: list[str], lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(lines)


def safe_filename(name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "-", name)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if not RULES_PATH.exists():
        error(f"{RULES_PATH} not found")
        return 1
    try:
        rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        error(f"{RULES_PATH} is not valid JSON: {e}")
        return 1
    if not isinstance(rules, dict) or not rules:
        error(f"{RULES_PATH} has no rules; refusing to touch {MAPPINGS_DIR}/")
        return 1

    rows_by_std, spellings, collisions = collect(rules)
    if not rows_by_std:
        error("No Authorities/Standards/References found in any rule; refusing to write")
        return 1

    existing = {
        p.name[: -len(SUFFIX)].upper(): p
        for p in MAPPINGS_DIR.glob(f"*{SUFFIX}")
        if p.is_file()
    }

    report = []  # (filename, total, added, removed, changed, is_new)
    written = set()
    for key in sorted(rows_by_std):
        path = existing.get(key) or MAPPINGS_DIR / safe_filename(
            f"{spellings[key].most_common(1)[0][0]}{SUFFIX}"
        )
        fieldnames, lines = render(rows_by_std[key])

        old = read_csv(path)
        new = {
            line["Rule ID"]: tuple(sorted({k: line.get(k, "") for k in fieldnames}.items()))
            for line in lines
        }
        added = len(new.keys() - old.keys())
        removed = len(old.keys() - new.keys())
        changed = sum(1 for k in new.keys() & old.keys() if new[k] != old[k])

        write_csv(path, fieldnames, lines)
        written.add(path.name)
        report.append((path.name, len(lines), added, removed, changed, not old))

    deleted = []
    if PRUNE_STALE:
        for path in sorted(existing.values()):
            if path.name not in written:
                path.unlink()
                deleted.append(path.name)

    for std, rid, ids in collisions:
        warn(f"{rid} in {std} is referenced by {', '.join(ids)}; versions merged, published owner kept")

    summary = build_summary(report, deleted, collisions, len(rules))
    print(summary)
    if PR_BODY_PATH:
        Path(PR_BODY_PATH).write_text(summary, encoding="utf-8")
    step_summary = os.getenv("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(summary)
    return 0


def build_summary(report, deleted, collisions, rule_count) -> str:
    touched = [r for r in report if r[2] or r[3] or r[4] or r[5]]
    lines = [
        f"Automated rebuild of `{MAPPINGS_DIR}/` from `{RULES_PATH}` ({rule_count} rules).",
        "",
        "| File | Rows | Added | Removed | Changed |",
        "|---|---|---|---|---|",
    ]
    for name, total, added, removed, changed, is_new in report:
        label = f"`{name}`" + (" (new)" if is_new else "")
        lines.append(f"| {label} | {total} | {added} | {removed} | {changed} |")
    lines.append("")
    if deleted:
        lines.append(f"**Deleted** (no longer referenced by any rule): {', '.join(f'`{d}`' for d in deleted)}")
        lines.append("")
    if collisions:
        shown = "\n".join(f"- `{rid}` ({std}): {', '.join(ids)}" for std, rid, ids in collisions[:100])
        more = f"\n- … and {len(collisions) - 100} more" if len(collisions) > 100 else ""
        lines.append(
            f"<details><summary>Rule IDs referenced by more than one CORE rule ({len(collisions)})</summary>"
            f"\n\n{shown}{more}\n</details>"
        )
        lines.append("")
    if not touched and not deleted:
        lines.append("_No mapping changes._")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())