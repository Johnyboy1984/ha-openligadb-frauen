# OpenLigaDB Frauen

**Erste Testversion 0.1.0b1** einer Home-Assistant-Integration für die Frauen-Bundesliga (`ffb1`) und den DFB-Pokal der Frauen (`dfbf`). Keine API-Schlüssel und keine YAML-Sensoren erforderlich. Die Integration ist unabhängig von OpenLigaDB, DFB und Home Assistant und kein offizielles Produkt dieser Organisationen.

## Aktueller Stand

Dieses öffentliche Repository enthält die erste Testversion. Die Installation erfolgt zunächst über HACS als benutzerdefiniertes Repository oder manuell. Die automatischen Prüfungen findest du unter **Actions**; es gibt noch keine Aufnahme in den allgemeinen HACS-Katalog.

Die portable Testsuite prüft die Auswahlregeln, Ergebnisse, lokale Datenkorrekturen, Zeitzonen und API-Fehler. Ein zusätzlicher GitHub-Actions-Workflow testet Einrichtung, Sensoren und Entladen mit einer echten Home-Assistant-Testumgebung unter Linux; **dieser Workflow wurde hier noch nicht ausgeführt**. Die Version wurde noch nicht in einer laufenden Home-Assistant-Instanz installiert. Bitte zuerst parallel zu vorhandenen Sensoren testen.

## Funktionen

- Einrichtung unter **Einstellungen → Geräte & Dienste → Integration hinzufügen → OpenLigaDB Frauen**.
- Einen Eintrag für die Bundesliga, einen weiteren für den Frauenpokal anlegen.
- Bundesliga: den gesamten Spieltag zwölf Stunden vor dessen erstem Anstoß anzeigen. Bis dahin bleiben die Ergebnisse des vorherigen Spieltags sichtbar. Nachholspiele älterer Spieltage setzen die Auswahl nicht zurück.
- Pokal: alle Spiele der aktuellen Runde inklusive Ergebnisse. Wechsel zur nächsten Runde erst beim ersten Anstoß dieser Runde.
- Eine gemeinsame Saisonabfrage pro Wettbewerb und Abrufintervall für alle Begegnungssensoren. Standard: fünf Minuten. Bundesliga-Tabelle zusätzlich höchstens alle 30 Minuten.
- Korrekte Daten werden vor dem Anlegen der Sensoren abgerufen. Bei einem fehlgeschlagenen Erstabruf wartet HA auf einen erneuten Versuch; es gibt keinen erfundenen Spieltag-1-Ersatzwert.
- Rundensensor mit vollständiger Begegnungsliste, einzelne Begegnungen, nächstes und letztes Spiel; zusätzlich Bundesliga-Tabelle und Platzierungssensoren.
- Vereinslogos mit Ersatzadressen für bekannte defekte SGS-Essen- und fehlende Hoffenheim-Links.
- Saison, Abrufintervall und die bekannte Ergebniskorrektur sind über die Optionen einstellbar.

## Installation zum ersten Test (ohne GitHub/HACS möglich)

1. Die Installations-ZIP entpacken. Den enthaltenen Ordner `custom_components/openligadb_frauen` vollständig nach `/config/custom_components/openligadb_frauen` kopieren. `manifest.json` muss direkt in diesem Ordner liegen, nicht in einem weiteren Unterordner.
2. Die bisherigen REST-/Template-Sensoren und ihre Start-Automatisierung zunächst behalten. Die neue Integration verwendet eigene IDs und ändert oder entfernt bestehende Entitäten nicht.
3. Home Assistant neu starten. Das unterbricht Automationen und Integrationen kurzzeitig.
4. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **OpenLigaDB Frauen** suchen. Falls sie nicht erscheint, die Browserseite neu laden und im Protokoll nach `openligadb_frauen` suchen.
5. **Frauen-Bundesliga**, Saisonstartjahr **2026** wählen. Anschließend die Integration erneut hinzufügen und **DFB-Pokal Frauen**, ebenfalls **2026**, wählen. `2026` bedeutet Saison 2026/27.
6. Erst die neuen Sensorwerte vergleichen, dann die Dashboard-Beispiele verwenden. Die alten Karten bis zur erfolgreichen Prüfung behalten.

