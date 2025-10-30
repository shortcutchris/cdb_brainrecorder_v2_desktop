#!/bin/bash
# Corporate Digital Brain Desktop Recorder Starter

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Setze UTF-8 Locale für korrekte Encoding-Unterstützung (wichtig für Raspberry Pi)
export LANG=de_DE.UTF-8
export LC_ALL=de_DE.UTF-8
export PYTHONIOENCODING=utf-8

# Aktiviere Virtual Environment
source venv/bin/activate

# Starte App
python3 app.py

# Deaktiviere venv nach Beenden
deactivate
