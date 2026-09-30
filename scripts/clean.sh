#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf _build
printf 'Removed _build/\n'
