#!/bin/bash
# Installiert Autostart für Corporate Digital Brain Recorder

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$SCRIPT_DIR/cdb-recorder.desktop"

echo "📦 Installiere Autostart für CDB Recorder..."

# Erstelle Autostart-Verzeichnis falls nicht vorhanden
mkdir -p "$AUTOSTART_DIR"

# Kopiere Desktop-Datei in Autostart
cp "$DESKTOP_FILE" "$AUTOSTART_DIR/"

echo "✅ Autostart wurde installiert!"
echo ""
echo "Die App startet jetzt automatisch beim Login."
echo ""
echo "Zum Deaktivieren verwende: ./remove-autostart.sh"
