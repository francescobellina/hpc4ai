#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing .venv. Run ./scripts/setup-env.sh first." >&2
  exit 1
fi

if command -v uv >/dev/null 2>&1; then
  exec uv run --python .venv/bin/python jupyter book start
else
  exec .venv/bin/jupyter book start
fi
