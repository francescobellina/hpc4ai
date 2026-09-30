#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -x .venv/bin/python ]]; then
  if command -v uv >/dev/null 2>&1; then
    exec uv run --python .venv/bin/python jupyter book build --html --strict
  else
    exec .venv/bin/jupyter book build --html --strict
  fi
else
  exec jupyter book build --html --strict
fi
