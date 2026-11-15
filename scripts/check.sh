#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_CHECK="python3"
if [[ -x .venv/bin/python ]]; then
  PYTHON_CHECK=".venv/bin/python"
fi

"$PYTHON_CHECK" - <<'PYCHECK'
from pathlib import Path
import yaml

for name in ["myst.yml", "toc.yml"]:
    with open(name, encoding="utf-8") as f:
        yaml.safe_load(f)

required = [
    "content/index.md",
    "content/teoria/01-architetture.md",
    "content/esercizi/index.md",
    "content/relazione/index.md",
    "content/workflow/overview.md",
    "content/workflow/lab-client-wilson.md",
]
missing = [p for p in required if not Path(p).exists()]
if missing:
    raise SystemExit("Missing required files: " + ", ".join(missing))

print("Basic project structure: OK")
PYCHECK

if [[ -x .venv/bin/python ]]; then
  if command -v uv >/dev/null 2>&1; then
    exec uv run --python .venv/bin/python jupyter book build --html --strict
  else
    exec .venv/bin/jupyter book build --html --strict
  fi
else
  exec jupyter book build --html --strict
fi
