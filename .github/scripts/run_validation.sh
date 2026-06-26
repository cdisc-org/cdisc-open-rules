#!/usr/bin/env bash
# Thin wrapper — all logic lives in run_validation.py
set -euo pipefail
exec "${2:?python_cmd required}" "$(dirname "$0")/run_validation.py" "$@"
