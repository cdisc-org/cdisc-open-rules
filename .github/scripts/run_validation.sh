#!/usr/bin/env bash
# run_validation.sh — iterates all positive/ and negative/ test cases for a rule,
# runs the CORE engine against each, converts JSON output to results.csv,
# diffs against any committed results.csv, and writes a markdown report.
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
ENGINE_DIR="$REPO_ROOT/engine"
SCRIPTS_DIR="$REPO_ROOT/.github/scripts"
REPORT_FILE="$REPO_ROOT/validation_report.md"

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
# Initialise report
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
# Iterate test types and cases
# ---------------------------------------------------------------------------
for TEST_TYPE in positive negative; do
  TYPE_DIR="$RULE_DIR/$TEST_TYPE"
  [ -d "$TYPE_DIR" ] || continue

  echo "" >> "$REPORT_FILE"
  echo "## $TEST_TYPE" >> "$REPORT_FILE"
  echo "" >> "$REPORT_FILE"

  for CASE_DIR in $(find "$TYPE_DIR" -mindepth 1 -maxdepth 1 -type d | sort); do
    CASE_ID=$(basename "$CASE_DIR")
    DATA_DIR="$CASE_DIR/data"
    RESULTS_DIR="$CASE_DIR/results"
    CASE_LABEL="$TEST_TYPE/$CASE_ID"

    TOTAL_CASES=$((TOTAL_CASES + 1))
    echo ""
    echo "--- Processing $RULE_ID / $CASE_LABEL ---"

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
    if [ ! -f "$RESULTS_DIR/results.csv" ]; then
      echo "  ERROR: no committed results.csv found for $CASE_LABEL"
      {
        echo "### \`$CASE_LABEL\` — ❌ Missing results.csv"
        echo ""
        echo "No \`results.csv\` was found for this test case. Run the rule locally before opening a PR and commit the generated \`results.csv\`."
        echo ""
      } >> "$REPORT_FILE"
      FAILED_CASES=$((FAILED_CASES + 1))
      OVERALL_SUCCESS=false
      continue
    fi

    ENGINE_ARGS=(
      "-lr"  "$RULE_YML"
      "-d"   "$DATA_DIR"
      "-dep" "$ENV_FILE"
      "-of"  "JSON"
      "-o"   "$RESULTS_DIR/results"
      "-p"   "disabled"
    )

    echo "  Command: python core.py validate ${ENGINE_ARGS[*]}"

    # Back up committed results.csv before the engine run
    cp "$RESULTS_DIR/results.csv" "$RESULTS_DIR/results.csv.committed"
    COMMITTED_RESULTS="$RESULTS_DIR/results.csv.committed"

    # Run the engine
    ENGINE_LOG="/tmp/engine_${TEST_TYPE}_${CASE_ID}.txt"
    ENGINE_EXIT=0
    (cd "$ENGINE_DIR" && $PYTHON_CMD core.py validate "${ENGINE_ARGS[@]}") \
      2>&1 | tee "$ENGINE_LOG" || ENGINE_EXIT=${PIPESTATUS[0]}

    if [ $ENGINE_EXIT -ne 0 ] || [ ! -f "$RESULTS_DIR/results.json" ]; then
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
      FAILED_CASES=$((FAILED_CASES + 1))
      OVERALL_SUCCESS=false
      mv "$COMMITTED_RESULTS" "$RESULTS_DIR/results.csv"
      continue
    fi

    # Convert engine JSON output to a temporary CSV for comparison
    GENERATED_CSV="/tmp/results_generated_${TEST_TYPE}_${CASE_ID}.csv"
    CONVERT_EXIT=0
    $PYTHON_CMD "$SCRIPTS_DIR/convert_results.py" \
      "$RESULTS_DIR/results.json" "$GENERATED_CSV" \
      2>&1 | tee -a "$ENGINE_LOG" || CONVERT_EXIT=$?

    if [ $CONVERT_EXIT -ne 0 ]; then
      echo "  ERROR: failed to convert results.json to results.csv"
      {
        echo "### \`$CASE_LABEL\` — ❌ Conversion error"
        echo ""
        echo "<details><summary>Conversion output</summary>"
        echo ""
        echo '```'
        cat "$ENGINE_LOG"
        echo '```'
        echo "</details>"
        echo ""
      } >> "$REPORT_FILE"
      FAILED_CASES=$((FAILED_CASES + 1))
      OVERALL_SUCCESS=false
      mv "$COMMITTED_RESULTS" "$RESULTS_DIR/results.csv"
      continue
    fi

    DIFF_LOG="/tmp/diff_${TEST_TYPE}_${CASE_ID}.txt"
    DIFF_EXIT=0
    $PYTHON_CMD "$SCRIPTS_DIR/diff_results.py" \
      "$COMMITTED_RESULTS" "$GENERATED_CSV" "$CASE_LABEL" \
      > "$DIFF_LOG" 2>&1 || DIFF_EXIT=$?

    if [ $DIFF_EXIT -eq 0 ]; then
      echo "  PASSED — results match committed baseline"
      {
        echo "### \`$CASE_LABEL\` — ✅ Results match committed baseline"
        echo ""
      } >> "$REPORT_FILE"
      PASSED_CASES=$((PASSED_CASES + 1))
    else
      echo "  FAILED — committed results do not match engine output"
      {
        echo "### \`$CASE_LABEL\` — ❌ Results do not match engine output"
        echo ""
        echo "<details><summary>Diff details</summary>"
        echo ""
        echo '```'
        cat "$DIFF_LOG"
        echo '```'
        echo "</details>"
        echo ""
      } >> "$REPORT_FILE"
      FAILED_CASES=$((FAILED_CASES + 1))
      OVERALL_SUCCESS=false
    fi
    mv "$COMMITTED_RESULTS" "$RESULTS_DIR/results.csv"
    if [ -s "$ENGINE_LOG" ]; then
      {
        echo "<details><summary>Engine output for \`$CASE_LABEL\`</summary>"
        echo ""
        echo '```'
        cat "$ENGINE_LOG"
        echo '```'
        echo "</details>"
        echo ""
      } >> "$REPORT_FILE"
    fi

  done   # cases
done     # test types

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