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
    "content/workflow/overview.md",
    "content/workflow/lab-client-wilson.md",
    "content/lectures/lecture01/index.md",
]
missing = [p for p in required if not Path(p).exists()]
if missing:
    raise SystemExit("Missing required files: " + ", ".join(missing))

for i in range(1, 14):
    base = Path(f"content/lectures/lecture{i:02d}")
    for rel in ["index.md", "theory.md", "examples.md", "exercises", "notebooks", "code", "data", "figures"]:
        if not (base / rel).exists():
            raise SystemExit(f"Missing lecture component: {base / rel}")

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
