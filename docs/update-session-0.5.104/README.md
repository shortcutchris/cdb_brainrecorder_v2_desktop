# Recorder Studio 0.5.104 · Anmeldung beim App-Update behalten

24. November 2026. 0.5.103 war vorbereitet, aber noch nicht auf dem Pi installiert.
Diese Version enthält dessen komplette Dialog-/Timeränderungen und ergänzt die
vom Nutzer gewünschte Anmeldung über den App-Austausch hinweg.

## Verhalten

Nur `/api/management/prepare` mit lokaler Geräteverwaltungsauthentisierung darf
eine Sitzungsübergabe ausstellen. Alle bisherigen Aufnahme-, Talk-, Timer-,
Wiedergabe- und Übertragungssperren bleiben erhalten. Offene Anmeldung oder
Startvorbereitung verhindern ein Update zusätzlich.

`management/update-session.json` enthält Konto-/Mandanten-/Serverbindung,
Sitzungsepoche, Linux-Bootkennung und monotone Fristen; keine CDB-Zugangstokens.
Dateirechte 0600. Die Übergabe gilt einmalig, maximal 120 Sekunden, nur unter dem
passenden Wartungsauftrag und vor Ablauf der ursprünglichen Ruhefrist. Sie wird
auch bei ungültigem Inhalt entfernt. Wartung zählt nicht als Benutzeraktivität.
Abmeldung und abgebrochener Wartungsauftrag löschen die Übergabe.

Ein normaler App-Start ohne Übergabe, Systemneustart, anderer Benutzer/Mandant/
Server oder abgelaufene Frist meldet weiterhin ab. Bestehende CDB-Token werden
normal geprüft/erneuert; eine serverseitig ungültige Anmeldung wird nicht umgangen.
Betreiber-PIN-Freigabe, Browser-Fernbedienungsfreigaben und Aufnahme-/Talk-Absichten
werden nicht wiederhergestellt. Ein aufliegender NFC-Tag muss wie bisher erst
abgenommen und erneut aufgelegt werden.

## Update und frische Installation

`services/update_session.py` liegt in der bestehenden App-Allowlist und wird in
signierten Updates und sauberen Image-Rezepten aus Git mitgeliefert. Keine neue
Abhängigkeit, Berechtigung, Datenbankmigration oder Änderung der Displayfirmware.
Ein frisches Image enthält keine Übergabedatei und verlangt normal die Anmeldung.

Die Erstinstallation von 0.5.102 verwendet den verifizierten neuen Helfer unter
dem bestehenden Wartungsschutz: Kontobindung und ursprüngliche Ruhefrist werden
vor dem Wartungsaufruf aufgenommen. Ab 0.5.104 erledigt der normale geschützte
Prepare-Endpunkt dies selbst. Keine Zugangsdaten aus einem früheren Backup
zurückkopieren. Release/Fehlerpfad verwirft ungenutzte Übergaben.

## Prüfstand

- 147 Python-Tests: Studio, Raummodus, Update-Übergabe, NFC, Geräteverwaltung,
  Kunden-Image-Paket. Alle bestanden.
- 170 JavaScript-Tests der Benutzeroberfläche bestanden.
- Neun gezielte Übergabetests: einmalige Übernahme, ursprüngliche Ruhefrist,
  Reboot, Ablauf, andere Kontobindung, beschädigte Daten, frische Installation,
  Abbruch, Standard-Powerpfad, offener Login/Start und Schreibfehler.
- Bestehender NFC-Test bestätigt: beim Start bereits aufgelegter Tag startet
  keine Aktion; erst Abnehmen und neues Auflegen löst aus.
- Signiertes Update: 157 Dateien verifiziert; sauberes Image-Rezept: 164
  Quelldateien verifiziert. Installationsnachweis: [deployment.json](deployment.json).

Das Image-Rezept ist kein gebautes oder am Gerät zertifiziertes SD-Image.

## Installation und Geräteprüfung am 24. November 2026

Um 12:18 Uhr MEZ wurde 0.5.104 aus Commit
`07223e7fdffcbe35f206afa391d4292d63ffe068` installiert. Der Benutzer hatte das
Bestätigen des noch offenen Timer-Alarms ausdrücklich freigegeben. Der Alarm
steht jetzt auf erledigt; die übrigen drei erledigten Timer blieben unverändert.

Die bisherige Anmeldung blieb beim App-Wechsel erhalten, mit identischer
Kontobindung und Sitzungsepoche. Die einmalige Übergabe wurde verbraucht.
Wartung wurde freigegeben, App, Kiosk und LCD-Begleiter liefen anschließend.
Konfiguration, bestehende Aufnahmen, NFC-Zuordnungen und Raummodusregeln blieben
beim Update erhalten. Kein Systemneustart oder Abschalten ausgeführt.

Am physischen 1280 × 720-Pi-Kiosk über den privaten Bildschirmzugriff geprüft:

- Kontodialog öffnen und über Escape schließen: weiterhin angemeldet.
- Timerformular **Zeit** und **Titel & Klang**: vollständig sichtbar, große
  Bedienelemente, fester Startbereich, kein Scrollen erforderlich.
- Verlauf mit vier vorhandenen Einträgen: drei auf Seite 1, einer auf Seite 2;
  Seitenwechsel am tatsächlichen Kiosk erfolgreich, keine Überlappung.
- Abschließender Status: 0.5.104, angemeldet, keine Aufnahme, Talk inaktiv,
  kein offener Timer-Alarm.

Grenze dieser Geräteprüfung: Die Koordinatenklicks des VNC-Zugriffs wurden nicht
zuverlässig auf das gedrehte Display abgebildet. Deshalb wurden weitere
Prüfschritte nur per Tastaturnavigation ausgeführt. Außentipp, Bildschirmtastatur,
1024 × 600 und die weiteren Dialog-/Aktivitätsszenarien sind durch die separate
Browserprüfung in [0.5.103](../ui-audit-0.5.103/README.md) belegt, aber nicht erneut
als physischer Fingertest auf diesem Gerät. Ein neuer Hörtest wurde nicht gemacht.

## Vorfall bei der Fernprüfung

Ein fehlgeleiteter Koordinatenklick startete versehentlich eine 15 Sekunden lange
Aufnahme. Sie wurde unmittelbar gestoppt; der Benutzer wurde darüber informiert.
Die konfigurierte CDB-Verarbeitung hatte bereits begonnen und wurde abgeschlossen.
Audio-, Transkript- und Zusammenfassungsinhalte wurden für die Prüfung nicht
ausgelesen. Anschließend wurde ausschließlich diese versehentlich erstellte
Sitzung über den normalen Löschweg entfernt; ihre verbliebenen lokalen
Verarbeitungsdateien wurden ebenfalls entfernt. Alle vorherigen Sitzungen blieben
erhalten. Eine Löschung eventueller serverseitiger Verarbeitungsreste ist damit
nicht nachgewiesen. Weitere Koordinatenklicks wurden unterlassen.
