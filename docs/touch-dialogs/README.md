# Touch-Dialogprüfung – Studio 0.4.3

12.10.2026. Browser bei 100 % / CSS-Pixeln. Echte Studio-HTTP-Anbindung an isolierte synthetische Sitzungen auf dem Pi; keine persönlichen Meetings. Künstliche Audioquelle und kontrollierter Testprozessor, keine Aussage zur Modellqualität.

- [Modelle, 1280×720](01-models-1280x720.jpg)
- [Prompt-Eingabe mit Tastatur, 1024×600](02-prompts-keyboard-1024x600.jpg)
- [Bibliothek, 1280×720](03-library-1280x720.jpg)
- [Meetingdetails, 1280×720](04-meeting-details-1280x720.jpg)
- [Einstellungen während Aufnahme, 1280×720](05-recording-settings-1280x720.jpg)

Messungen im Browser: Modelldialog 660 px hoch, äußerer scrollTop=0 und scrollHeight=clientHeight; Inhalt 415 px hoch bei 935 px Gesamthöhe. Nach Navigation zum unteren Bereich bleibt der Kopf bei y=31, die Testaktion bei y=621..677. Bibliothek-Inhalt 492 px hoch bei 2524 px Gesamthöhe; Suchfeld bleibt y=128..184.

Bei 1024×600 mit Tastatur: äußerer Dialog scrollt nicht; Inhalt 155 px hoch, Speichern y=307..363, Tastatur y=380..600. Zeichen über Touch-Tastatur erfolgreich eingegeben. Aufnahme-Stopp während geöffnetem Einstellungsdialog 56 px hoch, Modellwahl gesperrt.

29 bestehende Funktionstests auf dem Pi bestanden. Konfliktvergleich und Wiedergabehinweis verwenden denselben Dialograhmen; deren Backend-Fehlerpfade wurden nicht zusätzlich neu ausgelöst. Die Prüfung ersetzt keinen Fingertest am physischen Display.
