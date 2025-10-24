# 🎧 Product Requirements Document (PRD)
## Projekt: Audio Sessions – Desktop App
**Version:** 1.0  
**Letzte Aktualisierung:** 25. Oktober 2025  
**Verantwortlich:** [Dein Name]

---

## 1. Produktübersicht

### 1.1 Zielsetzung
Die Anwendung soll es Nutzer:innen ermöglichen, **Audio-Sessions einfach aufzuzeichnen, zu verwalten und wiederzugeben**.
Sie kombiniert eine **einfache Recorder-Funktion** (Mikrofonaufnahme) mit einer **CRUD-Verwaltung** (Create, Read, Update, Delete) für aufgezeichnete Sessions, Metadaten und Notizen.

### 1.2 Hauptnutzergruppen
- **Musiker:innen / Podcaster:innen** – wollen spontane Ideen festhalten und dokumentieren.  
- **Therapeut:innen / Coaches** – möchten Gespräche oder Sitzungen (mit Zustimmung) protokollieren.  
- **Forscher:innen / Entwickler:innen** – wollen Audio-Experimente oder Interviews aufzeichnen und archivieren.  

### 1.3 Zielplattformen
- **macOS (12+)**  
- **Windows 10/11**  
Cross-platform über **Python + Qt (PySide6)**.

---

## 2. Hauptfunktionen (MVP)

| Kategorie | Funktion | Beschreibung |
|------------|-----------|---------------|
| **Audioaufnahme** | Aufnahme starten/stoppen | Audio wird über das gewählte Mikrofon als WAV-Datei aufgezeichnet. |
| | Geräteauswahl | Auswahl zwischen allen verfügbaren Eingabegeräten. |
| | Live-Pegelanzeige | RMS-Pegelbalken in Echtzeit. |
| | Laufzeit-Anzeige | Anzeige der aktuellen Aufnahmedauer. |
| | Automatische Dateinamen | Zeitstempel-basierte Benennung (`session_YYYY-MM-DD_HH-MM-SS.wav`). |
| **Session-Verwaltung (CRUD)** | Neue Session | Manuelles Anlegen eines Datensatzes mit Titel, Notizen, Pfad etc. |
| | Lesen / Durchsuchen | Tabellenansicht aller Sessions mit Filterung (Suche nach Titel/Notizen). |
| | Bearbeiten | Editiermaske für Metadaten (Titel, Datum, Dauer, Notizen usw.). |
| | Löschen | Löschen eines Datensatzes inkl. Sicherheitsabfrage. |
| | CSV-Export | Export der Sessionliste in eine CSV-Datei. |
| | Datei öffnen | Öffnet die Audio-Datei im Standard-Audio-Player des Systems. |
| **Automatik** | Auto-Insert | Nach Aufnahme wird Session automatisch in DB gespeichert. |
| **Datenbank** | SQLite | Lokale, portable Datenbank `sessions.db`. |
| **UX/UI** | Modernes, schlichtes GUI mit Qt Widgets | Zwei Hauptbereiche: Sessions-Tabelle links, Recorder & Editor rechts. |

---

## 3. Erweiterungen (geplant, optional)

| Priorität | Feature | Beschreibung |
|------------|----------|--------------|
| 🔜 Hoch | **MP3-Export** | Export/Transkodierung via `pydub` + `ffmpeg`. |
| 🔜 Mittel | **Tags / Kategorien** | Zuordnung von Sessions zu Projekten oder Themen. |
| 🔜 Mittel | **Playback-Funktion** | Wiedergabe direkt in der App (QtMultimedia). |
| 🔜 Mittel | **Waveform-Vorschau** | Mini-Audiovisualisierung im Editor. |
| 🔜 Niedrig | **Cloud-Sync (z. B. Dropbox / GDrive)** | Automatische Sicherung von Sessions. |
| 🔜 Niedrig | **Mehrsprachigkeit (DE/EN)** | Übersetzbare UI über `.qm`-Dateien. |

---

## 4. Technische Architektur

### 4.1 Struktur
```
audio_sessions/
├── app.py
├── recorder.py
├── ui/
│   ├── main_window.py
│   ├── session_form.py
│   ├── table_widget.py
├── data/
│   ├── repo.py
│   └── sessions.db
├── recordings/
└── requirements.txt
```

