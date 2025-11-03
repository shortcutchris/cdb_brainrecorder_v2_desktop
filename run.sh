#!/bin/bash
# Corporate Digital Brain Desktop Recorder Starter

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Setze UTF-8 Locale für korrekte Encoding-Unterstützung (wichtig für Raspberry Pi)
export LANG=de_DE.UTF-8
export LC_ALL=de_DE.UTF-8
export PYTHONIOENCODING=utf-8

# Fullscreen-Modus (Standard: Auto-Detection in app.py)
# Überschreibe mit: FULLSCREEN=false ./run.sh (deaktiviert Fullscreen)
# Oder:             FULLSCREEN=true ./run.sh (erzwingt Fullscreen)
# Falls nicht gesetzt, startet Raspberry Pi automatisch im Fullscreen

# Aktiviere Virtual Environment
source venv/bin/activate

# Starte App
python3 app.py

# Deaktiviere venv nach Beenden
deactivate
