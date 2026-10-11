#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"
export LANG=de_DE.UTF-8 LC_ALL=de_DE.UTF-8 PYTHONIOENCODING=utf-8
runtime=venv-local-ai
if [[ ! -x "$runtime/bin/python" ]]; then
  echo 'Lokale Umgebung fehlt. Installation gemäß docs/LOCAL_AI.md durchführen.' >&2
  exit 1
fi
exec "$runtime/bin/python" app.py