### 4.2 Technologie-Stack
| Komponente | Bibliothek | Zweck |
|-------------|-------------|--------|
| GUI | **PySide6 (Qt)** | Cross-platform Desktop GUI |
| Audio I/O | **sounddevice + soundfile** | Aufnahme und WAV-Speicherung |
| Datenbank | **sqlite3** | Persistente Session-Verwaltung |
| Sprache | **Python 3.11+** | Hauptentwicklungssprache |
| Packaging | **PyInstaller** | Erzeugung von `.exe` / `.app` |

---

## 5. UX & Design

### 5.1 Layout
**Drei Kernbereiche:**
1. **Toolbar (oben)** – Suche, Aktionen (Neu, Bearbeiten, Löschen, Export, Öffnen)
2. **Sessions-Tabelle (links)** – alle Datensätze sortiert nach Datum
3. **Rechte Seite** – Recorder-Panel (oben) + Session-Formular (unten)

### 5.2 Designrichtlinien
- Schlicht, funktional, keine überladenen Farben  
- Verwendung von Icons (z. B. `QAction` mit Symbolen)  
- Einfache Navigation über Mausklicks, keine Mehrfensterstruktur  
- Fortschrittsbalken für Audio-Level  
- Hinweis auf Mikrofonberechtigung bei macOS  

---

## 6. Datenmodell (SQLite)

### Tabelle: `sessions`
| Feld | Typ | Beschreibung |
|------|-----|---------------|
| id | INTEGER PRIMARY KEY | Auto-ID |
| title | TEXT | Titel der Session |
| recorded_at | TEXT (ISO 8601) | Datum/Zeit der Aufnahme |
| duration_sec | INTEGER | Dauer in Sekunden |
| path | TEXT | Dateipfad zur Audiodatei |
| samplerate | INTEGER | Abtastrate |
| channels | INTEGER | Anzahl Kanäle |
| notes | TEXT | Freitextfeld für Notizen |

---

## 7. Entwicklungsplan

### Phase 1 – MVP (2–3 Wochen)
- [x] Recorder mit Live-Pegel + Laufzeit  
- [x] CRUD-Interface mit SQLite  
- [x] CSV-Export + Datei-Öffnen  
- [x] Packaging für macOS & Windows  

### Phase 2 – Erweiterungen (2 Wochen)
- [ ] Playback-Funktion  
- [ ] MP3-Export  
- [ ] Tags / Kategorien  
- [ ] Wellenform-Visualisierung  

### Phase 3 – Feinschliff (1–2 Wochen)
- [ ] Unit-Tests für Recorder & Repo  
- [ ] UI-Refinement & Icons  
- [ ] Installer-Erstellung (.exe / .dmg)

---

## 8. Technische Anforderungen & Risiken

| Bereich | Risiko | Gegenmaßnahme |
|----------|---------|---------------|
| macOS Mikrofonrechte | macOS blockiert Audioaufnahme ohne Plist-Eintrag | `NSMicrophoneUsageDescription` in Info.plist setzen |
| Audio-Treiber | Unterschiedliche Backends (WASAPI/CoreAudio) | sounddevice verwendet PortAudio (multiplattformfähig) |
| Datei-Zugriff | Aufnahmen können verloren gehen bei Crash | Schreiben im Thread + Flush nach jedem Block |
| UI-Blocking | Aufnahme darf UI nicht einfrieren | Threaded-Recorder mit Signalen |
| Datenverlust | Manuelles Löschen ohne Undo | Sicherheitsabfrage bei „Löschen“ |

---

## 9. Erfolgskriterien (KPIs)

- <1 Sekunde Startzeit  
- Aufnahme ohne Dropouts bei 44.1 kHz / 16 Bit / Mono  
- Speicherung & Anzeige von >100 Sessions stabil  
- Cross-platform build läuft ohne Fehlermeldungen  
- Nutzer kann innerhalb von 10 Sekunden eine Session aufnehmen und speichern

---

## 10. Lizenzierung & Veröffentlichung

- **Lizenz:** MIT oder proprietär (abhängig vom Projektziel)  
- **Distributionsform:**  
  - `.exe` (Windows, signiert)  
  - `.app` (macOS, signiert + notariert)  
- **Optionale Veröffentlichung:** GitHub oder eigener Download-Link
