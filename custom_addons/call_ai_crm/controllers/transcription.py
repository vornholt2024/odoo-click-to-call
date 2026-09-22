import json
import logging
import os

import requests

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)

OPENAI_TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"
MAX_AUDIO_SIZE = 25 * 1024 * 1024


class CallAiCrmTranscriptionController(http.Controller):

    @http.route(
        "/call_ai_crm/transcribe",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=True,
    )
    def transcribe_voice_note(self, **post):
        """Überträgt eine fertige Voice-Note serverseitig an OpenAI."""

        audio_file = request.httprequest.files.get("audio")
        if not audio_file:
            return self._json_response(
                {"error": "Es wurde keine Voice-Note übertragen."},
                status=400,
            )

        audio_data = audio_file.read()
        if not audio_data:
            return self._json_response(
                {"error": "Die Voice-Note enthält keine Audiodaten."},
                status=400,
            )

        if len(audio_data) > MAX_AUDIO_SIZE:
            return self._json_response(
                {"error": "Die Voice-Note ist größer als 25 MB."},
                status=400,
            )

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            _logger.error("OPENAI_API_KEY ist im Odoo-Prozess nicht gesetzt.")
            return self._json_response(
                {"error": "Die OpenAI-Konfiguration fehlt auf dem Server."},
                status=500,
            )

        filename = audio_file.filename or "voice-note.webm"
        mime_type = audio_file.mimetype or "audio/webm"

        try:
            response = requests.post(
                OPENAI_TRANSCRIPTION_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                },
                data={
                    "model": "gpt-transcribe",
                },
                files={
                    "file": (filename, audio_data, mime_type),
                },
                timeout=60,
            )
        except requests.RequestException:
            _logger.exception("OpenAI-Transkriptionsdienst ist nicht erreichbar.")
            return self._json_response(
                {"error": "Der Transkriptionsdienst ist momentan nicht erreichbar."},
                status=502,
            )

        if not response.ok:
            _logger.error(
                "OpenAI-Transkription fehlgeschlagen: HTTP %s - %s",
                response.status_code,
                response.text[:1000],
            )
            return self._json_response(
                {"error": "Die Voice-Note konnte nicht transkribiert werden."},
                status=502,
            )

        try:
            result = response.json()
        except ValueError:
            _logger.error(
                "OpenAI lieferte keine gültige JSON-Antwort: %s",
                response.text[:1000],
            )
            return self._json_response(
                {"error": "Die Antwort des Transkriptionsdienstes ist ungültig."},
                status=502,
            )

        transcript = (result.get("text") or "").strip()
        if not transcript:
            return self._json_response(
                {"error": "Es wurde kein gesprochener Text erkannt."},
                status=422,
            )

        return self._json_response({"text": transcript})

    @staticmethod
    def _json_response(payload, status=200):
        """Erzeugt für das Browser-Widget eine kleine JSON-Antwort."""
        return request.make_response(
            json.dumps(payload, ensure_ascii=False),
            headers=[("Content-Type", "application/json; charset=utf-8")],
            status=status,
        )
