#!/usr/bin/env bash
# Copy the key from .env.openrouter into .env (without printing it) and restart the backend.
set -euo pipefail
cd "$(dirname "$0")/.."
key="$(grep -E '^LLM_API_KEY=' .env.openrouter | cut -d= -f2-)"
[ -n "$key" ] || { echo "Add your key to .env.openrouter first (LLM_API_KEY=...)."; exit 1; }
if grep -q '^LLM_API_KEY=' .env; then
  python3 - "$key" <<'PY'
import re, sys
text = open(".env").read()
open(".env", "w").write(re.sub(r"(?m)^LLM_API_KEY=.*$", lambda _: "LLM_API_KEY=" + sys.argv[1], text))
PY
else
  printf 'LLM_API_KEY=%s\n' "$key" >> .env
fi
docker compose up -d backend >/dev/null
echo "Key installed; backend restarted."
