# Audio Transcription + GPT-5 Integration Guide

**Für:** Audio Sessions Desktop App
**Stack:** `gpt-4o-transcribe` + `gpt-5` Responses API
**Stand:** Januar 2025

---

## Übersicht

Diese Anleitung beschreibt die Integration der neuesten OpenAI APIs für die Audio Sessions App:

1. **Audio Transkription** mit `gpt-4o-transcribe` (Sprache → Text)
2. **Text-Transformation** mit `gpt-5` Responses API (Prompts anwenden)

---

## 1. Audio Transkription (Sprache → Text)

### Modell: `gpt-4o-transcribe`

**Vorteile:**
- ✅ Höchste Transkriptions-Genauigkeit
- ✅ Token-basierte Abrechnung mit transparenter Usage
- ✅ Unterstützt alle Sprachen (Deutsch, Englisch, etc.)
- ✅ Multiple Response-Formate (JSON, Text, Verbose)

### Basis-Implementation

```python
from openai import OpenAI
from pathlib import Path

class AudioTranscriptionService:
    """Service für Audio-Transkription mit gpt-4o-transcribe"""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key)

    def transcribe(
        self,
        audio_file_path: str,
        language: str = "de",
        prompt: str = None
    ) -> dict:
        """
        Transkribiere Audio-Datei zu Text

        Args:
            audio_file_path: Pfad zur Audio-Datei (WAV, MP3, etc.)
            language: Sprache als ISO-639-1 Code ("de", "en")
            prompt: Optionaler Kontext-Prompt (max 224 Tokens)

        Returns:
            {
                "text": str,              # Vollständiger Transkript-Text
                "language": str,          # Erkannte Sprache
                "duration": float,        # Dauer in Sekunden
                "segments": list,         # Text-Segmente mit Timestamps
                "tokens_used": int        # Verbrauchte Tokens
            }
        """
        # Context-Prompt für bessere Genauigkeit
        if prompt is None:
            prompt = "Audio Sessions, Transkription, Notizen, Sprachaufnahme"

        with open(audio_file_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file,
                language=language,
                response_format="verbose_json",
                prompt=prompt
            )

        # Strukturierte Rückgabe
        return {
            "text": transcript.text,
            "language": transcript.language,
            "duration": transcript.duration,
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text
                }
                for seg in transcript.segments
            ],
            "tokens_used": transcript.usage.total_tokens,
            "usage_details": {
                "input_tokens": transcript.usage.input_tokens,
                "input_audio_tokens": transcript.usage.input_token_details.audio_tokens,
                "output_tokens": transcript.usage.output_tokens
            }
        }

# Verwendung
service = AudioTranscriptionService()

result = service.transcribe(
    audio_file_path="/path/to/session_001.wav",
    language="de"
)

print(f"Transkript: {result['text']}")
print(f"Dauer: {result['duration']:.2f}s")
print(f"Tokens: {result['tokens_used']}")
```

### Unterstützte Audio-Formate

- **WAV** - Empfohlen für Desktop-App (unkomprimiert)
- **MP3** - Komprimiert, kleinere Dateien
- **M4A** - Apple Audio Format
- **FLAC** - Verlustfreie Kompression
- **OGG**, **WEBM** - Web-Formate

**Max. Dateigröße:** 25 MB

### Response-Formate

#### `json` - Einfach
```json
{
  "text": "Dies ist die Transkription."
}
```

#### `verbose_json` - Mit Details (empfohlen!)
```json
{
  "text": "Dies ist die Transkription.",
  "language": "de",
  "duration": 12.5,
  "segments": [
    {
      "start": 0.0,
      "end": 3.2,
      "text": "Dies ist"
    }
  ]
}
```

---

## 2. Text-Transformation mit GPT-5

### Modell: `gpt-5` (Responses API)

**Vorteile:**
- ✅ Erweiterte Reasoning-Fähigkeiten
- ✅ Granulare Kontrolle über Output-Länge und Detail-Tiefe
- ✅ Chain of Thought zwischen Requests
- ✅ Custom Tools Support

**Wichtig:** Keine `temperature` oder `top_p` - stattdessen `reasoning.effort` und `text.verbosity`!

### Basis-Implementation

