"""
Runtime Hook für PyInstaller
Setzt das Working Directory auf einen geeigneten Speicherort
"""
import os
import sys
from pathlib import Path

# Ermittle den App Support Ordner für macOS
if sys.platform == 'darwin':
    app_support = Path.home() / 'Library' / 'Application Support' / 'AudioSessions'
elif sys.platform == 'win32':
    app_support = Path(os.getenv('APPDATA')) / 'AudioSessions'
else:
    app_support = Path.home() / '.audiosessions'

# Erstelle den Ordner falls nicht vorhanden
app_support.mkdir(parents=True, exist_ok=True)

# Setze Working Directory
os.chdir(app_support)

# Erstelle Unterordner
(app_support / 'data').mkdir(exist_ok=True)
(app_support / 'recordings').mkdir(exist_ok=True)

print(f"AudioSessions: Working directory set to {app_support}")
