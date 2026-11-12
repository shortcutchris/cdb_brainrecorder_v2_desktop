# Recorder Studio 0.5.77 für eine neue Pi-5-Karte

**Stand am 12. November 2026:** gebaut und offline geprüft. Der erste Boot von einer zweiten SD-Karte auf echter Hardware steht aus.

| Export des Offline-Images | Wert |
| --- | --- |
| Dateiname | `cdb-brain-0.5.77-pi5-offline.img.xz` |
| Komprimiert / entpackt | 5.545.974.408 / 11.634.999.296 Byte |
| SHA-256 der .img.xz | `4054a5eb55057c4b8eadf28649356d3891bc9027a3961a2475eae7140eeabe1f` |
| SHA-256 der .img | `4e63a2726e5c6ab92cb1d94d38d2ccbac4df1857cd7d61995c588da4f12898c3` |
| Quellcommit | `fea40d74d1d2ce3d15c8428f571b0b7c67a78b5a` |
| pi-gen | `d346cd53562b3c6b4f94c9155175f814258c456d` |

Der ARM64-Build verwendete den öffentlichen Update-Prüfschlüssel, das WLAN-Länderkürzel DE und das Profil `--offline-models`. Raspberry Pi Imager kann die komprimierte Datei direkt auf eine **separate Karte ab 32 GB** schreiben. Keine gespeicherten Imager-Anpassungen für Benutzer, SSH oder WLAN übernehmen. Nach dem Schreiben verifizieren lassen.

### Prüfung des fertigen Exports

- FAT- und ext4-Dateisystem geprüft. Die Offlineprüfung bestätigte die 134 App-Dateien des Manifests, die Modellgewichte, die Ollama-Layer und die Lizenztexte. Der WLAN-Dienst ist für den Systemstart aktiviert. Die Prüfung auf vorinstallierte Kundendaten war unauffällig.
- In einem isolierten ARM64-Container ohne externes Netzwerk wurde der Export schreibgeschützt eingehängt. Ein temporäres leeres Geräteprofil durchlief dieselbe Initialisierung wie beim Erststart. Der Einrichtungsassistent war angefordert. Ollama konnte seinen lokalen Modellindex in einer flüchtigen Schreibschicht aufbauen.
- Der Recorder-Modellkatalog meldete Whisper Medium und Qwen3 4B Instruct als installiert. Whisper erkannte „Montag“ aus einem kurzen synthetischen deutschen Testclip. Qwen fasste den Beispieltext mit dem richtigen Wochentag zusammen. Dieser Test belegt die lokale Ausführbarkeit und die Verfügbarkeit ohne Modelldownload.
- 544 Python-Tests und 136 JavaScript-Tests bestanden. Der [WLAN-Test auf dem bereits eingerichteten Gehäuse-Pi](../../erststart-0.5.77.md) ist separat dokumentiert.

### Erster Test mit der Karte

Pi mit der zweiten Karte ohne LAN starten. Der Assistent soll nach verfügbaren WLANs suchen und den Zugang über Netzauswahl und Passwort ermöglichen. Unter „Lokale Modelle“ sollen beide Einträge bereits „Installiert“ anzeigen. Für die persönliche Brain-Anmeldung ist Internet erforderlich. Zum Schluss Mikrofon und Lautsprecher prüfen und eine kurze Probeaufnahme lokal transkribieren und zusammenfassen. Nach einem Neustart kontrollieren, dass Verbindung und Einrichtung erhalten sind.
