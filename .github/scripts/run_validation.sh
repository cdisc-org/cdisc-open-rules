#!/usr/bin/env bash
# run_validation.sh — iterates all positive/ and negative/ test cases for a rule,
# runs the CORE engine against each, prints output to results.csv,
# diffs against any expected results.csv, and writes two outputs:
#   - $REPO_ROOT/validation_report.md  (detailed markdown, legacy/fallback)
#   - $REPO_ROOT/case_results.jsonl    (one JSON line per test case for the summary table)
#
# Usage:
#   bash .github/scripts/run_validation.sh <rule_rel_path> <python_cmd> <repo_root>
#
# Exit codes:
#   0 — all engine runs succeeded (diff warnings do not cause failure)
#   1 — one or more engine runs failed

set -euo pipefail

RULE_REL_PATH="${1:?rule_rel_path required}"
PYTHON_CMD="${2:?python_cmd required}"
REPO_ROOT="${3:?repo_root required}"

RULE_ID=$(basename "$RULE_REL_PATH")
RULE_DIR="$REPO_ROOT/$RULE_REL_PATH"
# Allow caller to override engine location (e.g. when called from rules-engine repo)
ENGINE_DIR="${ENGINE_DIR_OVERRIDE:-$REPO_ROOT/engine}"
SCRIPTS_DIR="$REPO_ROOT/.github/scripts"
REPORT_FILE="$REPO_ROOT/validation_report.md"
JSONL_FILE="$REPO_ROOT/case_results.jsonl"

# ---------------------------------------------------------------------------
# Locate the rule YAML
# ---------------------------------------------------------------------------
RULE_YML=$(find "$RULE_DIR" -maxdepth 1 -name "*.yml" | head -1)
if [ -z "$RULE_YML" ]; then
  echo "::error::No .yml rule file found in $RULE_DIR"
  exit 1
fi
echo "Rule file: $RULE_YML"

# ---------------------------------------------------------------------------
# Initialize report
# ---------------------------------------------------------------------------
{
  echo "# Rule Validation Report"
  echo ""
  echo "**Rule:** \`$RULE_ID\`"
  echo "**Rule file:** \`$RULE_YML\`"
  echo ""
} > "$REPORT_FILE"

OVERALL_SUCCESS=true
TOTAL_CASES=0
PASSED_CASES=0
FAILED_CASES=0

# ---------------------------------------------------------------------------
# Helper: append one JSON line to case_results.jsonl
# Passes all values via env vars to avoid shell-quoting issues with paths.
# Args: exec(true|false)  expected  actual  match(true|false)  diff_path  stderr_path
# ---------------------------------------------------------------------------
emit_result() {
  R_RULE="$RULE_ID"   \
  R_TYPE="$TEST_TYPE" \
  R_NUM="$CASE_ID"    \
  R_EXEC="$1"         \
  R_EXPECTED="$2"     \
  R_ACTUAL="$3"       \
  R_MATCH="$4"        \
  R_DIFF="$5"         \
  R_STDERR="$6"       \
  python -c "
import json, os
e = os.environ
print(json.dumps({
  'rule':     e['R_RULE'],
  'type':     e['R_TYPE'],
  'num':      e['R_NUM'],
  'exec':     e['R_EXEC'] == 'true',
  'expected': e['R_EXPECTED'],
  'actual':   e['R_ACTUAL'],
  'match':    e['R_MATCH'] == 'true',
  'diff':     e['R_DIFF'],
  'stderr':   e['R_STDERR'],
}))" >> "$JSONL_FILE"
}

