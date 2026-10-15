# Revision 2: Nebenabfragen vorhanden, Kandidat weiterhin falsch

Die ergänzten Antworten für Wissensbereiche und frühere Mikrofon-Testdatei
lieferten jeweils HTTP 200. Der Originaldurchlauf beendete seine fünf Minuten
ohne protokollierten API-Fehler. Die Gegenprobe enthielt jedoch weiterhin den
falschen `setIcon`-Aufruf aus Revision 1. Ihr Quellenhash weicht vom echten
committed Fix ab. Sie ist **kein gültiger Kandidatentest**.

Nach Entdecken dieses Fehlers wurde nur der Hauptprozess des isolierten
Diagnose-Diensts per SIGINT beendet. Seine `finally`-Bereinigung schloss Browser,
Server und Wächter; die Produktions-App und der Langzeitmonitor blieben aktiv.
Dass systemd SIGINT als erfolgreichen Dienstabschluss meldet, bedeutet hier
keinen bestandenen Test: `profile_written` ist false und die Messung unvollständig.

Originalbericht, partielle Gegenmessung, Abbruchgrund, Quellen und
Bereinigungsnachweise bleiben erhalten. Keine Aufnahmeinhalte oder
Wissensbereichsnamen in den Berichten. Diese Revision begründet keine Auslieferung.
