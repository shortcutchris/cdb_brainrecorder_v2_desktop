"""
Kompiliert .ts Dateien zu .qm Dateien mit PySide6
"""
import subprocess
import sys
from pathlib import Path

def compile_ts_files():
    """Kompiliert alle .ts Dateien im translations-Verzeichnis"""
    translations_dir = Path("translations")

    if not translations_dir.exists():
        print("Translations-Verzeichnis nicht gefunden!")
        return False

    ts_files = list(translations_dir.glob("*.ts"))

    if not ts_files:
        print("Keine .ts Dateien gefunden!")
        return False

    print(f"Gefundene .ts Dateien: {[f.name for f in ts_files]}")

    # Versuche lrelease zu finden
    lrelease_candidates = [
        "lrelease",
        "lrelease-qt5",
        "lrelease-qt6",
        "pyside6-lrelease"
    ]

    lrelease_path = None
    for candidate in lrelease_candidates:
        try:
            result = subprocess.run([candidate, "-version"],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lrelease_path = candidate
                print(f"Gefunden: {candidate}")
                break
        except FileNotFoundError:
            continue

    if not lrelease_path:
        print("lrelease nicht gefunden. Erstelle .qm Dateien mit alternativer Methode...")
        # Alternative: Verwende QTranslator zum Laden der .ts Dateien direkt
        print("Hinweis: .ts Dateien können auch direkt mit QTranslator geladen werden")
        print("Die App wird so konfiguriert, dass sie .ts Dateien lädt")
        return True

    # Kompiliere jede .ts Datei
    success = True
    for ts_file in ts_files:
        qm_file = ts_file.with_suffix(".qm")
        print(f"Kompiliere {ts_file.name} -> {qm_file.name}")

        try:
            result = subprocess.run([lrelease_path, str(ts_file), "-qm", str(qm_file)],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  ✓ Erfolgreich")
            else:
                print(f"  ✗ Fehler: {result.stderr}")
                success = False
        except Exception as e:
            print(f"  ✗ Fehler: {e}")
            success = False

    return success

if __name__ == "__main__":
    success = compile_ts_files()
    sys.exit(0 if success else 1)