# ---------------------------------------------------------------------------
# Iterate test types and cases
# ---------------------------------------------------------------------------
for TEST_TYPE in positive negative; do
  TYPE_DIR="$RULE_DIR/$TEST_TYPE"
  [ -d "$TYPE_DIR" ] || continue

  {
    echo ""
    echo "## $TEST_TYPE"
    echo ""
  } >> "$REPORT_FILE"

  while IFS= read -r -d '' CASE_DIR; do
    CASE_ID=$(basename "$CASE_DIR")
    DATA_DIR="$CASE_DIR/data"
    RESULTS_DIR="$CASE_DIR/results"
    CASE_LABEL="$TEST_TYPE/$CASE_ID"

    echo ""
    echo "--- Processing $RULE_ID / $CASE_LABEL ---"

    # -- Skip cases that are structurally incomplete (no jsonl entry emitted)
    if [ ! -d "$DATA_DIR" ]; then
      echo "::warning::Missing data/ directory for $CASE_LABEL — skipping"
      echo "### \`$CASE_LABEL\` — ⚠️ Skipped (no data/ directory)" >> "$REPORT_FILE"
      echo "" >> "$REPORT_FILE"
      continue
    fi

    mkdir -p "$RESULTS_DIR"

    ENV_FILE=$(find "$DATA_DIR" -maxdepth 1 \( -name "*.env" -o -name ".env" \) | head -1)
    if [ -z "$ENV_FILE" ]; then
      echo "::warning::No .env file found in $DATA_DIR for $CASE_LABEL — skipping"
      echo "### \`$CASE_LABEL\` — ⚠️ Skipped (no .env file)" >> "$REPORT_FILE"
      echo "" >> "$REPORT_FILE"
      continue
    fi
    echo "  .env: $ENV_FILE"

    TOTAL_CASES=$((TOTAL_CASES + 1))

    # -- Check for missing expected baseline (engine still runs)
    MISSING_BASELINE=false
    if [ ! -f "$RESULTS_DIR/results.csv" ]; then
      echo "  WARNING: no expected results.csv found for $CASE_LABEL — engine will still run"
      MISSING_BASELINE=true
    fi

    # Back up expected results.csv before the engine run (only if it exists)
    EXPECTED_RESULTS=""
    if [ "$MISSING_BASELINE" = false ]; then
      cp "$RESULTS_DIR/results.csv" "$RESULTS_DIR/results.expected.csv"
      EXPECTED_RESULTS="$RESULTS_DIR/results.expected.csv"
    fi

    ENGINE_ARGS=(
      "-lr"  "$RULE_YML"
      "-d"   "$DATA_DIR"
      "-dep" "$ENV_FILE"
      "-of"  "CSV"
      "-o"   "$RESULTS_DIR/results"
      "-p"   "disabled"
    )

    echo "  Command: python core.py validate ${ENGINE_ARGS[*]}"

    # Run the engine
    ENGINE_LOG="/tmp/engine_${TEST_TYPE}_${CASE_ID}.txt"
    ENGINE_EXIT=0
    (cd "$ENGINE_DIR" && $PYTHON_CMD core.py validate "${ENGINE_ARGS[@]}") \
      2>&1 | tee "$ENGINE_LOG" || ENGINE_EXIT=${PIPESTATUS[0]}

    ACTUAL_CSV="$RESULTS_DIR/results.csv"

    if [ $ENGINE_EXIT -ne 0 ] || [ ! -f "$ACTUAL_CSV" ]; then
      echo "  ERROR: engine failed or produced no output (exit $ENGINE_EXIT)"
      {
        echo "### \`$CASE_LABEL\` — ❌ Engine error"
        echo ""
        echo "<details><summary>Engine output</summary>"
        echo ""
        echo '```'
        cat "$ENGINE_LOG"
        echo '```'
        echo "</details>"
        echo ""
      } >> "$REPORT_FILE"
      emit_result "false" "" "" "false" "" "$ENGINE_LOG"
      FAILED_CASES=$((FAILED_CASES + 1))
      OVERALL_SUCCESS=false
      [ "$MISSING_BASELINE" = false ] && mv "$EXPECTED_RESULTS" "$RESULTS_DIR/results.csv"
      continue
    fi

    ACTUAL_COUNT=$(( $(wc -l < "$ACTUAL_CSV") - 1 ))

    # -- Missing baseline: report actual count, no diff
    if [ "$MISSING_BASELINE" = true ]; then
      echo "  FAILED — no expected results.csv baseline exists"
      {
        echo "### \`$CASE_LABEL\` — ❌ Missing expected results.csv"
        echo ""
        echo "No expected \`results.csv\` was found for this test case."
        echo ""
      } >> "$REPORT_FILE"
      emit_result "true" "" "$ACTUAL_COUNT" "false" "" ""
      FAILED_CASES=$((FAILED_CASES + 1))
      OVERALL_SUCCESS=false
      continue
    fi

    # -- Diff
    EXPECTED_COUNT=$(( $(wc -l < "$EXPECTED_RESULTS") - 1 ))

    DIFF_LOG="/tmp/diff_${TEST_TYPE}_${CASE_ID}.txt"
    DIFF_EXIT=0
    $PYTHON_CMD "$SCRIPTS_DIR/diff_results.py" \
      "$EXPECTED_RESULTS" "$ACTUAL_CSV" "$CASE_LABEL" \
      > "$DIFF_LOG" 2>&1 || DIFF_EXIT=$?

    if [ $DIFF_EXIT -eq 0 ]; then
      echo "  PASSED — actual results match expected baseline"
      {
        echo "### \`$CASE_LABEL\` — ✅ Actual results match expected baseline"
        echo ""
      } >> "$REPORT_FILE"
      emit_result "true" "$EXPECTED_COUNT" "$ACTUAL_COUNT" "true" "" ""
      PASSED_CASES=$((PASSED_CASES + 1))
    else
      echo "  FAILED — expected results do not match actual engine output"
      {
        echo "### \`$CASE_LABEL\` — ❌ Expected results do not match actual engine output"
        echo ""
        echo "<details><summary>Diff details</summary>"
        echo ""
        echo '```'
        cat "$DIFF_LOG"
        echo '```'
        echo "</details>"
        echo ""
      } >> "$REPORT_FILE"
      emit_result "true" "$EXPECTED_COUNT" "$ACTUAL_COUNT" "false" "$DIFF_LOG" ""
      FAILED_CASES=$((FAILED_CASES + 1))
      OVERALL_SUCCESS=false
    fi

    mv "$EXPECTED_RESULTS" "$RESULTS_DIR/results.csv"

  done < <(find "$TYPE_DIR" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
{
  echo "---"
  echo ""
  printf "**Summary:** %d passed" "$PASSED_CASES"
  [ $FAILED_CASES -gt 0 ] && printf " | %d failed" "$FAILED_CASES"
  printf " (Total: %d test cases)\n" "$TOTAL_CASES"
  echo ""
} >> "$REPORT_FILE"

if [ "$OVERALL_SUCCESS" = false ]; then
  exit 1
fi
