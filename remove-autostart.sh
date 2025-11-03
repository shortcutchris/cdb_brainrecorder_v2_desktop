#!/bin/bash
# Entfernt Autostart für Corporate Digital Brain Recorder

AUTOSTART_FILE="$HOME/.config/autostart/cdb-recorder.desktop"

echo "🗑️  Entferne Autostart für CDB Recorder..."

if [ -f "$AUTOSTART_FILE" ]; then
    rm "$AUTOSTART_FILE"
    echo "✅ Autostart wurde entfernt!"
    echo ""
    echo "Die App startet nicht mehr automatisch beim Login."
    echo ""
    echo "Zum erneuten Aktivieren verwende: ./install-autostart.sh"
else
    echo "⚠️  Autostart war nicht installiert."
fi
