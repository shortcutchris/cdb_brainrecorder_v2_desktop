"""
Audio Transcription & GPT-5 Transformation Service
Basierend auf docs/AUDIO_TRANSCRIPTION_GPT5_INTEGRATION.md
"""
from openai import OpenAI, OpenAIError, APIError, RateLimitError, APITimeoutError
from pathlib import Path
from typing import Optional, Dict, Any
import json
import hashlib
import sys
import tempfile
import os
import platform
import subprocess

# Platform detection: Raspberry Pi verwendet ffmpeg direkt (Python 3.13 kompatibel)
IS_RASPBERRY_PI = platform.machine().startswith('aarch') or platform.machine().startswith('arm')

# Conditional imports: pydub nur auf nicht-Raspberry-Pi Plattformen
if not IS_RASPBERRY_PI:
    from pydub import AudioSegment
    from pydub.utils import which

sys.path.append(str(Path(__file__).parent.parent))
from settings import SettingsManager

# Konfiguriere ffmpeg Pfad für pydub (für PyInstaller-gebaute Apps)
def _setup_ffmpeg():
    """Findet und setzt ffmpeg/ffprobe Pfad für pydub (nur auf nicht-Raspberry-Pi)"""
    if IS_RASPBERRY_PI:
        return  # Auf Raspberry Pi wird ffmpeg direkt verwendet

    # Prüfe ob wir in einer PyInstaller-App laufen
    if getattr(sys, 'frozen', False):
        # In PyInstaller-App: Binaries sind im gleichen Verzeichnis wie die Executable
        bundle_dir = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
        ffmpeg_path = bundle_dir / 'ffmpeg'
        ffprobe_path = bundle_dir / 'ffprobe'

        if ffmpeg_path.exists():
            AudioSegment.converter = str(ffmpeg_path)
            AudioSegment.ffmpeg = str(ffmpeg_path)
        if ffprobe_path.exists():
            AudioSegment.ffprobe = str(ffprobe_path)
    else:
        # Development-Modus: Versuche ffmpeg im PATH zu finden
        ffmpeg = which("ffmpeg")
        ffprobe = which("ffprobe")
        if ffmpeg:
            AudioSegment.converter = ffmpeg
            AudioSegment.ffmpeg = ffmpeg
        if ffprobe:
            AudioSegment.ffprobe = ffprobe

