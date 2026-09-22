import json
import logging
import os
import re
from datetime import datetime, time, timedelta

import pytz
import requests

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_ANALYSIS_MODEL = "gpt-5.6-terra"

WEEKDAYS = {
    "montag": 0,
    "dienstag": 1,
    "mittwoch": 2,
    "donnerstag": 3,
    "freitag": 4,
    "samstag": 5,
    "sonntag": 6,
}

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "lead_status": {
            "type": "string",
            "enum": [
                "no_interest",
                "interested",
                "very_interested",
                "customer",
            ],
        },
        "objections": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "Kein Bedarf",
                    "Internes Programm",
                    "Andere Partner",
                    "Kosten / Preis",
                ],
            },
        },
        "followup_requested": {
            "type": "boolean",
        },
        "followup_expression": {
            "type": "string",
        },
        "note": {
            "type": "string",
        },
    },
    "required": [
        "lead_status",
        "objections",
        "followup_requested",
        "followup_expression",
        "note",
    ],
    "additionalProperties": False,
}


class CallAiCrmAnalysisController(http.Controller):

    @http.route(
        "/call_ai_crm/analyze",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=True,
    )
    def analyze_transcript(self, **post):
        """Analysiert ein Transkript und liefert nur definierte CRM-Vorschläge."""

        transcript = (post.get("transcript") or "").strip()
        if not transcript:
            return self._json_response(
                {"error": "Es wurde kein Transkript zur Analyse übertragen."},
                status=400,
            )

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            _logger.error("OPENAI_API_KEY ist im Odoo-Prozess nicht gesetzt.")
            return self._json_response(
                {"error": "Die OpenAI-Konfiguration fehlt auf dem Server."},
                status=500,
            )

        instructions = (
            "Analysiere die transkribierte Voice-Note eines Mitarbeiters nach "
            "einem B2B-Akquisegespräch. Gib ausschließlich die durch das "
            "JSON-Schema vorgegebenen Werte zurück. "
            "Leadstatus: no_interest = kein Interesse, interested = Interesse, "
            "very_interested = deutliches oder konkretes Interesse, customer = "
            "bereits Kunde bzw. verbindlicher Kundenstatus. 'new' darf niemals "
            "zurückgegeben werden. "
            "Erkenne nur diese Einwände: Kein Bedarf, Internes Programm, "
            "Andere Partner und Kosten / Preis. Mehrere Einwände dürfen "
            "gleichzeitig vorkommen. "
            "Erkenne eine gewünschte Wiedervorlage. Übernimm eine relative "
            "Zeitangabe wie 'nächsten Dienstag' wortgetreu in "
            "followup_expression. Wenn keine Wiedervorlage genannt wird, setze "
            "followup_requested auf false und followup_expression auf einen "
            "leeren String. "
            "Die note ist eine kurze, sachliche, sinngemäße Gesprächsnotiz. "
            "Relevante Fakten müssen erhalten bleiben. Insbesondere gesuchte "
            "Fachkräfte wie Physiotherapeuten, Pflegefachkräfte oder Ärzte "
            "müssen in der Notiz genannt werden. Erfinde keine Informationen. "
            "Informationen zur Wiedervorlage gehören ausschließlich in die "
            "dafür vorgesehenen followup-Felder und dürfen nicht zusätzlich "
            "in der note wiederholt werden."
        )

        payload = {
            "model": OPENAI_ANALYSIS_MODEL,
            "store": False,
            "instructions": instructions,
            "input": transcript,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "call_analysis",
                    "strict": True,
                    "schema": ANALYSIS_SCHEMA,
                }
            },
        }

        try:
            response = requests.post(
                OPENAI_RESPONSES_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
        except requests.RequestException:
            _logger.exception("OpenAI-Analysedienst ist nicht erreichbar.")
            return self._json_response(
                {"error": "Der Analysedienst ist momentan nicht erreichbar."},
                status=502,
            )

        if not response.ok:
            _logger.error(
                "OpenAI-Analyse fehlgeschlagen: HTTP %s",
                response.status_code,
            )
            return self._json_response(
                {"error": "Das Transkript konnte nicht analysiert werden."},
                status=502,
            )

        try:
            response_data = response.json()
            output_text = self._extract_output_text(response_data)
            analysis = json.loads(output_text)
        except (ValueError, TypeError, KeyError):
            _logger.exception("OpenAI lieferte keine auswertbare Analyse.")
            return self._json_response(
                {"error": "Die Antwort des Analysedienstes ist ungültig."},
                status=502,
            )

        if analysis.get("followup_requested"):
            followup_datetime = self._parse_followup_expression(
                analysis.get("followup_expression", "")
            )
            analysis["followup_datetime"] = followup_datetime
        else:
            analysis["followup_datetime"] = None

        return self._json_response({"analysis": analysis})

    @staticmethod
    def _parse_followup_expression(expression):
        """Berechnet aus einfachen deutschen Zeitangaben einen festen Termin."""

        text_value = (expression or "").strip().lower()
        if not text_value:
            return None

        # Die Berechnung erfolgt in der Zeitzone des angemeldeten Benutzers.
        # Dadurch bleibt 10:00 Uhr auch tatsächlich 10:00 Uhr Ortszeit.
        timezone_name = request.env.user.tz or "Europe/Berlin"
        try:
            user_timezone = pytz.timezone(timezone_name)
        except pytz.UnknownTimeZoneError:
            user_timezone = pytz.timezone("Europe/Berlin")

        now_local = datetime.now(user_timezone)
        target_date = None

        if "übermorgen" in text_value:
            target_date = now_local.date() + timedelta(days=2)
        elif "morgen" in text_value:
            target_date = now_local.date() + timedelta(days=1)
        elif "heute" in text_value:
            target_date = now_local.date()
        else:
            for weekday_name, weekday_number in WEEKDAYS.items():
                if weekday_name not in text_value:
                    continue

                days_ahead = (weekday_number - now_local.weekday()) % 7

                # Ein genannter Wochentag bezeichnet die nächste zukünftige
                # Ausführung. Am gleichen Wochentag wird daher eine Woche
                # weitergerechnet.
                if days_ahead == 0:
                    days_ahead = 7

                target_date = now_local.date() + timedelta(days=days_ahead)
                break

        if target_date is None:
            return None

        # Ohne konkrete Uhrzeit wird als feste Geschäftsregel 10:00 Uhr
        # verwendet. Das ist eine übliche Bürozeit und bleibt editierbar.
        target_hour = 10
        target_minute = 0

        time_match = re.search(
            r"(?<!\d)([01]?\d|2[0-3])(?:\s*[:.]\s*([0-5]\d))?\s*(?:uhr)?",
            text_value,
        )
        if time_match:
            target_hour = int(time_match.group(1))
            target_minute = int(time_match.group(2) or 0)
        elif "vormittag" in text_value:
            target_hour = 10
        elif "mittag" in text_value:
            target_hour = 12
        elif "nachmittag" in text_value:
            target_hour = 15

        local_datetime = user_timezone.localize(
            datetime.combine(
                target_date,
                time(hour=target_hour, minute=target_minute),
            )
        )

        # Für die Browserseite geben wir ISO 8601 mit Zeitzoneninformation
        # zurück. So kann der Wert später eindeutig in Odoo übernommen werden.
        return local_datetime.isoformat()

    @staticmethod
    def _extract_output_text(response_data):
        """Sucht den Textinhalt in der Responses-API-Antwort."""

        for output_item in response_data.get("output", []):
            if output_item.get("type") != "message":
                continue

            for content_item in output_item.get("content", []):
                if content_item.get("type") == "output_text":
                    text = (content_item.get("text") or "").strip()
                    if text:
                        return text

                if content_item.get("type") == "refusal":
                    raise ValueError("Die Analyse wurde vom Modell abgelehnt.")

        raise ValueError("Die Responses API enthielt keinen Ausgabetext.")

    @staticmethod
    def _json_response(payload, status=200):
        """Erzeugt für das Browser-Widget eine kleine JSON-Antwort."""
        return request.make_response(
            json.dumps(payload, ensure_ascii=False),
            headers=[("Content-Type", "application/json; charset=utf-8")],
            status=status,
        )
