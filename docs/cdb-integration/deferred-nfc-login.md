# Persönliche NFC-Anmeldung – Idee, noch nicht implementiert

23.11.2026. Chris möchte eine persönliche Anmeldung durch Vorhalten einer Karte.
Die bestehenden Talk-/Meeting-Aufsteller bleiben gemeinsame Modusschalter.

Der Rocketek wird aktuell nur zur UID-Abfrage genutzt; SHA-256 schützt die rohe
Kennung im Speicher, beweist aber nicht den Besitz eines sicheren Ausweises.
Abmelden und App-Neustart entfernen die persönliche Brain-Sitzung. Ein normaler
NFC-Tag kann deshalb keine abgemeldete Microsoft-Sitzung wiederherstellen.

Vorschlag: Nach regulärer Anmeldung eine persönliche Karte verknüpfen. Später
Karte kurz vorhalten und persönliche PIN bestätigen. Das Brain-Backend stellt
hierfür eine befristete, widerrufbare Geräte-Sitzung aus. Kein Microsoft-Token
und kein Passwort auf dem Tag. Dies benötigt einen neuen Backend-Vertrag und
Pi-Unterstützung; noch kein freigegebener Implementierungsauftrag.

Derselbe Leser kann erst die persönliche Karte und danach den Modusaufsteller
lesen. Das Abnehmen der persönlichen Karte meldet nicht sofort ab. Während
Aufnahme oder Talk bleiben Kontowechsel gesperrt. Eine neue Anmeldung ohne Netz
ist in diesem Vorschlag zunächst nicht vorgesehen.

Für vollständig automatisches Anmelden ohne PIN wären kryptografische Tags und
die tatsächliche Unterstützung durch Leser und Backend zuerst zu qualifizieren.

Belege: services/nfc_reader.py (UID), services/cdb_integration.py (Device-Code,
Logout) und services/room_mode.py (Neustart-Abmeldung).
[Microsoft-Gerätecode](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-device-code),
[NXP UID-Eigenschaften](https://www.nxp.com/docs/en/application-note/AN10927.pdf).
