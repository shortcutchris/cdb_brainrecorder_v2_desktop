# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File für Linux/Raspberry Pi Build
Corporate Digital Brain Desktop Recorder

HINWEIS: Auf Raspberry Pi ist es oft einfacher, die App
direkt mit Python zu starten statt PyInstaller zu nutzen.
Siehe RASPBERRY_PI_BUILD.md für Details.
"""

import sys
from pathlib import Path

block_cipher = None

# Prüfe ob wir auf ARM (Raspberry Pi) sind
is_arm = 'arm' in sys.platform.lower() or 'aarch64' in sys.platform.lower()

# ffmpeg Pfad für Linux/Raspberry Pi
# Normalerweise installiert via: sudo apt-get install ffmpeg
ffmpeg_path = '/usr/bin/ffmpeg'
ffprobe_path = '/usr/bin/ffprobe'

binaries = []
# Nur hinzufügen wenn ffmpeg existiert
if Path(ffmpeg_path).exists():
    binaries.append((ffmpeg_path, '.'))
if Path(ffprobe_path).exists():
    binaries.append((ffprobe_path, '.'))

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=[
        ('icon.png', '.'),
        ('translations', 'translations'),
    ],
    hiddenimports=[
        'sounddevice',
        'soundfile',
        'cffi',
        'numpy',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hooks/runtime_hook.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CorporateDigitalBrainRecorder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Kein Terminal-Fenster
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CorporateDigitalBrainRecorder',
)

# Linux/Raspberry Pi hat kein BUNDLE wie macOS
# Das Ergebnis ist ein Ordner mit der Binary
