#!/bin/bash
# Live run via Groq's OpenAI-compatible API. Reads GROQ_API_KEY from ~/.config/groq/config.env; never prints it.
set -euo pipefail
KEYLINE=$(grep -E '^GROQ_API_KEY=' "$HOME/.config/groq/config.env" | head -1)
export API_KEY="${KEYLINE#GROQ_API_KEY=}"
export BASE_URL="https://api.groq.com/openai/v1"
exec "${PYTHON:-python3}" "$(dirname "$0")/run.py" --live "$@"
