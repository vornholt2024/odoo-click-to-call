# Odoo 17 Click-to-Call und KI-gestützte CRM-Analyse

Dieses Repository enthält mein 80-stündiges IHK-Abschlussprojekt zum Fachinformatiker für Anwendungsentwicklung. Die Odoo-Erweiterung digitalisiert einen zuvor Excel-basierten Prozess der B2B-Telefonakquise und verbindet Telefonie, strukturierte Nachbearbeitung und KI-gestützte Vorschläge in einem durchgängigen Arbeitsablauf.

## Ausgangssituation und Ziel

Kontaktdaten, Gesprächsergebnisse und Wiedervorlagen wurden zuvor über mehrere Werkzeuge gepflegt. Ziel war eine zentrale Lösung in Odoo 17, die Medienbrüche reduziert, Gesprächsdaten nachvollziehbar ablegt und den Mitarbeiter bei der Nachbearbeitung unterstützt.

## Funktionsumfang

- Click-to-Call aus dem Odoo-Kontakt über den unter Windows registrierten `sip:`-Protokollhandler und MicroSIP
- Gesprächsstatus mit den Zuständen Bereit, Im Gespräch und Nachbearbeitung
- Benutzerbezogene Reservierung eines Kontakts durch einen Soft-Lock
- Automatische Freigabe verwaister oder abgelaufener Vorgänge
- Anrufhistorie mit Start, Ende, Dauer, Telefonnummer, Mitarbeiter und Ergebnis
- Erfassung typischer Einwände und strukturierter Gesprächsnotizen
- Kennzahlen zu Anzahl, Gesamt- und Durchschnittsdauer der Anrufe
- Wiedervorlagen einschließlich normaler Odoo-Aktivität
- Voice-Note-Aufnahme des Mitarbeiters im Browser
- serverseitige Speech-to-Text-Verarbeitung über die OpenAI API
- strukturierte Textanalyse mit JSON-Schema
- regelbasierte Klassifikation von Leadstatus und Einwänden
- manuelle Prüfung und Korrektur aller Vorschläge vor der endgültigen Speicherung

## Vereinfachter Ablauf

1. Der Mitarbeiter startet den Anruf aus dem Odoo-Kontakt.
2. Odoo übergibt die SIP-Adresse an MicroSIP. Die Telefonie läuft asynchron und besitzt keinen CTI-Rückkanal.
3. Nach Gesprächsende wechselt der Kontakt in die Nachbearbeitung.
4. Der Mitarbeiter kann eine kurze Voice Note aufnehmen.
5. Das Odoo-Backend überträgt die Aufnahme zur Transkription und anschließend das Transkript zur strukturierten Analyse.
6. Eigene Geschäftsregeln prüfen und ergänzen die Analyse.
7. Der Mitarbeiter kontrolliert und korrigiert die Vorschläge.
8. Erst nach der ausdrücklichen Bestätigung werden die Daten in Odoo/PostgreSQL gespeichert.

## KI und Geschäftslogik

Die KI erzeugt eine sachliche Gesprächsnotiz und erkennt, ob eine Wiedervorlage gewünscht wurde. Die endgültige Klassifikation bleibt nachvollziehbar im Anwendungscode:

- Leadstatus und Einwände werden durch feste Geschäftsregeln bestimmt.
- Relative Zeitangaben werden in einen konkreten Termin in der Zeitzone des Benutzers umgerechnet.
- KI-Ergebnisse werden zunächst ausschließlich in Entwurfsfelder übernommen.
- Die fachliche Entscheidung und Speicherung erfolgen erst nach der Kontrolle durch den Mitarbeiter.

Damit bleibt die KI ein Assistenzsystem und trifft keine endgültige CRM-Entscheidung.

## Datenschutzbewusste Gestaltung

- Aufgezeichnet wird ausschließlich eine bewusst gestartete Sprachnotiz des Mitarbeiters nach dem Telefonat.
- Kundenaudio und das eigentliche Telefongespräch werden nicht aufgezeichnet.
- Die Audiodatei wird nicht dauerhaft in Odoo gespeichert.
- Der OpenAI-API-Schlüssel bleibt auf dem Server und wird nicht an den Browser ausgeliefert.
- Bei der strukturierten Textanalyse wird die Speicherung der API-Antwort mit `store: false` deaktiviert.

Diese technischen Maßnahmen unterstützen Datenminimierung und kontrollierte Verarbeitung. Sie ersetzen keine vollständige organisatorische und rechtliche Datenschutzprüfung für einen Produktivbetrieb.

## Technische Architektur

- Odoo 17 Community
- Python und Odoo ORM
- XML-Views
- JavaScript und Owl
- PostgreSQL 15
- Docker Compose unter Linux/WSL2
- REST und JSON
- MicroSIP über den `sip:`-Protokollhandler
- OpenAI Audio Transcriptions API und Responses API

## Projektstruktur

```text
.
├── custom_addons/
│   └── call_ai_crm/
│       ├── controllers/       # Transkription und strukturierte Analyse
│       ├── data/              # Cronjob für abgelaufene Reservierungen
│       ├── models/            # Kontakte und Anrufhistorie
│       ├── security/          # Odoo-Zugriffsrechte
│       ├── static/src/        # JavaScript/Owl und Templates
│       ├── views/             # Erweiterte Kontaktansichten
│       └── __manifest__.py
├── .env.example
├── docker-compose.yml
└── README.md
```

## Lokale Installation

Voraussetzungen sind Docker Desktop oder Docker Engine mit Docker Compose.

```bash
git clone https://github.com/vornholt2024/odoo-click-to-call.git
cd odoo-click-to-call
cp .env.example .env
```

Anschließend in `.env` einen eigenen OpenAI-API-Schlüssel sowie lokale Entwicklungskennwörter eintragen und die Container starten:

```bash
docker compose up -d
```

Odoo ist danach lokal unter `http://localhost:8069` erreichbar. In Odoo den Entwicklermodus aktivieren, die App-Liste aktualisieren und das Modul **Call AI CRM** installieren.

> Die mitgelieferte Konfiguration ist ausschließlich für eine lokale Entwicklungs- und Demonstrationsumgebung vorgesehen. Für einen Produktivbetrieb sind insbesondere Secret-Management, HTTPS, Backups, Berechtigungskonzept, Monitoring und Datenschutzprozesse gesondert umzusetzen.

## Sicherheit und Abgrenzung

- Die API-Endpunkte erfordern einen angemeldeten Odoo-Benutzer und CSRF-Schutz.
- Anrufhistorien sind für interne Benutzer lesbar, werden aber ausschließlich über die serverseitig geprüften Arbeitsabläufe angelegt und aktualisiert.
- Der Soft-Lock verhindert parallele Nachbearbeitung desselben Kontakts.
- Die Telefonie ist bewusst keine vollständige CTI-Integration.
- Das Projekt ist ein IHK-Projekt und Demonstrator, keine unverändert produktiv einsetzbare Standardlösung.
- Automatisierte Tests sind derzeit nicht Bestandteil des Repositories; die Projektfunktionen wurden anhand definierter Anwendungsszenarien geprüft.

## Autor

**Heinz-Jörg Vornholt**  
Umschulung zum Fachinformatiker für Anwendungsentwicklung  
IHK-Abschlussprojekt 2026

GitHub: https://github.com/vornholt2024