Mindestversion: Home Assistant **2026.10.0**. Die erste Version ist auf die derzeitige Bundesliga mit 14 Teams und sieben Spielen pro Spieltag sowie Pokalrunden mit höchstens 16 Begegnungen zugeschnitten. Der Rundensensor enthält auch bei mehr Begegnungen die gesamte Liste; einzelne Pokalsensoren gibt es für die ersten 16 Plätze.

## Später über HACS installieren

Nach der Veröffentlichung des vollständigen Repository-Inhalts auf einem **öffentlichen** GitHub-Repository:

1. HACS öffnen → Menü → **Benutzerdefinierte Repositories**.
2. Die tatsächliche Repository-URL eintragen, Kategorie **Integration** wählen.
3. **OpenLigaDB Frauen** herunterladen und Home Assistant neu starten.
4. Die Einträge wie oben über Geräte & Dienste einrichten.

`hacs.json`, die erforderliche Verzeichnisstruktur und lokale Brand-Icons sind enthalten. Ein eigenes Repository in HACS hinzuzufügen ist unabhängig von einer späteren Aufnahme in den allgemeinen Katalog. Vor einer Veröffentlichung sollten die GitHub-Workflows erfolgreich laufen; HACS-/hassfest-Validierungen sind zusätzliche Prüfungen vor dem Release.

## Sensoren

Die automatisch erzeugten IDs sollten wie folgt aussehen. Bei vorhandenen Namenskollisionen kann HA eine Nummer anhängen; dann die tatsächliche ID im Dashboard einsetzen.

| Sensor | Inhalt |
|---|---|
| `sensor.openligadb_frauen_bundesliga_aktuelle_runde` | aktueller Spieltag, Attribut `spiele` mit allen sieben Begegnungen |
| `sensor.openligadb_frauen_bundesliga_spiel_01` … `_07` | einzelne Begegnungen |
| `sensor.openligadb_frauen_bundesliga_nachstes_spiel` | nächstes bzw. noch laufendes, nicht als beendet gemeldetes Spiel |
| `sensor.openligadb_frauen_bundesliga_letztes_spiel` | zuletzt beendetes Spiel |
| `sensor.openligadb_frauen_bundesliga_tabelle` | Teamanzahl, Attribut `table` mit der Tabelle |
| `sensor.openligadb_frauen_bundesliga_platz_01` … `_14` | Mannschaft und Statistik pro Tabellenplatz |
| `sensor.openligadb_dfb_pokal_frauen_aktuelle_runde` | aktuelle Pokalrunde, Attribut `spiele` mit sämtlichen Begegnungen |
| `sensor.openligadb_dfb_pokal_frauen_spiel_01` … `_16` | einzelne Pokalbegegnungen |

Die Einzelspiele liefern sowohl die neuen flachen Attribute `heim`, `gast`, `anstoss`, `ergebnis`, `heim_logo`, `gast_logo` als auch die bisherigen Felder `group`, `team1`, `team2`, `matchDateTime` und `matchResults`. Nicht belegte Slots werden `unavailable`; ihre alten Begegnungen bleiben nicht stehen. Das gilt etwa für die überzähligen Slots ab dem Viertelfinale.

`spiele`, `matches` und Tabellenlisten werden nicht als große Attributlisten im Recorder archiviert. Aktuelle Werte bleiben für Dashboards und Automationen verfügbar.

## Dashboards und Wechsel von der bisherigen YAML

Unter `examples/` liegen Karten für beide Spielpläne und die Bundesliga-Tabelle; `flex-table-card` muss wie bisher über HACS installiert sein. Die Integration selbst installiert keine Dashboard-Karten.

