#!/bin/bash

# Build Script für Corporate Digital Brain Desktop Recorder
# Baut die .app mit PyInstaller und patcht automatisch die Berechtigungen

set -e

APP_NAME="CorporateDigitalBrainRecorder.app"

echo "🚀 Baue Corporate Digital Brain Desktop Recorder..."
echo ""

# Prüfe ob venv existiert
if [ ! -d "venv" ]; then
    echo "❌ Fehler: Virtuelles Environment nicht gefunden!"
    echo "   Bitte zuerst installieren: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Prüfe ob PyInstaller installiert ist
if ! ./venv/bin/python3 -c "import PyInstaller" 2>/dev/null; then
    echo "⚠️  PyInstaller nicht gefunden, installiere..."
    ./venv/bin/pip install pyinstaller
fi

# Lösche alten Build
echo "🧹 Lösche alten Build..."
rm -rf build dist

# Baue App mit PyInstaller
echo ""
echo "🔨 Baue App mit PyInstaller..."
./venv/bin/pyinstaller AudioSessions.spec --clean

if [ ! -d "dist/$APP_NAME" ]; then
    echo "❌ Build fehlgeschlagen: dist/$APP_NAME nicht gefunden!"
    exit 1
fi

echo "✅ PyInstaller Build abgeschlossen"
echo ""

# Führe Permission-Fix aus
echo "🔧 Fixe Berechtigungen..."
./fix_app_permissions.sh

echo ""
echo "🎉 Build erfolgreich abgeschlossen!"
echo ""
echo "📦 Die fertige App befindet sich in:"
echo "   dist/$APP_NAME"
echo ""
echo "🚀 Starten mit:"
echo "   open \"dist/$APP_NAME\""
echo ""
echo "📁 Installation (optional):"
echo "   cp -r \"dist/$APP_NAME\" /Applications/"
echo ""
