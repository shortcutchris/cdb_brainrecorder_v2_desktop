# Zurückgestellt: Brain-Anmeldung ohne Abtippen des Gerätecodes

Stand: 23.11.2026. Nutzerentscheidung: Idee festhalten, vorerst nicht umsetzen.

## Wunsch und heutiger Stand

Nach Scannen am Pi soll auf dem Handy bereits der richtige Anmeldevorgang
geöffnet sein. Der Benutzer soll keinen Gerätecode mehr abschreiben müssen.

Heute fordert `services/cdb_integration.py` bei Microsoft einen Gerätecode an.
`studio/cdb.js` und `studio/welcome.js` zeigen einen QR-Code zur allgemeinen
Microsoft-Geräteanmeldeseite. Die Zuordnung zum Pi erfolgt durch den dort
eingegebenen Code. Das bleibt unverändert.

## Vorgemerkter Lösungsweg

1. Der Pi fordert eine kurzlebige Anmeldeanfrage bei CDB an.
2. Der QR-Code öffnet die zu dieser Anfrage gehörende CDB-Seite auf dem Handy.
3. Dort wird die vorhandene Anmeldung verwendet oder die reguläre Anmeldung
   einschließlich gegebenenfalls erforderlicher Mehrfaktorbestätigung geöffnet.
4. Der Benutzer bestätigt das konkrete Gerät und das verwendete Konto.
   Ein übereinstimmendes Erkennungsmerkmal auf Handy und Pi hilft bei der Zuordnung.
5. Der Pi erhält eine eigene, begrenzte und widerrufbare Sitzung für dieses Konto,
   diesen Mandanten und diese Umgebung. Die Handy-Sitzung wird nicht kopiert.
6. Abmelden am Pi beendet dessen Berechtigung. Die bisherige Gerätecode-Anmeldung
   bleibt als Rückfallweg erhalten.

Das ist ein Vorschlag für einen eigenen CDB-Ablauf, keine bloße Änderung des
QR-Bildes. Pi, CDB-Webseite und Server müssen zusammenpassen; die heutigen
API-Aufrufe mit Microsoft-Bearer-Token benötigen einen abgestimmten zukünftigen
Berechtigungsvertrag. Kein ungeprüfter Zusatzparameter an Microsoft-URLs.

## Abgrenzung

Keine Umsetzung, kein Serverauftrag, keine neue Kopplung oder Freischaltung.
Die vorgeschlagene [lokale Hilfe mit Fernbedienung](../local-portal/README.md)
ist unabhängig davon. Keine Auswirkung dieses Dokumentationsstands auf
App-Updates oder neue SD-Images.