```python
from openai import OpenAI

class GPT5TransformationService:
    """Service für Text-Transformation mit GPT-5 Responses API"""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key)

    def transform(
        self,
        text: str,
        task: str = "zusammenfassen",
        reasoning_effort: str = "medium",
        verbosity: str = "medium"
    ) -> dict:
        """
        Transformiere Text mit GPT-5

        Args:
            text: Zu transformierender Text (z.B. Transkript)
            task: Transformations-Art ("zusammenfassen", "uebersetzen", "strukturieren")
            reasoning_effort: "minimal" | "low" | "medium" | "high"
            verbosity: "low" | "medium" | "high"

        Returns:
            {
                "result": str,           # Transformierter Text
                "tokens_used": int,      # Verbrauchte Tokens
                "reasoning_level": str,  # Verwendetes Reasoning-Level
                "verbosity_level": str   # Verwendetes Verbosity-Level
            }
        """
        # Task-spezifische Prompts
        task_prompts = {
            "zusammenfassen": (
                "Fasse den folgenden Transkript-Text prägnant zusammen. "
                "Behalte die wichtigsten Informationen und Kernaussagen bei. "
                "Strukturiere die Zusammenfassung übersichtlich."
            ),
            "uebersetzen": (
                "Übersetze den folgenden deutschen Text ins Englische. "
                "Achte auf natürliche Formulierungen und korrekte Terminologie."
            ),
            "strukturieren": (
                "Strukturiere den folgenden Transkript-Text übersichtlich. "
                "Erstelle Überschriften, Absätze und Stichpunkte. "
                "Verbessere die Lesbarkeit und Organisation."
            ),
            "erweitern": (
                "Erweitere und verbessere den folgenden Transkript-Text. "
                "Füge Kontext, Erklärungen und Details hinzu. "
                "Verbessere Formulierungen und Grammatik."
            )
        }

        prompt = task_prompts.get(task, task_prompts["zusammenfassen"])
        full_input = f"{prompt}\n\n{text}"

        # GPT-5 Responses API Call
        response = self.client.responses.create(
            model="gpt-5",
            input=full_input,
            reasoning={
                "effort": reasoning_effort
            },
            text={
                "verbosity": verbosity
            },
            max_output_tokens=4096
        )

        return {
            "result": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
            "reasoning_level": reasoning_effort,
            "verbosity_level": verbosity,
            "usage_details": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        }

# Verwendung
service = GPT5TransformationService()

# Zusammenfassen
summary = service.transform(
    text="[Langes Transkript...]",
    task="zusammenfassen",
    reasoning_effort="medium",
    verbosity="low"
)

print(f"Zusammenfassung: {summary['result']}")
print(f"Tokens: {summary['tokens_used']}")
```

### Reasoning Effort Levels

| Level | Use Case | Beispiel |
|-------|----------|----------|
| `minimal` | Einfache, schnelle Aufgaben | Kurze Fakten-Fragen |
| `low` | Standard-Zusammenfassungen | Einfache Transkript-Zusammenfassung |
| `medium` | Strukturierung & Analyse | Text strukturieren, umformulieren |
| `high` | Komplexe Transformationen | Tiefe Analyse, erweiterte Bearbeitung |

### Verbosity Levels

| Level | Ausgabe-Länge | Use Case |
|-------|---------------|----------|
| `low` | Kurz & prägnant | Quick Summary für UI |
| `medium` | Ausgewogen | Standard-Transformationen |
| `high` | Ausführlich | Detaillierte Berichte |

---

## 3. Vollständige Integration für Audio Sessions App

### Kombinierter Service

