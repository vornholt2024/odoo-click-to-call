# 📞 Odoo Click-to-Call & AI CRM Erweiterung

## 🧠 Projektbeschreibung

Dieses Projekt erweitert das Odoo CRM (res.partner) um eine integrierte Click-to-Call Funktion sowie eine vorbereitete Struktur für Speech-to-Text (STT) und KI-gestützte Analyse.

Ziel ist die Automatisierung von Vertriebsprozessen durch Kombination von Telefonie, Transkription und intelligenter Auswertung.

---

## 🚀 Features (aktuell)

* 📞 Click-to-Call Button im Kontaktformular
* 🧾 Erweiterung von `res.partner` um telefoniebezogene Felder
* 📊 Call History Modell (`call.history`)
* 🧩 Integration als Odoo Custom Modul (`call_ai_crm`)
* 🐳 Docker Setup für lokale Entwicklungsumgebung

---

## 🔜 Geplante Features (Projektumfang)

* 🎤 Voice-Notiz Aufnahme nach Telefonat
* 🧠 Speech-to-Text (z. B. Whisper)
* 🤖 KI-Analyse:

  * Gesprächszusammenfassung
  * Lead-Bewertung
  * automatische Wiedervorlage
* 🌍 Mehrsprachige Ausgabe (DE / TR)

---

## 🏗️ Architektur (vereinfacht)

Odoo (Frontend & Backend)
→ Click-to-Call
→ Telefonie (SIP / PBX)
→ Voice Input
→ STT
→ KI Analyse
→ Rückgabe an Odoo CRM

---

## ⚙️ Installation (lokal via Docker)

```bash
docker-compose up -d
```

Zugriff auf Odoo:

```
http://localhost:8069
```

---

## 📁 Projektstruktur

```
odoo17/
├── custom_addons/
│   └── call_ai_crm/
├── docker-compose.yml
└── README.md
```

---

## 🎯 Ziel des Projekts

Dieses Projekt ist Teil eines IHK-Abschlussprojekts im Bereich:

**Fachinformatiker Anwendungsentwicklung**

Fokus:

* Prozessautomatisierung im Vertrieb
* Integration moderner Technologien (Telefonie + KI)
* Praxisnahe Umsetzung in Odoo

---

## 👤 Autor

Jörg Vornholt
GitHub: https://github.com/vornholt2024

---
