#!/usr/bin/env bash
# Optional local detector; leaves Wake Word switched off in the application.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
"$root/venv-local-ai/bin/python" -m pip install -r "$root/requirements-wake.txt"
"$root/venv-local-ai/bin/python" -c 'from pymicro_wakeword import MicroWakeWord, Model; MicroWakeWord.from_builtin(Model.OKAY_NABU); print("Okay Nabu: lokale Laufzeit bereit")'