# ffmpeg beim Import konfigurieren
_setup_ffmpeg()


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

    def transcribe(self, audio_file_path: str, language: str = "de", use_cache: bool = True,
                   progress_callback=None) -> dict:
        """
        Transkribiert Audio-Datei mit gpt-4o-transcribe

        Args:
            audio_file_path: Pfad zur Audio-Datei (WAV)
            language: Sprache als ISO-639-1 Code ("de", "en")
            use_cache: Cache verwenden für schnellere Wiederverarbeitung
            progress_callback: Callback-Funktion für Progress (current_chunk, total_chunks)

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

        # Konvertiere relative Pfade zu absoluten (Legacy-Support)
        audio_path = Path(audio_file_path)
        if not audio_path.is_absolute():
            audio_path = Path.cwd() / audio_path
        audio_file_path = str(audio_path)

        # Prüfe ob Datei existiert
        if not audio_path.exists():
            return {"success": False, "error": f"Audio-Datei nicht gefunden: {audio_file_path}"}

        # Cache-Check (basierend auf Original-WAV)
        if use_cache:
            cached = self._load_from_cache(audio_file_path)
            if cached:
                cached["success"] = True
                return cached

        audio_chunks = []

        try:
            # 1. Audio vorbereiten (MP3 + ggf. Chunking)
            audio_chunks = self._prepare_audio_for_transcription(audio_file_path)
            total_chunks = len(audio_chunks)

            # 2. Jeden Chunk einzeln transkribieren
            all_transcripts = []
            total_tokens = 0

            for i, chunk_path in enumerate(audio_chunks):
                # Progress-Callback (für UI-Update)
                if progress_callback:
                    progress_callback(i + 1, total_chunks)

                # API-Call
                with open(chunk_path, "rb") as audio_file:
                    transcript = self.client.audio.transcriptions.create(
                        model="gpt-4o-transcribe",
                        file=audio_file,
                        language=language,
                        response_format="json",
                        prompt="Audio Sessions, Transkription, Notizen"
                    )

                # Transkript sammeln
                all_transcripts.append(transcript.text)
                total_tokens += getattr(transcript.usage, 'total_tokens', 0) if hasattr(transcript, 'usage') else 0

            # 3. Transkripte zusammenführen
            combined_text = " ".join(all_transcripts)

            result = {
                "success": True,
                "text": combined_text,
                "language": language,
                "duration": 0.0,
                "segments": [],
                "tokens_used": total_tokens
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

        finally:
            # 4. Temp-Dateien IMMER aufräumen (auch bei Fehler)
            if audio_chunks:
                self._cleanup_temp_files(audio_chunks)

    def transform(
        self,
        text: str,
        prompt_id: str = "zusammenfassen",
        reasoning_effort: str = "medium",
        verbosity: str = "low"
    ) -> dict:
        """
        Transformiert Text mit Responses API

        Args:
            text: Zu transformierender Text
            prompt_id: ID des zu verwendenden Prompts
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

        # Prompt aus Settings laden
        settings_manager = SettingsManager()
        prompt_obj = settings_manager.get_prompt_by_id(prompt_id)

        if not prompt_obj:
            # Fallback: Ersten Prompt verwenden
            all_prompts = settings_manager.get_all_prompts()
            if all_prompts:
                prompt_obj = all_prompts[0]
            else:
                return {"success": False, "error": "Keine Prompts verfügbar"}

        prompt = prompt_obj.get('prompt_text', '')
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

    def _prepare_audio_for_transcription(self, audio_file_path: str, max_mb: int = 20) -> list:
        """
        Bereitet Audio für Whisper API vor

        1. Konvertiert WAV → MP3 (16 kHz, 64 kbps, Mono)
        2. Splittet in 15-Min-Chunks wenn >20 MB

        Args:
            audio_file_path: Pfad zur Original-WAV-Datei
            max_mb: Maximale Dateigröße in MB (Standard: 20)

        Returns:
            Liste von Temp-MP3-Dateipfaden (1+ Chunks)
        """
        if IS_RASPBERRY_PI:
            return self._prepare_audio_ffmpeg(audio_file_path, max_mb)
        else:
            return self._prepare_audio_pydub(audio_file_path, max_mb)

    def _prepare_audio_pydub(self, audio_file_path: str, max_mb: int = 20) -> list:
        """
        Bereitet Audio mit pydub vor (für macOS, Windows, x86 Linux)
        """
        # 1. WAV laden und zu MP3 konvertieren
        audio = AudioSegment.from_wav(audio_file_path)
        audio = audio.set_frame_rate(16000)  # Whisper-optimiert
        audio = audio.set_channels(1)  # Mono

        # Temp-MP3 erstellen
        temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        audio.export(temp_mp3.name, format="mp3", bitrate="64k")
        temp_mp3.close()

        # 2. Dateigröße prüfen
        file_size_mb = os.path.getsize(temp_mp3.name) / (1024 * 1024)

        # 3. Wenn klein genug: Direkt zurückgeben
        if file_size_mb <= max_mb:
            return [temp_mp3.name]

        # 4. Zu groß: In 15-Min-Chunks aufteilen
        chunk_length_ms = 15 * 60 * 1000  # 15 Minuten in Millisekunden
        chunks = []

        for i in range(0, len(audio), chunk_length_ms):
            chunk = audio[i:i + chunk_length_ms]

            # Temp-Datei für Chunk
            temp_chunk = tempfile.NamedTemporaryFile(delete=False, suffix=f"_chunk_{len(chunks)}.mp3")
            chunk.export(temp_chunk.name, format="mp3", bitrate="64k")
            temp_chunk.close()

            chunks.append(temp_chunk.name)

        # Original-Temp-MP3 löschen (nicht mehr benötigt)
        os.unlink(temp_mp3.name)

        return chunks

    def _get_audio_duration(self, audio_file_path: str) -> float:
        """Ermittelt Audio-Dauer mit ffprobe"""
        result = subprocess.run([
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_file_path
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"⚠️ ffprobe Warnung: {result.stderr}")
            return 0.0

        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0

    def _prepare_audio_ffmpeg(self, audio_file_path: str, max_mb: int = 20) -> list:
        """
        Bereitet Audio mit ffmpeg vor (für Raspberry Pi / Python 3.13)
        """
        # Original-Dauer ermitteln für Validierung
        original_duration = self._get_audio_duration(audio_file_path)
        print(f"📊 Original Audio-Dauer: {original_duration:.2f} Sekunden")

        # 1. WAV zu MP3 konvertieren mit ffmpeg
        temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_mp3.close()

        # ffmpeg Konvertierung: 16kHz, Mono, 64kbps
        # -max_muxing_queue_size für Raspberry Pi Stabilität
        result = subprocess.run([
            'ffmpeg', '-i', audio_file_path,
            '-ar', '16000',  # Sample rate: 16kHz
            '-ac', '1',      # Channels: Mono
            '-b:a', '64k',   # Bitrate: 64kbps
            '-max_muxing_queue_size', '1024',  # Größere Buffer für USB-Audio
            '-y',            # Overwrite output
            temp_mp3.name
        ], capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"ffmpeg Fehler: {result.stderr}")

        # VALIDIERUNG: Prüfe ob konvertierte Dauer korrekt ist
        converted_duration = self._get_audio_duration(temp_mp3.name)
        print(f"📊 Konvertierte Audio-Dauer: {converted_duration:.2f} Sekunden")

        if original_duration > 0 and abs(converted_duration - original_duration) > 1.0:
            print(f"⚠️ WARNUNG: Audio-Dauer-Verlust! Original: {original_duration:.2f}s, Konvertiert: {converted_duration:.2f}s")
            print(f"⚠️ Differenz: {abs(converted_duration - original_duration):.2f} Sekunden verloren!")

        # 2. Dateigröße prüfen
        file_size_mb = os.path.getsize(temp_mp3.name) / (1024 * 1024)
        print(f"📦 MP3 Dateigröße: {file_size_mb:.2f} MB")

        # 3. Wenn klein genug: Direkt zurückgeben
        if file_size_mb <= max_mb:
            return [temp_mp3.name]

        # 4. Zu groß: Audio-Dauer ermitteln und in 15-Min-Chunks aufteilen
        print(f"📦 Datei zu groß ({file_size_mb:.2f} MB), erstelle Chunks...")

        total_duration = converted_duration  # Verwende bereits ermittelte Dauer
        chunk_duration = 15 * 60  # 15 Minuten in Sekunden
        chunks = []
        total_chunk_duration = 0.0

        # Chunks erstellen
        start_time = 0
        chunk_index = 0
        while start_time < total_duration:
            temp_chunk = tempfile.NamedTemporaryFile(delete=False, suffix=f"_chunk_{chunk_index}.mp3")
            temp_chunk.close()

            # Berechne verbleibende Dauer für letzten Chunk
            remaining_duration = total_duration - start_time
            actual_chunk_duration = min(chunk_duration, remaining_duration)

            print(f"📊 Erstelle Chunk {chunk_index + 1}: Start={start_time:.1f}s, Dauer={actual_chunk_duration:.1f}s")

            # Chunk mit ffmpeg extrahieren
            result = subprocess.run([
                'ffmpeg', '-i', audio_file_path,
                '-ss', str(start_time),      # Start time
                '-t', str(actual_chunk_duration),   # Exakte Duration für letzten Chunk
                '-ar', '16000',
                '-ac', '1',
                '-b:a', '64k',
                '-max_muxing_queue_size', '1024',
                '-y',
                temp_chunk.name
            ], capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"ffmpeg Chunk-Fehler: {result.stderr}")

            # VALIDIERUNG: Chunk-Dauer prüfen
            chunk_duration_actual = self._get_audio_duration(temp_chunk.name)
            total_chunk_duration += chunk_duration_actual
            print(f"  ✓ Chunk {chunk_index + 1} Dauer: {chunk_duration_actual:.2f}s")

            chunks.append(temp_chunk.name)
            start_time += chunk_duration
            chunk_index += 1

        # FINAL-VALIDIERUNG: Prüfe Gesamt-Chunk-Dauer
        print(f"📊 Gesamt-Chunk-Dauer: {total_chunk_duration:.2f}s von {total_duration:.2f}s")
        if abs(total_chunk_duration - total_duration) > 2.0:
            print(f"⚠️ WARNUNG: Chunk-Dauer-Verlust! Erwartet: {total_duration:.2f}s, Chunks: {total_chunk_duration:.2f}s")

        # Original-Temp-MP3 löschen (nicht mehr benötigt)
        os.unlink(temp_mp3.name)

        return chunks

    def _cleanup_temp_files(self, file_paths: list):
        """Löscht temporäre Audio-Dateien"""
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception as e:
                print(f"Warnung: Temp-Datei konnte nicht gelöscht werden: {path} - {e}")

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
