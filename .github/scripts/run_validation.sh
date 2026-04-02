#!/usr/bin/env bash
# run_validation.sh — iterates all positive/ and negative/ test cases for a rule,
# runs the CORE engine against each, diffs against any committed results.json,
# and writes a markdown report to validation_report.md.
#
# Usage:
#   bash .github/scripts/run_validation.sh <rule_id> <python_cmd> <repo_root>
#
# Environment:
#   GITHUB_STEP_SUMMARY — set automatically by GitHub Actions
#
# Exit codes:
#   0 — all engine runs succeeded (diff warnings do not cause failure)
#   1 — one or more engine runs failed

set -euo pipefail

RULE_ID="${1:?rule_id required}"
PYTHON_CMD="${2:?python_cmd required}"
REPO_ROOT="${3:?repo_root required}"

RULE_DIR="$REPO_ROOT/rules/$RULE_ID"
ENGINE_DIR="$REPO_ROOT/engine"
SCRIPTS_DIR="$REPO_ROOT/.github/scripts"   # diff_results.py
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
NEW_CASES=0

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

    # Validate layout
    if [ ! -d "$DATA_DIR" ]; then
      echo "::warning::Missing data/ directory for $CASE_LABEL — skipping"
      echo "### \`$CASE_LABEL\` — ⚠️ Skipped (no data/ directory)" >> "$REPORT_FILE"
      echo "" >> "$REPORT_FILE"
      continue
    fi

    mkdir -p "$RESULTS_DIR"

    # Locate .env file (accept both "something.env" and ".env")
    ENV_FILE=$(find "$DATA_DIR" -maxdepth 1 \( -name "*.env" -o -name ".env" \) | head -1)
    if [ -z "$ENV_FILE" ]; then
      echo "::warning::No .env file found in $DATA_DIR for $CASE_LABEL — skipping"
      echo "### \`$CASE_LABEL\` — ⚠️ Skipped (no .env file)" >> "$REPORT_FILE"
      echo "" >> "$REPORT_FILE"
      continue
    fi
    echo "  .env: $ENV_FILE"

    # Assemble engine argument list — engine reads all standard/version/CT
    # flags directly from the .env via -dep
    ENGINE_ARGS=(
      "-lr"  "$RULE_YML"
      "-d"   "$DATA_DIR"
      "-dep" "$ENV_FILE"
      "-of"  "JSON"
      "-o"   "$RESULTS_DIR/results"
      "-p"   "disabled"
    )

    echo "  Command: python core.py validate ${ENGINE_ARGS[*]}"

    # Backup committed results if present
    COMMITTED_RESULTS=""
    if [ -f "$RESULTS_DIR/results.json" ]; then
      cp "$RESULTS_DIR/results.json" "$RESULTS_DIR/results.json.committed"
      COMMITTED_RESULTS="$RESULTS_DIR/results.json.committed"
      echo "  Backed up existing results.json"
    fi

    # Run the engine from inside the engine/ directory
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
      rm -f "$COMMITTED_RESULTS"
      continue
    fi

    # Diff or report
    if [ -n "$COMMITTED_RESULTS" ]; then
      DIFF_LOG="/tmp/diff_${TEST_TYPE}_${CASE_ID}.txt"
      DIFF_EXIT=0
      $PYTHON_CMD "$SCRIPTS_DIR/diff_results.py" \
        "$COMMITTED_RESULTS" "$RESULTS_DIR/results.json" "$CASE_LABEL" \
        > "$DIFF_LOG" 2>&1 || DIFF_EXIT=$?

      if [ $DIFF_EXIT -eq 0 ]; then
        echo "  PASSED — results match committed baseline"
        {
          echo "### \`$CASE_LABEL\` — ✅ Results match committed baseline"
          echo ""
        } >> "$REPORT_FILE"
        PASSED_CASES=$((PASSED_CASES + 1))
      elif [ $DIFF_EXIT -eq 1 ]; then
        echo "  CHANGED — results differ from committed baseline (human review required)"
        {
          echo "### \`$CASE_LABEL\` — ⚠️ Results differ from committed baseline (human review required)"
          echo ""
          echo "<details><summary>Diff details</summary>"
          echo ""
          echo '```'
          cat "$DIFF_LOG"
          echo '```'
          echo "</details>"
          echo ""
        } >> "$REPORT_FILE"
        PASSED_CASES=$((PASSED_CASES + 1))   # diff is a warning, not a job failure
      else
        echo "  ERROR: diff script failed (exit $DIFF_EXIT)"
        {
          echo "### \`$CASE_LABEL\` — ❌ Diff script error"
          echo ""
          echo '```'
          cat "$DIFF_LOG"
          echo '```'
          echo ""
        } >> "$REPORT_FILE"
        FAILED_CASES=$((FAILED_CASES + 1))
        OVERALL_SUCCESS=false
      fi

      rm -f "$COMMITTED_RESULTS"
    else
      # No prior results — post full output for human review
      echo "  NEW — no prior results.json; posting for human review"
      NEW_CASES=$((NEW_CASES + 1))
      {
        echo "### \`$CASE_LABEL\` — 🆕 New results (no prior baseline — human review required)"
        echo ""
        echo "<details><summary>View results.json</summary>"
        echo ""
        echo '```json'
        cat "$RESULTS_DIR/results.json"
        echo '```'
        echo "</details>"
        echo ""
      } >> "$REPORT_FILE"
    fi

    # Always attach engine log for debugging
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
  printf "**Summary:** %d passed/updated" "$PASSED_CASES"
  [ $NEW_CASES -gt 0 ]    && printf " | %d new (human review required)" "$NEW_CASES"
  [ $FAILED_CASES -gt 0 ] && printf " | %d engine errors" "$FAILED_CASES"
  printf " (Total: %d test cases)\n" "$TOTAL_CASES"
  echo ""
} >> "$REPORT_FILE"

if [ "$OVERALL_SUCCESS" = false ]; then
  exit 1
fi
