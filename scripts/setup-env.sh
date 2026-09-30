#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
  if [[ ! -d .venv ]]; then
    uv venv --python 3.12
  fi
  uv pip install --python .venv/bin/python -r requirements.txt
  .venv/bin/python -m ipykernel install --user --name hpc4ai --display-name "Python (hpc4ai)" >/dev/null 2>&1 || true
  echo "Environment ready with uv: $(pwd)/.venv"
  echo "Preview with: uv run --python .venv/bin/python jupyter book start"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
  if [[ ! -d .venv ]]; then
    "$PYTHON_BIN" -m venv .venv
  fi
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
  .venv/bin/python -m ipykernel install --user --name hpc4ai --display-name "Python (hpc4ai)" >/dev/null 2>&1 || true
  echo "Environment ready: $(pwd)/.venv"
fi
