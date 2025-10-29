@echo off
REM ============================================================================
REM Build Script für Corporate Digital Brain Desktop Recorder - Windows
REM ============================================================================
REM
REM Dieses Script baut die Windows .exe Version der App mit PyInstaller
REM
REM Voraussetzungen:
REM   - Python 3.9+ installiert
REM   - ffmpeg & ffprobe im PATH (siehe WINDOWS_BUILD.md)
REM
REM ============================================================================

setlocal enabledelayedexpansion

set APP_NAME=CorporateDigitalBrainRecorder

echo.
echo ============================================
echo   Windows Build - %APP_NAME%
echo ============================================
echo.

REM ============================================================================
REM 1. Prüfe Python Installation
REM ============================================================================
echo [1/6] Pruefe Python Installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python ist nicht installiert oder nicht im PATH!
    echo Bitte installieren Sie Python 3.9 oder hoeher von python.org
    pause
    exit /b 1
)
python --version
echo.

REM ============================================================================
REM 2. Erstelle/Aktiviere virtuelles Environment
REM ============================================================================
echo [2/6] Pruefe virtuelles Environment...
if not exist "venv\" (
    echo Erstelle neues virtuelles Environment...
    python -m venv venv
    if errorlevel 1 (
        echo FEHLER: Konnte venv nicht erstellen!
        pause
        exit /b 1
    )
    echo Virtuelles Environment erstellt.
)

REM Aktiviere venv
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo FEHLER: Konnte venv nicht aktivieren!
    pause
    exit /b 1
)
echo Virtuelles Environment aktiviert.
echo.

REM ============================================================================
REM 3. Installiere Dependencies
REM ============================================================================
echo [3/6] Installiere Python Dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo FEHLER: Konnte Dependencies nicht installieren!
    pause
    exit /b 1
)
echo Dependencies installiert.
echo.

REM ============================================================================
REM 4. Prüfe ffmpeg Installation
REM ============================================================================
echo [4/6] Pruefe ffmpeg Installation...
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo.
    echo ============================================
    echo   WARNUNG: ffmpeg nicht gefunden!
    echo ============================================
    echo.
    echo ffmpeg wird fuer die Audio-Transkription benoetigt.
    echo.
    echo Bitte installieren Sie ffmpeg:
    echo   1. Download: https://github.com/BtbN/FFmpeg-Builds/releases
    echo   2. Entpacken Sie ffmpeg.exe und ffprobe.exe
    echo   3. Fuegen Sie den Pfad zu PATH hinzu ODER
    echo   4. Kopieren Sie die .exe Dateien nach dist\%APP_NAME%\
    echo.
    echo Der Build wird fortgesetzt, aber Transkription wird nicht funktionieren
    echo ohne ffmpeg!
    echo.
    pause
) else (
    ffmpeg -version | findstr "ffmpeg version"
    echo ffmpeg gefunden.
)
echo.

REM ============================================================================
REM 5. Loesche alten Build
REM ============================================================================
echo [5/6] Loesche alten Build...
if exist "build\" rmdir /s /q build
if exist "dist\" rmdir /s /q dist
echo Alte Build-Dateien geloescht.
echo.

REM ============================================================================
REM 6. Baue App mit PyInstaller
REM ============================================================================
echo [6/6] Baue App mit PyInstaller...
echo Dies kann einige Minuten dauern...
echo.
pyinstaller AudioSessions_windows.spec --clean
if errorlevel 1 (
    echo.
    echo FEHLER: PyInstaller Build fehlgeschlagen!
    pause
    exit /b 1
)

REM Pruefe ob Build erfolgreich war
if not exist "dist\%APP_NAME%\%APP_NAME%.exe" (
    echo.
    echo FEHLER: dist\%APP_NAME%\%APP_NAME%.exe wurde nicht erstellt!
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build erfolgreich abgeschlossen!
echo ============================================
echo.
echo Die fertige App befindet sich in:
echo   dist\%APP_NAME%\
echo.
echo Zum Starten:
echo   dist\%APP_NAME%\%APP_NAME%.exe
echo.
echo WICHTIG: Falls ffmpeg nicht im PATH ist,
echo kopieren Sie ffmpeg.exe und ffprobe.exe nach:
echo   dist\%APP_NAME%\
echo.
echo Weitere Informationen: WINDOWS_BUILD.md
echo.
pause