```python
from openai import OpenAI
from pathlib import Path
import json
import hashlib

class AudioSessionService:
    """
    Kombinierter Service für Audio Sessions App:
    1. Transkription (Sprache → Text)
    2. Transformation (Text → Bearbeiteter Text)
    """

    def __init__(self, api_key: str = None, cache_dir: str = ".transcripts_cache"):
        self.client = OpenAI(api_key=api_key)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def process_audio_session(
        self,
        audio_file_path: str,
        language: str = "de",
        transformations: list[dict] = None,
        use_cache: bool = True
    ) -> dict:
        """
        Vollständiger Workflow: Audio → Transkript → Transformationen

        Args:
            audio_file_path: Pfad zur Audio-Datei
            language: Sprache ("de", "en")
            transformations: Liste von Transformationen, z.B.:
                [
                    {"task": "zusammenfassen", "reasoning": "medium", "verbosity": "low"},
                    {"task": "uebersetzen", "reasoning": "low", "verbosity": "medium"}
                ]
            use_cache: Cache für Transkripte verwenden

        Returns:
            {
                "transcript": {...},
                "transformations": {...},
                "total_tokens": int
            }
        """
        # Schritt 1: Transkription
        transcript = self._transcribe(audio_file_path, language, use_cache)

        result = {
            "transcript": transcript,
            "transformations": {},
            "total_tokens": transcript["tokens_used"]
        }

        # Schritt 2: Transformationen anwenden (falls gewünscht)
        if transformations:
            for transform in transformations:
                task = transform.get("task", "zusammenfassen")
                reasoning = transform.get("reasoning", "medium")
                verbosity = transform.get("verbosity", "medium")

                transformed = self._transform(
                    text=transcript["text"],
                    task=task,
                    reasoning_effort=reasoning,
                    verbosity=verbosity
                )

                result["transformations"][task] = transformed
                result["total_tokens"] += transformed["tokens_used"]

        return result

    def _transcribe(self, audio_file_path: str, language: str, use_cache: bool) -> dict:
        """Interne Transkriptions-Methode mit Caching"""
        # Cache-Check
        if use_cache:
            cached = self._load_transcript_from_cache(audio_file_path)
            if cached:
                print(f"✓ Transkript aus Cache geladen")
                return cached

        print(f"⚙ Transkribiere Audio-Datei...")

        # Transkribieren
        with open(audio_file_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file,
                language=language,
                response_format="verbose_json",
                prompt="Audio Sessions, Transkription, Notizen"
            )

        result = {
            "text": transcript.text,
            "language": transcript.language,
            "duration": transcript.duration,
            "segments": [
                {"start": seg.start, "end": seg.end, "text": seg.text}
                for seg in transcript.segments
            ],
            "tokens_used": transcript.usage.total_tokens
        }

        # Cache speichern
        if use_cache:
            self._save_transcript_to_cache(audio_file_path, result)

        print(f"✓ Transkription abgeschlossen ({result['tokens_used']} Tokens)")

        return result

    def _transform(
        self,
        text: str,
        task: str,
        reasoning_effort: str,
        verbosity: str
    ) -> dict:
        """Interne Transformations-Methode"""
        print(f"⚙ Wende Transformation an: {task}")

        task_prompts = {
            "zusammenfassen": (
                "Fasse den folgenden Transkript-Text prägnant zusammen. "
                "Behalte die wichtigsten Informationen bei."
            ),
            "uebersetzen": (
                "Übersetze den folgenden deutschen Text ins Englische. "
                "Achte auf natürliche Formulierungen."
            ),
            "strukturieren": (
                "Strukturiere den folgenden Transkript-Text übersichtlich. "
                "Verwende Überschriften und Stichpunkte."
            )
        }

        prompt = task_prompts.get(task, task_prompts["zusammenfassen"])
        full_input = f"{prompt}\n\n{text}"

        response = self.client.responses.create(
            model="gpt-5",
            input=full_input,
            reasoning={"effort": reasoning_effort},
            text={"verbosity": verbosity},
            max_output_tokens=4096
        )

        result = {
            "result": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
            "reasoning_level": reasoning_effort,
            "verbosity_level": verbosity
        }

        print(f"✓ Transformation abgeschlossen ({result['tokens_used']} Tokens)")

        return result

    def _load_transcript_from_cache(self, audio_file_path: str) -> dict | None:
        """Lade Transkript aus Cache"""
        file_hash = self._get_audio_hash(audio_file_path)
        cache_file = self.cache_dir / f"{file_hash}.json"

        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return None

    def _save_transcript_to_cache(self, audio_file_path: str, data: dict):
        """Speichere Transkript im Cache"""
        file_hash = self._get_audio_hash(audio_file_path)
        cache_file = self.cache_dir / f"{file_hash}.json"

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get_audio_hash(self, audio_file_path: str) -> str:
        """Berechne SHA256-Hash der Audio-Datei"""
        with open(audio_file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()


# ===== VERWENDUNG =====

if __name__ == "__main__":
    # Service initialisieren
    service = AudioSessionService()

    # Vollständiger Workflow
    result = service.process_audio_session(
        audio_file_path="/path/to/session_001.wav",
        language="de",
        transformations=[
            {
                "task": "zusammenfassen",
                "reasoning": "medium",
                "verbosity": "low"
            },
            {
                "task": "strukturieren",
                "reasoning": "medium",
                "verbosity": "medium"
            },
            {
                "task": "uebersetzen",
                "reasoning": "low",
                "verbosity": "medium"
            }
        ],
        use_cache=True
    )

    # Ergebnisse ausgeben
    print("\n" + "="*50)
    print("TRANSKRIPT:")
    print("="*50)
    print(result["transcript"]["text"])
    print(f"\nDauer: {result['transcript']['duration']:.2f}s")
    print(f"Tokens: {result['transcript']['tokens_used']}")

    print("\n" + "="*50)
    print("ZUSAMMENFASSUNG:")
    print("="*50)
    print(result["transformations"]["zusammenfassen"]["result"])
    print(f"Tokens: {result['transformations']['zusammenfassen']['tokens_used']}")

    print("\n" + "="*50)
    print("STRUKTURIERT:")
    print("="*50)
    print(result["transformations"]["strukturieren"]["result"])

    print("\n" + "="*50)
    print(f"GESAMT TOKENS: {result['total_tokens']}")
    print("="*50)
```

