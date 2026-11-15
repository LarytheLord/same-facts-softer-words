#!/bin/bash
# Live run on Claude. Reads key `anthropic` from ~/Documents/AI/.env; never prints it.
set -euo pipefail
KEYLINE=$(grep -E '^[[:space:]]*anthropic[[:space:]]*=' "$HOME/Documents/AI/.env" | head -1)
VAL="${KEYLINE#*=}"; VAL="${VAL//\"/}"; VAL="${VAL//\'/}"; VAL="$(echo -n "$VAL" | tr -d '[:space:]')"
export ANTHROPIC_API_KEY="$VAL"
exec "${PYTHON:-python3}" "$(dirname "$0")/run.py" --live "$@"
