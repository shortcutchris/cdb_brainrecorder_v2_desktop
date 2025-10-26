#!/bin/bash

# Fix App Permissions - Patcht Info.plist und signiert die App neu
# Verwendung: ./fix_app_permissions.sh

set -e

APP_NAME="CorporateDigitalBrainRecorder.app"
APP_PATH="dist/$APP_NAME"
INFO_PLIST="$APP_PATH/Contents/Info.plist"
ENTITLEMENTS="entitlements.plist"

echo "🔧 Fixe Berechtigungen für $APP_NAME..."

# Prüfe ob App existiert
if [ ! -d "$APP_PATH" ]; then
    echo "❌ Fehler: $APP_PATH nicht gefunden!"
    echo "   Bitte zuerst die App bauen: ./venv/bin/pyinstaller AudioSessions.spec --clean"
    exit 1
fi

# Prüfe ob Info.plist existiert
if [ ! -f "$INFO_PLIST" ]; then
    echo "❌ Fehler: $INFO_PLIST nicht gefunden!"
    exit 1
fi

echo "📝 Patche Info.plist..."

# Backup der Original Info.plist (außerhalb der .app)
cp "$INFO_PLIST" "Info.plist.backup"

# Erstelle temporäre Datei mit NSMicrophoneUsageDescription
# Füge den Key vor dem schließenden </dict> ein
sed -i '' '/<\/dict>/i\
	<key>NSMicrophoneUsageDescription</key>\
	<string>Corporate Digital Brain Desktop Recorder benötigt Zugriff auf das Mikrofon um Audio-Aufnahmen zu erstellen.</string>
' "$INFO_PLIST"

echo "✅ NSMicrophoneUsageDescription hinzugefügt"

# Prüfe ob entitlements.plist existiert
if [ ! -f "$ENTITLEMENTS" ]; then
    echo "❌ Fehler: $ENTITLEMENTS nicht gefunden!"
    exit 1
fi

echo "🔐 Signiere App mit Entitlements..."

# Entferne alte Signatur
find "$APP_PATH" -name "_CodeSignature" -exec rm -rf {} + 2>/dev/null || true

# Signiere App mit ad-hoc Signatur und Entitlements
codesign --force --deep --sign - --entitlements "$ENTITLEMENTS" "$APP_PATH"

echo "✅ App signiert"

# Entferne Quarantine-Attribute
echo "🧹 Entferne Quarantine-Attribute..."
xattr -cr "$APP_PATH"

echo "✅ Quarantine-Attribute entfernt"

# Verifiziere Signatur
echo "🔍 Verifiziere Signatur..."
codesign --verify --verbose "$APP_PATH"

if [ $? -eq 0 ]; then
    echo "✅ Signatur verifiziert"
else
    echo "❌ Signatur-Verifizierung fehlgeschlagen"
    exit 1
fi

# Zeige Entitlements an
echo ""
echo "📋 Entitlements der signierten App:"
codesign -d --entitlements - "$APP_PATH"

echo ""
echo "✅ Fertig! Die App ist bereit:"
echo "   $APP_PATH"
echo ""
echo "   Starte mit: open \"$APP_PATH\""