---

## 4. Qt Integration für Audio Sessions App

### Worker-Threads für UI-Responsiveness

```python
from PySide6.QtCore import QThread, Signal
from audio_session_service import AudioSessionService

class TranscriptionWorker(QThread):
    """Worker-Thread für Audio-Transkription"""

    finished = Signal(dict)  # Erfolg mit Transkript
    error = Signal(str)      # Fehler
    progress = Signal(str)   # Fortschritts-Updates

    def __init__(self, audio_file_path: str, language: str = "de"):
        super().__init__()
        self.audio_file_path = audio_file_path
        self.language = language
        self.service = AudioSessionService()

    def run(self):
        try:
            self.progress.emit("Starte Transkription...")

            result = self.service._transcribe(
                self.audio_file_path,
                self.language,
                use_cache=True
            )

            self.progress.emit("Transkription abgeschlossen")
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(f"Transkriptionsfehler: {str(e)}")


class TransformationWorker(QThread):
    """Worker-Thread für Text-Transformation"""

    finished = Signal(dict)  # Erfolg mit transformiertem Text
    error = Signal(str)      # Fehler
    progress = Signal(str)   # Fortschritts-Updates

    def __init__(
        self,
        text: str,
        task: str,
        reasoning_effort: str = "medium",
        verbosity: str = "medium"
    ):
        super().__init__()
        self.text = text
        self.task = task
        self.reasoning_effort = reasoning_effort
        self.verbosity = verbosity
        self.service = AudioSessionService()

    def run(self):
        try:
            self.progress.emit(f"Wende '{self.task}' an...")

            result = self.service._transform(
                text=self.text,
                task=self.task,
                reasoning_effort=self.reasoning_effort,
                verbosity=self.verbosity
            )

            self.progress.emit(f"'{self.task}' abgeschlossen")
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(f"Transformationsfehler: {str(e)}")


# ===== VERWENDUNG IN UI-WIDGET =====

class AIView(QWidget):
    """AI View Widget mit Transkription und Transformation"""

    def __init__(self):
        super().__init__()
        self.transcription_worker = None
        self.transformation_worker = None
        self.current_transcript = ""

    def start_transcription(self, audio_file_path: str):
        """Starte Transkription in Worker-Thread"""
        if self.transcription_worker and self.transcription_worker.isRunning():
            print("Transkription läuft bereits")
            return

        self.transcription_worker = TranscriptionWorker(audio_file_path, "de")
        self.transcription_worker.finished.connect(self.on_transcription_finished)
        self.transcription_worker.error.connect(self.on_transcription_error)
        self.transcription_worker.progress.connect(self.on_transcription_progress)
        self.transcription_worker.start()

    def on_transcription_finished(self, result: dict):
        """Transkription erfolgreich abgeschlossen"""
        self.current_transcript = result["text"]

        # Zeige Transkript in UI
        self.transcript_text_edit.setPlainText(self.current_transcript)

        # Zeige Token-Info
        tokens = result["tokens_used"]
        duration = result["duration"]
        self.statusbar.showMessage(
            f"✓ Transkription abgeschlossen - {tokens} Tokens - {duration:.1f}s"
        )

    def on_transcription_error(self, error_msg: str):
        """Transkriptionsfehler"""
        self.statusbar.showMessage(f"✗ {error_msg}")

    def on_transcription_progress(self, message: str):
        """Fortschritts-Update"""
        self.statusbar.showMessage(message)

    def apply_transformation(self, task: str):
        """Wende Transformation auf Transkript an"""
        if not self.current_transcript:
            self.statusbar.showMessage("Kein Transkript vorhanden")
            return

        if self.transformation_worker and self.transformation_worker.isRunning():
            print("Transformation läuft bereits")
            return

        # Reasoning & Verbosity aus UI-Einstellungen
        reasoning = self.reasoning_combo.currentText().lower()  # "Low", "Medium", "High"
        verbosity = self.verbosity_combo.currentText().lower()  # "Low", "Medium", "High"

        self.transformation_worker = TransformationWorker(
            text=self.current_transcript,
            task=task,
            reasoning_effort=reasoning,
            verbosity=verbosity
        )
        self.transformation_worker.finished.connect(self.on_transformation_finished)
        self.transformation_worker.error.connect(self.on_transformation_error)
        self.transformation_worker.progress.connect(self.on_transformation_progress)
        self.transformation_worker.start()

    def on_transformation_finished(self, result: dict):
        """Transformation erfolgreich abgeschlossen"""
        # Zeige transformierten Text in UI
        self.transformed_text_edit.setPlainText(result["result"])

        # Zeige Token-Info
        tokens = result["tokens_used"]
        reasoning = result["reasoning_level"]
        verbosity = result["verbosity_level"]
        self.statusbar.showMessage(
            f"✓ Transformation abgeschlossen - {tokens} Tokens "
            f"(Reasoning: {reasoning}, Verbosity: {verbosity})"
        )

    def on_transformation_error(self, error_msg: str):
        """Transformationsfehler"""
        self.statusbar.showMessage(f"✗ {error_msg}")

    def on_transformation_progress(self, message: str):
        """Fortschritts-Update"""
        self.statusbar.showMessage(message)
```