1. Die neuen Einträge parallel einrichten und prüfen.
2. Die bisherigen Karten duplizieren oder die Beispiele als zusätzliche Karten einfügen.
3. In der bisherigen Liga-Tabelle genügt für die Platzierungssensoren der Wechsel von `sensor.frauen_bundesliga_platz_*` zu `sensor.openligadb_frauen_bundesliga_platz_*`. Die Spaltenattribute bleiben erhalten.
4. Spielplan-Karten auf den jeweiligen neuen Rundensensor umstellen oder die Beispiele verwenden.
5. Erst danach die bisherigen YAML-Definitionen entfernen bzw. auskommentieren und ihre Start-Automatisierung deaktivieren. Andere REST-Sensoren unter `rest:` beibehalten. Konfiguration vor dem Neuladen/Neustart prüfen.

Es gibt **keine automatische Übernahme oder Umbenennung** bestehender REST-/Template-Entitäten. Die Entity-Registry wird nicht ungefragt verändert. Eine Rückkehr ist möglich, indem die alten Definitionen wieder aktiviert und die Karten auf die alten IDs zurückgestellt werden.

## Datenqualität und Grenzen

OpenLigaDB wird von der Community gepflegt. Die Integration kann verspätete oder falsche Meldungen der Datenquelle nicht generell erkennen und garantiert keine Live-Ergebnisse. Fehlende Termine/Platzhalter werden nicht als reale Begegnungen verwendet. Die erste Version enthält folgende eng begrenzte lokale Korrekturen:

- Bayern–Leverkusen, Match-ID 88746, Saison 2026: ausschließlich das bekannte vertauschte Endergebnis 0:1 wird zu 1:0 korrigiert. Die Korrektur ist in den Optionen abschaltbar und am Spiel unter `corrections` mit Quellenangabe sichtbar.
- SGS-Essen-Logo von der offiziellen Vereinswebsite, Ersatzlogo für Hoffenheim sowie Ersatz für bekannte defekte Leverkusen-Logo-Adressen.

Die Quellen werden nicht verändert. Der Saisonwechsel erfolgt bewusst über die Optionen, nicht automatisch am 1. Juli. Ein Wettbewerb kann pro HA-Instanz einmal konfiguriert werden; für eine andere Saison dessen Optionen ändern. Wird der erste Saisonspieltag deutlich früher als die übrigen Partien ausgetragen, zählt dessen erster tatsächlicher Anstoß für die 12-Stunden-Regel. Verschobene Spiele mit altem Datum und fehlender Beendet-Meldung können die Auswahl von „nächstes Spiel“ verfälschen; die Spieltagsauswahl bleibt anhand der höchsten begonnenen Runde stabil.

Bei einem Abruffehler nach erfolgreicher Einrichtung behalten HA/coordinator die letzten Daten intern, markieren die abhängigen Sensoren aber als nicht verfügbar. Das vermeidet die Anzeige scheinbar frischer Ergebnisse. Ein Fehler der Tabellenabfrage betrifft die Tabelle; die Begegnungen können weiter aktualisiert werden. Der nächste Abruf versucht es erneut.

## Entfernen

Unter Geräte & Dienste die Einträge löschen. Anschließend bei Bedarf in HACS deinstallieren bzw. den Integration-Ordner entfernen. Dashboard-Karten vorher auf die bisherigen Sensoren zurückstellen oder entfernen; eine Deinstallation stellt alte YAML-Sensoren nicht selbst wieder her.

## Entwicklung und Prüfung

Portable Tests (Python 3.13+):

```sh
python -m pip install aiohttp voluptuous tzdata ruff
python -m unittest discover -s tests -v
ruff check .
python -m compileall -q custom_components
```

Vollständige HA-Tests in einer separaten Linux-/Python-3.14-Umgebung:

```sh
python -m pip install pytest-homeassistant-custom-component
python -m pytest ha_tests -v
```

Referenzen: [OpenLigaDB](https://www.openligadb.de/), [API-Beispiele](https://github.com/OpenLigaDB/OpenLigaDB-Samples), [HA Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/), [DataUpdateCoordinator](https://developers.home-assistant.io/docs/integration_fetching_data/), [HACS-Anforderungen](https://www.hacs.xyz/docs/publish/integration/).

