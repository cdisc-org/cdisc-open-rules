#!/usr/bin/env python3
"""
Local test runner for CDISC Open Rules.
Prompts for a rule folder path, runs the CORE engine against each test case,
and writes results.csv into each case's results/ directory.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, List

ENGINE_DIR = Path("engine")

LOG_LEVELS = ["info", "debug", "error", "critical", "disabled", "warn"]

# ---------------------------------------------------------------------------
# Rule folder helpers
# ---------------------------------------------------------------------------


def resolve_rule_path(raw: str) -> Path:
    path = Path(raw.strip()).expanduser()
    if not path.exists():
        print(f"Error: Path does not exist: {path}")
        sys.exit(1)
    if not path.is_dir():
        print(f"Error: Path is not a directory: {path}")
        sys.exit(1)
    return path


def find_rule_yml(rule_path: Path) -> Path:
    ymls = list(rule_path.glob("*.yml"))
    if not ymls:
        print(f"Error: No .yml file found in {rule_path}")
        sys.exit(1)
    if len(ymls) > 1:
        print(f"Error: Multiple .yml files found in {rule_path} — expected exactly one")
        sys.exit(1)
    return ymls[0]


def get_test_cases(rule_path: Path) -> Dict[str, List[dict]]:
    cases: Dict[str, List[dict]] = {"positive": [], "negative": []}
    for test_type in ("positive", "negative"):
        type_dir = rule_path / test_type
        if not type_dir.exists():
            continue
        for case_dir in sorted(type_dir.iterdir()):
            if case_dir.is_dir() and (case_dir / "data").is_dir():
                cases[test_type].append(
                    {
                        "case_id": case_dir.name,
                        "data_dir": case_dir / "data",
                        "results_dir": case_dir / "results",
                    }
                )
    return cases


def find_env_file(data_dir: Path) -> Optional[Path]:
    for candidate in data_dir.iterdir():
        if candidate.suffix == ".env" or candidate.name == ".env":
            return candidate
    return None


def next_results_path(results_dir: Path) -> Path:
    """
    Creates results/ if needed. Returns the next available -o path for the engine
    (without extension — engine appends .csv automatically).
    - No results.csv yet  ->  results_dir/results
    - results.csv exists  ->  results_dir/results(1), results_dir/results(2), ...
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    if not (results_dir / "results.csv").exists():
        return results_dir / "results"
    n = 1
    while (results_dir / f"results({n}).csv").exists():
        n += 1
    return results_dir / f"results({n})"


# ---------------------------------------------------------------------------
# Engine invocation
# ---------------------------------------------------------------------------


def run_engine(
    rule_yml: Path,
    data_dir: Path,
    output_path: Path,
    log_level: str,
    capture_logs: bool,
) -> tuple[bool, str]:
    env_file = find_env_file(data_dir)
    if env_file is None:
        return False, f"No .env file found in {data_dir}"

    cmd = [
        sys.executable,
        "core.py",
        "validate",
        "-lr",
        str(rule_yml.resolve()),
        "-d",
        str(data_dir.resolve()),
        "-dep",
        str(env_file.resolve()),
        "-of",
        "CSV",
        "-o",
        str(output_path.resolve()),
        "-p",
        "disabled",
        "-l",
        log_level,
    ]

    try:
        env = os.environ.copy()

        stream_output = log_level != "disabled"
        lines: list[str] = []
        with subprocess.Popen(
            cmd,
            cwd=ENGINE_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as proc:
            for line in proc.stdout:
                if stream_output:
                    print(f"    {line}", end="")
                lines.append(line)
            proc.wait()

        output = "".join(lines).strip()

        if capture_logs and output:
            log_path = output_path.parent / f"{output_path.name}_engine.log.txt"
            log_path.write_text(output, encoding="utf-8")
            print(f"    Log captured — {log_path}")

        return proc.returncode == 0, output
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_rule(
    rule_path: Path,
    specific_case: Optional[str],
    log_level: str,
    capture_logs: bool,
):
    rule_yml = find_rule_yml(rule_path)
    all_cases = get_test_cases(rule_path)

    if specific_case:
        target_type, target_id = specific_case.split("/", 1)
        all_cases = {
            k: ([c for c in v if c["case_id"] == target_id] if k == target_type else [])
            for k, v in all_cases.items()
        }

    print(f"\nRule: {rule_yml.name}")
    print("-" * 60)

    any_ran = False
    for test_type in ("positive", "negative"):
        for case in all_cases[test_type]:
            any_ran = True
            case_id = case["case_id"]
            data_dir = case["data_dir"]
            output_path = next_results_path(case["results_dir"])

            print(f"\n  Running {test_type}/{case_id}...")
            ok, output = run_engine(
                rule_yml, data_dir, output_path, log_level, capture_logs
            )

            csv_path = Path(str(output_path) + ".csv")
            if ok and csv_path.exists():
                print(f"    Done — results written to {csv_path}")
            else:
                print(f"    [ERROR] Engine failed for {test_type}/{case_id}")
                for line in output.splitlines():
                    print(f"      {line}")

    if not any_ran:
        print("  No test cases found.")

    print()


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


def prompt_rule_path() -> Path:
    print("\nEnter the path to your rule folder (e.g. Unpublished/CORE-000001).")
    print("Expected structure:")
    print("  <rule_folder>/")
    print("    <rule>.yml")
    print("    positive/01/data/")
    print("    negative/01/data/")
    print()
    while True:
        raw = input("Rule folder path: ").strip()
        if not raw:
            print("Path cannot be empty — try again.")
            continue
        path = resolve_rule_path(raw)
        if not list(path.glob("*.yml")):
            print(f"  No .yml file found in '{path}' — is this the right folder?")
            again = input("  Try a different path? (y/n): ").strip().lower()
            if again != "n":
                continue
        return path


def prompt_case(cases: Dict[str, List[dict]]) -> Optional[str]:
    flat = [f"{t}/{c['case_id']}" for t in ("positive", "negative") for c in cases[t]]
    if not flat:
        return None

    print("\nFound test cases:")
    for i, tc in enumerate(flat, 1):
        print(f"  {i}. {tc}")

    while True:
        choice = input("\nEnter case number/name, or press Enter to run all: ").strip()
        if not choice:
            return None
        if choice in flat:
            return choice
        if choice.isdigit() and 1 <= int(choice) <= len(flat):
            return flat[int(choice) - 1]
        print("Invalid — try again.")


def prompt_log_level() -> str:
    print("\nLog level options:")
    for i, level in enumerate(LOG_LEVELS, 1):
        print(f"  {i}. {level}")
    while True:
        choice = input("Select log level (default: disabled): ").strip().lower()
        if not choice:
            return "disabled"
        if choice in LOG_LEVELS:
            return choice
        if choice.isdigit() and 1 <= int(choice) <= len(LOG_LEVELS):
            return LOG_LEVELS[int(choice) - 1]
        print("Invalid — try again.")


def prompt_capture_logs() -> bool:
    choice = input("Capture engine logs to results folder? (y/N): ").strip().lower()
    return choice == "y"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    rule_path = prompt_rule_path()
    cases = get_test_cases(rule_path)
    specific = prompt_case(cases)
    log_level = prompt_log_level()
    capture_logs = prompt_capture_logs()
    run_rule(rule_path, specific, log_level, capture_logs)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