---

## 5. Error Handling & Best Practices

### Robustes Error Handling

```python
from openai import OpenAI, OpenAIError, APIError, RateLimitError, APITimeoutError

def safe_transcribe(audio_file_path: str) -> dict:
    """Transkription mit umfassendem Error Handling"""
    try:
        client = OpenAI()

        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file,
                language="de"
            )

        return {
            "success": True,
            "text": transcript.text,
            "tokens": transcript.usage.total_tokens
        }

    except FileNotFoundError:
        return {
            "success": False,
            "error": "Audio-Datei nicht gefunden",
            "error_type": "file_not_found"
        }

    except RateLimitError as e:
        return {
            "success": False,
            "error": "API Rate Limit erreicht - bitte später erneut versuchen",
            "error_type": "rate_limit",
            "details": str(e)
        }

    except APITimeoutError as e:
        return {
            "success": False,
            "error": "API Timeout - Anfrage dauerte zu lange",
            "error_type": "timeout",
            "details": str(e)
        }

    except APIError as e:
        return {
            "success": False,
            "error": f"API Fehler: {e.message}",
            "error_type": "api_error",
            "status_code": e.status_code
        }

    except OpenAIError as e:
        return {
            "success": False,
            "error": f"OpenAI Fehler: {str(e)}",
            "error_type": "openai_error"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Unerwarteter Fehler: {str(e)}",
            "error_type": "unknown"
        }


def safe_transform(text: str, task: str) -> dict:
    """Transformation mit Error Handling"""
    try:
        client = OpenAI()

        response = client.responses.create(
            model="gpt-5",
            input=f"Fasse zusammen: {text}",
            reasoning={"effort": "medium"},
            text={"verbosity": "low"}
            # WICHTIG: Keine temperature oder top_p verwenden!
        )

        return {
            "success": True,
            "result": response.choices[0].message.content,
            "tokens": response.usage.total_tokens
        }

    except ValueError as e:
        # Tritt auf wenn alte Parameter verwendet werden
        if "temperature" in str(e) or "top_p" in str(e):
            return {
                "success": False,
                "error": "Alte Parameter verwendet - nutze reasoning/verbosity stattdessen",
                "error_type": "invalid_parameters"
            }
        raise

    except RateLimitError as e:
        return {
            "success": False,
            "error": "Rate Limit erreicht",
            "error_type": "rate_limit"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "unknown"
        }
```

