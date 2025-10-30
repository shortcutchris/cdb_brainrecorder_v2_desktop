#!/bin/bash
################################################################################
# Build Script für Corporate Digital Brain Desktop Recorder - Linux/Raspberry Pi
################################################################################
#
# Dieses Script baut die App für Linux-basierte Systeme (inkl. Raspberry Pi)
#
# Voraussetzungen:
#   - Python 3.9+
#   - Desktop-Umgebung (X11 oder Wayland)
#   - Audio-Treiber (ALSA/PulseAudio)
#
# HINWEIS: Auf Raspberry Pi ist es oft einfacher, die App direkt mit
# Python zu starten statt einen PyInstaller Build zu erstellen.
# Siehe RASPBERRY_PI_BUILD.md für Details.
#
################################################################################

set -e

APP_NAME="CorporateDigitalBrainRecorder"

echo ""
echo "========================================"
echo "  Linux/Raspberry Pi Build"
echo "  $APP_NAME"
echo "========================================"
echo ""

################################################################################
# 1. System-Check
################################################################################
echo "[1/7] Pruefe System..."

# Check OS
if [[ "$(uname)" != "Linux" ]]; then
    echo "FEHLER: Dieses Script ist nur fuer Linux-Systeme!"
    exit 1
fi

# Check if Raspberry Pi
IS_RPI=false
if [[ -f /proc/device-tree/model ]]; then
    MODEL=$(cat /proc/device-tree/model)
    if [[ "$MODEL" == *"Raspberry Pi"* ]]; then
        IS_RPI=true
        echo "✓ Raspberry Pi erkannt: $MODEL"
    fi
fi

# Check architecture
ARCH=$(uname -m)
echo "✓ Architektur: $ARCH"

if [[ "$ARCH" == "armv"* ]] || [[ "$ARCH" == "aarch64" ]]; then
    echo "✓ ARM-Prozessor erkannt"
    if [[ "$IS_RPI" == false ]]; then
        echo "  (Vermutlich Raspberry Pi oder aehnliches Geraet)"
    fi
fi

echo ""

################################################################################
# 2. Prüfe/Installiere System-Dependencies
################################################################################
echo "[2/7] Pruefe System-Dependencies..."

MISSING_DEPS=()

# Prüfe wichtige Pakete
for pkg in python3 python3-pip python3-venv ffmpeg portaudio19-dev libsndfile1; do
    if ! dpkg -l | grep -q "^ii  $pkg"; then
        MISSING_DEPS+=("$pkg")
    fi
done

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo ""
    echo "Fehlende Pakete gefunden: ${MISSING_DEPS[*]}"
    echo ""
    read -p "Soll ich diese jetzt installieren? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installiere fehlende Pakete..."
        sudo apt-get update
        sudo apt-get install -y "${MISSING_DEPS[@]}"
        echo "✓ Pakete installiert"
    else
        echo "FEHLER: Bitte installieren Sie die Pakete manuell:"
        echo "  sudo apt-get install ${MISSING_DEPS[*]}"
        exit 1
    fi
else
    echo "✓ Alle System-Dependencies vorhanden"
fi

echo ""

################################################################################
# 3. Python Version prüfen
################################################################################
echo "[3/7] Pruefe Python Version..."

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

echo "✓ Python $PYTHON_VERSION gefunden"

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo "WARNUNG: Python 3.9+ wird empfohlen. Sie haben $PYTHON_VERSION"
    echo "         Die App funktioniert moeglicherweise nicht korrekt."
fi

echo ""

################################################################################
# 4. Erstelle/Aktiviere Virtual Environment
################################################################################
echo "[4/7] Pruefe Virtual Environment..."

if [ ! -d "venv" ]; then
    echo "Erstelle Virtual Environment..."
    python3 -m venv venv
    echo "✓ Virtual Environment erstellt"
else
    echo "✓ Virtual Environment existiert bereits"
fi

source venv/bin/activate
echo "✓ Virtual Environment aktiviert"

echo ""

################################################################################
# 5. Installiere Python Dependencies
################################################################################
echo "[5/7] Installiere Python Dependencies..."

pip install --upgrade pip
pip install -r requirements.txt

echo "✓ Dependencies installiert"
echo ""

################################################################################
# 6. Wähle Build-Methode
################################################################################
echo "[6/7] Waehle Build-Methode..."
echo ""
echo "Es gibt zwei Moeglichkeiten die App zu nutzen:"
echo ""
echo "  [1] PyInstaller Build (erstellt standalone Binary)"
echo "      + Vorteil: Einzelne ausfuehrbare Datei"
echo "      - Nachteil: Langsam auf Raspberry Pi, groesser"
echo ""
echo "  [2] Direkt mit Python starten (empfohlen fuer Raspberry Pi)"
echo "      + Vorteil: Schneller Start, weniger Speicher"
echo "      - Nachteil: Benoetigt Python + venv"
echo ""

# Wenn Raspberry Pi: Empfehle Option 2
if [[ "$IS_RPI" == true ]]; then
    echo "EMPFEHLUNG fuer Raspberry Pi: Option 2 (Direkt mit Python)"
    echo ""
fi

read -p "Ihre Wahl (1 oder 2): " -n 1 -r
echo
echo ""

if [[ $REPLY =~ ^[1]$ ]]; then
    ################################################################################
    # Option 1: PyInstaller Build
    ################################################################################
    echo "[7/7] Baue App mit PyInstaller..."
    echo "Dies kann auf Raspberry Pi mehrere Minuten dauern..."
    echo ""

    # Loesche alten Build
    rm -rf build dist

    # Baue mit PyInstaller
    pyinstaller AudioSessions_linux.spec --clean

    if [ ! -f "dist/$APP_NAME/$APP_NAME" ]; then
        echo ""
        echo "FEHLER: Build fehlgeschlagen!"
        echo "dist/$APP_NAME/$APP_NAME wurde nicht erstellt"
        exit 1
    fi

    echo ""
    echo "========================================"
    echo "  Build erfolgreich!"
    echo "========================================"
    echo ""
    echo "Die fertige App befindet sich in:"
    echo "  dist/$APP_NAME/"
    echo ""
    echo "Zum Starten:"
    echo "  ./dist/$APP_NAME/$APP_NAME"
    echo ""
    echo "Oder Desktop-Starter erstellen:"
    echo "  siehe RASPBERRY_PI_BUILD.md"
    echo ""

elif [[ $REPLY =~ ^[2]$ ]]; then
    ################################################################################
    # Option 2: Python-Runner erstellen
    ################################################################################
    echo "[7/7] Erstelle Start-Script..."

    # Erstelle run.sh Script
    cat > run.sh << 'EOF'
#!/bin/bash
# Corporate Digital Brain Desktop Recorder Starter

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Aktiviere Virtual Environment
source venv/bin/activate

# Starte App
python3 app.py

# Deaktiviere venv nach Beenden
deactivate
EOF

    chmod +x run.sh

    echo ""
    echo "========================================"
    echo "  Setup erfolgreich!"
    echo "========================================"
    echo ""
    echo "Zum Starten der App:"
    echo "  ./run.sh"
    echo ""
    echo "Oder Desktop-Starter erstellen:"
    echo "  siehe RASPBERRY_PI_BUILD.md"
    echo ""
else
    echo "Ungueltige Eingabe. Abbruch."
    exit 1
fi

echo "Weitere Informationen: RASPBERRY_PI_BUILD.md"
echo ""
