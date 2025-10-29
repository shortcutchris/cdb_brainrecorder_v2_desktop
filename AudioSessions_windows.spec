# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File für Windows Build
Corporate Digital Brain Desktop Recorder
"""

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[
        # ffmpeg und ffprobe müssen auf Windows installiert sein
        # Entweder im PATH oder in dist/ kopiert werden
        # Siehe WINDOWS_BUILD.md für Details
    ],
    datas=[
        ('icon.png', '.'),           # Logo für Splash Screen
        ('translations', 'translations'),  # Übersetzungsdateien
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
    console=False,  # Keine Konsole anzeigen
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # Windows Icon
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

# HINWEIS: BUNDLE ist macOS-spezifisch und wird für Windows nicht verwendet