### Performance-Optimierung

```python
# 1. Caching verwenden
service = AudioSessionService(cache_dir=".transcripts_cache")
result = service.process_audio_session(
    audio_file_path="session.wav",
    use_cache=True  # ✅ Cache aktivieren
)

# 2. Angemessenes Reasoning-Level wählen
# SCHLECHT - unnötig hohes Reasoning
response = client.responses.create(
    model="gpt-5",
    input="Kurze Zusammenfassung von: [Text]",
    reasoning={"effort": "high"}  # ❌ Verschwendet Tokens
)

# GUT - angemessenes Reasoning
response = client.responses.create(
    model="gpt-5",
    input="Kurze Zusammenfassung von: [Text]",
    reasoning={"effort": "low"}  # ✅ Effizient
)

# 3. Verbosity für UI anpassen
# Für kurze UI-Anzeige
response = client.responses.create(
    model="gpt-5",
    input="...",
    text={"verbosity": "low"}  # ✅ Kurze Ausgabe
)

# 4. Token-Limits setzen
response = client.responses.create(
    model="gpt-5",
    input="...",
    max_output_tokens=1000  # ✅ Limit setzen
)
```

---

## 6. Cheat Sheet

### Schnellreferenz für Transcription

```python
# Basic Transcription
transcript = client.audio.transcriptions.create(
    model="gpt-4o-transcribe",
    file=open("audio.wav", "rb"),
    language="de"
)

# Mit Context & Details
transcript = client.audio.transcriptions.create(
    model="gpt-4o-transcribe",
    file=open("audio.wav", "rb"),
    language="de",
    response_format="verbose_json",
    prompt="Kontext für bessere Genauigkeit"
)
```

### Schnellreferenz für GPT-5 Transformation

```python
# Basic Transformation
response = client.responses.create(
    model="gpt-5",
    input="Fasse zusammen: [Text]"
)

# Mit Reasoning & Verbosity Control
response = client.responses.create(
    model="gpt-5",
    input="Fasse zusammen: [Text]",
    reasoning={"effort": "medium"},
    text={"verbosity": "low"},
    max_output_tokens=2000
)
```

### Parameter-Mapping

| Alt (Chat Completions) | Neu (Responses API) |
|------------------------|---------------------|
| `temperature=0.7` | `reasoning={"effort": "medium"}` |
| `max_tokens=1000` | `max_output_tokens=1000` |
| - | `text={"verbosity": "low"}` |

---

## 7. Zusammenfassung

### Empfohlener Stack für Audio Sessions App

```
1. Audio aufnehmen → WAV speichern
                ↓
2. Transkription → gpt-4o-transcribe
                ↓
3. Text transformieren → gpt-5 (Responses API)
                ↓
4. Ergebnisse anzeigen in UI
```

### Key Points

✅ **Transkription:**
- Modell: `gpt-4o-transcribe`
- Sprache: `language="de"` immer angeben!
- Format: `verbose_json` für Details
- Caching: Für wiederholte Transkriptionen

✅ **Transformation:**
- Modell: `gpt-5`
- API: Responses API (`/v1/responses`)
- Control: `reasoning.effort` + `text.verbosity`
- Keine alten Parameter (`temperature`, `top_p`)

✅ **Integration:**
- Qt Worker-Threads für UI-Responsiveness
- Error Handling für alle API-Calls
- Token-Tracking für Kosten-Übersicht
- Cache-System für Performance

### Next Steps

1. ✅ `AudioSessionService` in App integrieren
2. ✅ Worker-Threads in UI einbauen
3. ✅ UI-Controls für Reasoning/Verbosity
4. ✅ Token-Anzeige implementieren
5. ✅ Error-Dialoge für API-Fehler

---

**Dokumentation erstellt:** Januar 2025
**Für:** cdb_brainrecorder_v2_desktop
