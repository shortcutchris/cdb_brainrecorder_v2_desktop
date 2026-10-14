# Gesprächsstart · 0.5.40

Stand: 14. Oktober 2026. Pi 5 / 16 GB, ReSpeaker XVF3800, Marshall EMBERTON II.

## Ablauf

1. Mikrofon und Ausgabe werden wie bisher exklusiv für das Live-Gespräch reserviert.
2. Nach erfolgreicher lokaler Audiovorbereitung läuft ein leiser, 1,8 Sekunden langer
   Verbindungsklang. Lokale PCM-Erzeugung, 24 kHz mono, keine Audiodateien oder TTS-Anfragen.
3. Erst tatsächliches WebRTC `connected` beendet den Klang mit 80 ms Ausblendung.
   Anschließend der bisherige 360-ms-Bereitschaftston.
4. Nach `session.started` genau ein fest vorgegebener Begrüßungsauftrag an Voice One.
   Das Modell spricht selbst; keine lokale Ersatzstimme, kein erfundener Transkripteintrag.
5. Gespräch und Sprachbefehl zum Beenden funktionieren anschließend wie zuvor.

Der Eingangsstream enthält während der lokalen Starttöne ausschließlich Null-PCM;
der kurze Eingangsbuffer wird vor der Freigabe geleert. Dies überschreibt niemals
„Mikrofon stumm“. Nach Freigabe bleibt das normale Unterbrechen der Antwort möglich.
Alle Audioprozesse gehören der Sitzung und werden bei Ende/Fehler/Abbruch beendet.
Nur 20-ms-Blöcke werden ausgegeben, kein kompletter Loop vorgepuffert.

## CDB-Vertrag und Grenzen

Der vorhandene Datenkanal wird jetzt ausschließlich für einen festen
`session.instructions.append` mit `delegation_id: null` verwendet. Vorbild ist
`greetConversation` in `cdb_voice_one/app/voice-one/public/gira-guide.js`.
Keine beliebigen Browserbefehle, keine Änderung von Tools, Modell oder Bereichsrechten;
Brain-Anmeldung, Sitzungsanlage und Verarbeitung bleiben servergeführt.

Die Bestätigung wird über `client_event_id` zugeordnet. Höchstens zehn Sekunden
Warten auf Sitzungsbereitschaft bzw. ACK, keine Wiederholung bei unklarer Bestätigung,
keine zweite Begrüßung bei erneutem `connected`. Ein fehlender optionaler Ton oder
Begrüßungs-ACK beendet keine funktionierende Unterhaltung. ACK bedeutet Annahme,
nicht bereits hörbare Sprache; die Abnahme prüft zusätzlich Audioframes und Transkript.

[OpenAI-Dokumentation](https://developers.openai.com/api/docs/guides/live-delegation)
beschreibt die bestätigten Session-Appends. Für neue serverseitige Sitzungsverträge
wird dort eine Startnachricht in `session.input` empfohlen; der bestehende CDB-Endpunkt
bietet das derzeit nicht an. Daher derselbe nachgelagerte, auf Azure geprüfte Weg wie
im vorhandenen Voice-One-Client, ohne Serveränderung.

## Prüfung

- 222 Python-Tests und 99 JavaScript-Tests bestanden.
- Neu geprüft: Loop endet vor Bereitschaftston/Begrüßung, Abbruch räumt Prozesse auf,
  wiederholtes `connected` begrüßt nicht doppelt, passende ACK-ID erforderlich,
  Ablehnung löst keine Wiederholung aus, bestehendes Mute bleibt erhalten.
- Echte CDB-Staging-Sitzung mit synthetischer Stille: Modell begrüßt wörtlich,
  gesprochene Audioframes und normaler CDB-Chatverlauf bestätigt. [Messung](synthetic.json).
- Echte Pi-Hardware: ReSpeaker geöffnet, Eingang vorab stumm (keine Raumaufnahme
  übertragen), Verbindungston, Bereitschaftston und Modellantwort über den ausgewählten
  Marshall-Ausgang ausgegeben. 390 Loop-Blöcke, eine bestätigte Begrüßung,
  300 empfangene Audioframes. [Messung](hardware.json).
- Vollständiger synthetischer Sprachablauf gegen CDB: Begrüßung → „Bitte antworte
  nur mit dem Wort bereit“ → passende Antwort → „Okay, beende das Gespräch“.
  Ende durch `voice_command`, alle Audioprozesse beendet, Recorder und Einstellungen
  wieder freigegeben. [Nachweis](conversation.json).
- Im Hardwarelauf: Start bis WebRTC verbunden 8,34 s; erste Begrüßung siehe
  Provider-Zeitstempel in der Messung. Netzwerkzeiten schwanken.

Die Ausgabe wurde technisch auf dem echten Lautsprecherpfad geprüft; eine menschliche
Hörabnahme vor Ort wird damit nicht behauptet. Kein System-, Firmware- oder Modellwechsel.
