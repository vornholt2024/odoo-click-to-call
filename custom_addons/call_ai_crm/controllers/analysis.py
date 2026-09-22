import json
import logging
import os

import requests

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_ANALYSIS_MODEL = "gpt-5.6-terra"

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
                    "no_need",
                    "internal_program",
                    "other_partner",
                    "price",
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
            "Erkenne nur diese Einwände: no_need = kein Bedarf, "
            "internal_program = eigenes/internes Programm, other_partner = "
            "Zusammenarbeit mit anderen Partnern, price = Kosten oder Preis. "
            "Mehrere Einwände dürfen gleichzeitig vorkommen. "
            "Erkenne eine gewünschte Wiedervorlage. Übernimm eine relative "
            "Zeitangabe wie 'nächsten Dienstag' wortgetreu in "
            "followup_expression. Wenn keine Wiedervorlage genannt wird, setze "
            "followup_requested auf false und followup_expression auf einen "
            "leeren String. "
            "Die note ist eine kurze, sachliche, sinngemäße Gesprächsnotiz. "
            "Relevante Fakten müssen erhalten bleiben. Insbesondere gesuchte "
            "Fachkräfte wie Physiotherapeuten, Pflegefachkräfte oder Ärzte "
            "müssen in der Notiz genannt werden. Erfinde keine Informationen."
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

        return self._json_response({"analysis": analysis})

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
