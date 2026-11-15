#!/bin/bash
# Generator on Groq (BASE_URL/API_KEY), checker on Adaption via --checker-model adaption:<id>.
# Reads keys from local config files; never prints them.
set -euo pipefail
KEYLINE=$(grep -E '^[[:space:]]*adaptive[[:space:]]*=' "$HOME/Documents/AI/.env" | head -1)
VAL="${KEYLINE#*=}"; VAL="${VAL//\"/}"; VAL="${VAL//\'/}"; VAL="$(echo -n "$VAL" | tr -d '[:space:]')"
export ADAPTION_API_KEY="$VAL"
exec "$(dirname "$0")/synth_groq.sh" "$@"
