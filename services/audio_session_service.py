"""
Audio Transcription & GPT-5 Transformation Service
Basierend auf docs/AUDIO_TRANSCRIPTION_GPT5_INTEGRATION.md
"""
from openai import OpenAI, OpenAIError, APIError, RateLimitError, APITimeoutError
from pathlib import Path
from typing import Optional, Dict, Any
import json
import hashlib


class AudioSessionService:
    """Service für Audio-Transkription und Text-Transformation"""

    def __init__(self, api_key: str = None, cache_dir: str = ".transcripts_cache"):
        """
        Initialisiert den Service

        Args:
            api_key: OpenAI API Key
            cache_dir: Verzeichnis für Transkript-Cache
        """
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def transcribe(self, audio_file_path: str, language: str = "de", use_cache: bool = True) -> dict:
        """
        Transkribiert Audio-Datei mit gpt-4o-transcribe

        Args:
            audio_file_path: Pfad zur Audio-Datei
            language: Sprache als ISO-639-1 Code ("de", "en")
            use_cache: Cache verwenden für schnellere Wiederverarbeitung

        Returns:
            {
                "success": True/False,
                "text": str,
                "language": str,
                "duration": float,
                "segments": list,
                "tokens_used": int,
                "error": str (nur bei success=False)
            }
        """
        if not self.client:
            return {"success": False, "error": "Kein API Key konfiguriert"}

        # Cache-Check
        if use_cache:
            cached = self._load_from_cache(audio_file_path)
            if cached:
                cached["success"] = True
                return cached

        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="gpt-4o-transcribe",
                    file=audio_file,
                    language=language,
                    response_format="json",
                    prompt="Audio Sessions, Transkription, Notizen"
                )

            # Mit response_format="json" bekommen wir nur text und basic info
            result = {
                "success": True,
                "text": transcript.text,
                "language": getattr(transcript, 'language', language),
                "duration": getattr(transcript, 'duration', 0.0),
                "segments": [],
                "tokens_used": getattr(transcript.usage, 'total_tokens', 0) if hasattr(transcript, 'usage') else 0
            }

            # Cache speichern
            if use_cache:
                self._save_to_cache(audio_file_path, result)

            return result

        except FileNotFoundError:
            return {"success": False, "error": "Audio-Datei nicht gefunden"}

        except RateLimitError:
            return {"success": False, "error": "Rate Limit erreicht. Bitte später erneut versuchen."}

        except APITimeoutError:
            return {"success": False, "error": "API Timeout - Anfrage dauerte zu lange"}

        except APIError as e:
            return {"success": False, "error": f"API Fehler: {e.message}"}

        except OpenAIError as e:
            return {"success": False, "error": f"OpenAI Fehler: {str(e)}"}

        except Exception as e:
            return {"success": False, "error": f"Unerwarteter Fehler: {str(e)}"}

    def transform(
        self,
        text: str,
        task: str = "zusammenfassen",
        reasoning_effort: str = "medium",
        verbosity: str = "low"
    ) -> dict:
        """
        Transformiert Text mit Responses API

        Args:
            text: Zu transformierender Text
            task: "zusammenfassen" | "uebersetzen" | "strukturieren"
            reasoning_effort: "minimal" | "low" | "medium" | "high"
            verbosity: "low" | "medium" | "high"

        Returns:
            {
                "success": True/False,
                "result": str,
                "tokens_used": int,
                "error": str (nur bei success=False)
            }
        """
        if not self.client:
            return {"success": False, "error": "Kein API Key konfiguriert"}

        task_prompts = {
            "zusammenfassen": (
                "Fasse den folgenden Transkript-Text prägnant zusammen. "
                "Behalte die wichtigsten Informationen und Kernaussagen bei."
            ),
            "uebersetzen": (
                "Übersetze den folgenden deutschen Text ins Englische. "
                "Achte auf natürliche Formulierungen und korrekte Terminologie."
            ),
            "strukturieren": (
                "Strukturiere den folgenden Transkript-Text übersichtlich. "
                "Erstelle Überschriften, Absätze und Stichpunkte für bessere Lesbarkeit."
            )
        }

        prompt = task_prompts.get(task, task_prompts["zusammenfassen"])
        full_input = f"{prompt}\n\n{text}"

        try:
            # Versuche zuerst GPT-5 mit Chat Completions
            try:
                # Verbosity in Prompt einbauen für GPT-5
                verbosity_suffix = {
                    "low": " Sei kurz und prägnant.",
                    "medium": " Gib eine ausgewogene Antwort.",
                    "high": " Sei ausführlich und detailliert."
                }
                gpt5_input = full_input + verbosity_suffix.get(verbosity, verbosity_suffix["medium"])

                # GPT-5 verwendet reasoning_effort als Parameter
                response = self.client.chat.completions.create(
                    model="gpt-5",
                    messages=[
                        {"role": "system", "content": "Du bist ein hilfreicher Assistent für Textverarbeitung."},
                        {"role": "user", "content": gpt5_input}
                    ],
                    reasoning_effort=reasoning_effort if reasoning_effort else "medium",
                    max_completion_tokens=4096
                )

                output_text = response.choices[0].message.content
                tokens = response.usage.total_tokens
                print(f"GPT-5 erfolgreich verwendet (Reasoning: {reasoning_effort}, Tokens: {tokens})")

            except Exception as gpt5_error:
                # Fallback auf Chat Completions mit gpt-4o
                print(f"GPT-5 nicht verfügbar, Fallback auf GPT-4o: {str(gpt5_error)}")

                # Reasoning effort auf temperature mappen
                temperature_map = {
                    "minimal": 0.3,
                    "low": 0.5,
                    "medium": 0.7,
                    "high": 0.9
                }
                temperature = temperature_map.get(reasoning_effort, 0.7)

                # Verbosity in Prompt einbauen
                verbosity_suffix = {
                    "low": " Sei kurz und prägnant.",
                    "medium": " Gib eine ausgewogene Antwort.",
                    "high": " Sei ausführlich und detailliert."
                }
                full_input += verbosity_suffix.get(verbosity, verbosity_suffix["medium"])

                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Du bist ein hilfreicher Assistent für Textverarbeitung."},
                        {"role": "user", "content": full_input}
                    ],
                    temperature=temperature,
                    max_tokens=4096
                )

                output_text = response.choices[0].message.content
                tokens = response.usage.total_tokens

            return {
                "success": True,
                "result": output_text,
                "tokens_used": tokens
            }

        except RateLimitError:
            return {"success": False, "error": "Rate Limit erreicht. Bitte später erneut versuchen."}

        except APIError as e:
            return {"success": False, "error": f"API Fehler: {e.message}"}

        except Exception as e:
            return {"success": False, "error": f"Fehler: {str(e)}"}

    def _load_from_cache(self, audio_file_path: str) -> Optional[dict]:
        """Lädt Transkript aus Cache"""
        file_hash = self._get_audio_hash(audio_file_path)
        cache_file = self.cache_dir / f"{file_hash}.json"

        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_to_cache(self, audio_file_path: str, data: dict):
        """Speichert Transkript im Cache"""
        file_hash = self._get_audio_hash(audio_file_path)
        cache_file = self.cache_dir / f"{file_hash}.json"

        # success-Flag entfernen vor dem Speichern
        cache_data = {k: v for k, v in data.items() if k != "success"}

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

    def _get_audio_hash(self, audio_file_path: str) -> str:
        """Berechnet SHA256-Hash der Audio-Datei"""
        with open(audio_file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
