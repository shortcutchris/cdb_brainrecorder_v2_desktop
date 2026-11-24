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
- Abnahme am realen Pi wird nach der Installation mit Versionsstand und
  bereinigter Prüfevidenz ergänzt.

Das Image-Rezept ist kein gebautes oder am Gerät zertifiziertes SD-Image.
