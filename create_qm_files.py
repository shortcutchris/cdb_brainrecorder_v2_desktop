"""
Erstellt funktionierende .qm Dateien aus .ts Dateien
"""
import xml.etree.ElementTree as ET
from pathlib import Path
import struct

class QMWriter:
    """Schreibt .qm Dateien im Qt-Format"""

    def __init__(self):
        self.messages = []

    def add_message(self, context, source, translation):
        """Fügt eine Nachricht hinzu"""
        self.messages.append({
            'context': context,
            'source': source,
            'translation': translation
        })

    def write(self, output_file):
        """Schreibt die .qm Datei"""
        with open(output_file, 'wb') as f:
            # Qt QM Magic Number
            f.write(b'\x3c\xb8\x64\x18\xca\xef\x9c\x95')

            # Contexts Section
            contexts = {}
            for msg in self.messages:
                ctx = msg['context']
                if ctx not in contexts:
                    contexts[ctx] = []
                contexts[ctx].append(msg)

            # Write contexts
            for context_name, msgs in contexts.items():
                # Context name length and name
                ctx_bytes = context_name.encode('utf-8')
                f.write(struct.pack('>H', len(ctx_bytes)))
                f.write(ctx_bytes)

                # Number of messages
                f.write(struct.pack('>I', len(msgs)))

                # Write messages
                for msg in msgs:
                    src_bytes = msg['source'].encode('utf-8')
                    trans_bytes = msg['translation'].encode('utf-8')

                    # Source length and source
                    f.write(struct.pack('>I', len(src_bytes)))
                    f.write(src_bytes)

                    # Translation length and translation
                    f.write(struct.pack('>I', len(trans_bytes)))
                    f.write(trans_bytes)

def parse_ts_file(ts_file):
    """Parsed eine .ts Datei"""
    tree = ET.parse(ts_file)
    root = tree.getroot()

    writer = QMWriter()

    for context in root.findall('.//context'):
        context_name = context.find('name').text

        for message in context.findall('message'):
            source_elem = message.find('source')
            trans_elem = message.find('translation')

            if source_elem is not None and trans_elem is not None:
                source_text = source_elem.text or ""
                trans_text = trans_elem.text

                # Skip wenn keine Übersetzung vorhanden
                if trans_text:
                    writer.add_message(context_name, source_text, trans_text)

    return writer

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

    print(f"Erstelle .qm Dateien...\n")

    for ts_file in ts_files:
        qm_file = ts_file.with_suffix(".qm")
        print(f"Verarbeite: {ts_file.name}")

        try:
            writer = parse_ts_file(ts_file)
            writer.write(qm_file)
            print(f"  ✓ Erstellt: {qm_file.name} ({len(writer.messages)} Übersetzungen)")
        except Exception as e:
            print(f"  ✗ Fehler: {e}")
            import traceback
            traceback.print_exc()

    print("\nFertig!")

if __name__ == "__main__":
    main()
