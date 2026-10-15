# Revision 3: frühe Prüfung findet fehlende statische Antworten

Der Quellenvergleich nutzt jetzt den echten committed Kandidaten. Der Original-
Lauf stoppt jedoch vor dem ersten akzeptierten Messpunkt: Der Diagnose-Server
liefert 404 für die Schriftdatei und das Browser-Icon. Dieser fehlgeschlagene
Lauf ist kein Ressourcenvergleich und keine Freigabe-Evidenz. Bereinigung bestätigt.

Die unmittelbare Prüfung am echten Pi ergibt unterschiedliche Fälle:
`/assets/InterVariable.woff2` liefert auch produktiv 404, `/favicon.ico` hingegen
204. Die Schrift ist im Repository versioniert (352.240 Bytes); die derzeitige
App-Paket-Positivliste enthält `.woff2` nicht. Das ist ein eigenständiger
Auslieferungsbefund, keine bewiesene Ursache des CPU-/Speicheranstiegs.
Er wird hier nicht durch eine ungeprüfte Schrift-/Layoutänderung vermischt.

Revision 4 hält beide tatsächlichen Antworten im RAM der Vorschau und protokolliert
die vorhandene fehlende Schrift ausdrücklich. Unbekannte fehlende Assets bleiben
Fehler; insbesondere ein falsches `/play` würde nicht akzeptiert. Jeder Messpunkt
prüft zusätzlich die vollständige Bildadresse und erfolgreiche Dekodierung.
Die App bleibt 0.5.55; kein produktiver Eingriff durch diesen Diagnoseversuch.
