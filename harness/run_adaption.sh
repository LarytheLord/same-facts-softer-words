#!/bin/bash
# Live run via Adaption hosted models. Reads key `adaptive` from ~/Documents/AI/.env; never prints it.
set -euo pipefail
KEYLINE=$(grep -E '^[[:space:]]*adaptive[[:space:]]*=' "$HOME/Documents/AI/.env" | head -1)
VAL="${KEYLINE#*=}"; VAL="${VAL//\"/}"; VAL="${VAL//\'/}"; VAL="$(echo -n "$VAL" | tr -d '[:space:]')"
export ADAPTION_API_KEY="$VAL" BACKEND=adaption
exec "${PYTHON:-python3}" "$(dirname "$0")/run.py" --live "$@"
