#!/usr/bin/env bash
# Optional local detector; preserves the application's explicit on/off choice.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
"$root/venv-local-ai/bin/python" -m pip install -r "$root/requirements-wake.txt"
cd "$root"
"$root/venv-local-ai/bin/python" -m scripts.install_wake_model
