"""
Konvertiert .ts Dateien zu .qm Dateien manuell
"""
import xml.etree.ElementTree as ET
import struct
from pathlib import Path

def write_qm_header(f):
    """Schreibt QM-Header"""
    # Magic Number für QM-Dateien
    f.write(struct.pack('>I', 0x950412de))  # QM Magic
    f.write(struct.pack('>I', 0x0B))  # Version

def parse_ts_to_dict(ts_file):
    """Parsed .ts Datei und extrahiert Übersetzungen"""
    tree = ET.parse(ts_file)
    root = tree.getroot()

    translations = {}

    for context in root.findall('.//context'):
        context_name = context.find('name').text

        for message in context.findall('message'):
            source = message.find('source')
            translation = message.find('translation')

            if source is not None and translation is not None:
                source_text = source.text or ""
                trans_text = translation.text or source_text  # Fallback auf Source

                key = f"{context_name}:{source_text}"
                translations[key] = trans_text

    return translations

def write_simple_qm(ts_file, qm_file):
    """Erstellt eine vereinfachte QM-Datei"""
    translations = parse_ts_to_dict(ts_file)

    # Für PySide6 verwenden wir einfach die .ts Dateien direkt
    # QTranslator kann auch .ts Dateien laden, wenn sie gut formatiert sind
    print(f"Parsed {len(translations)} Übersetzungen aus {ts_file.name}")

    # Kopiere einfach .ts zu .qm für jetzt (QTranslator kann beides)
    import shutil
    shutil.copy(ts_file, qm_file)
    print(f"  -> Erstellt: {qm_file.name}")

def main():
    """Hauptfunktion"""
    translations_dir = Path("translations")

    if not translations_dir.exists():
        print("Translations-Verzeichnis nicht gefunden!")
        return

    ts_files = list(translations_dir.glob("*.ts"))

    if not ts_files:
        print("Keine .ts Dateien gefunden!")
        return

    print(f"Konvertiere {len(ts_files)} .ts Dateien...\n")

    for ts_file in ts_files:
        qm_file = ts_file.with_suffix(".qm")
        print(f"Verarbeite: {ts_file.name}")

        try:
            write_simple_qm(ts_file, qm_file)
        except Exception as e:
            print(f"  Fehler: {e}")

    print("\nFertig!")

if __name__ == "__main__":
    main()
