/** @odoo-module **/

import { Component, onWillUnmount, onWillUpdateProps, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Voice-Note-Aufnahme für die Nachbearbeitung eines Telefonats.
 *
 * Die Aufnahme entsteht im Browser und wird nach dem Stoppen an das
 * Odoo-Backend übertragen. Erst das Backend kommuniziert mit OpenAI,
 * damit der API-Schlüssel niemals an den Browser ausgeliefert wird.
 *
 * Nach der Transkription wird der erkannte Text analysiert. Die daraus
 * entstehenden Werte werden nur als Entwurf in die vorhandenen Felder
 * der Nachbearbeitung übernommen. Der Mitarbeiter kann sie anschließend
 * prüfen und ändern, bevor er sie mit "Speichern" bestätigt.
 */
export class VoiceNoteRecorder extends Component {
    static template = "call_ai_crm.VoiceNoteRecorder";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({
            recording: false,
            transcribing: false,
            analyzing: false,
            transcript: null,
            analysis: null,
            error: null,
        });

        this.mediaRecorder = null;
        this.mediaStream = null;
        this.audioChunks = [];

        /*
         * Transkript und Analyse gehören immer nur zur aktuellen
         * Nachbearbeitung. Sobald Speichern, Verwerfen oder ein anderer
         * Ablauf den Status "post_processing" verlässt, werden die
         * temporären Daten entfernt.
         */
        onWillUpdateProps((nextProps) => {
            const currentStatus = this.props.record.data.call_status;
            const nextStatus = nextProps.record.data.call_status;

            if (
                currentStatus === "post_processing" &&
                nextStatus !== "post_processing"
            ) {
                this.clearTemporaryData();
            }
        });

        onWillUnmount(() => {
            this.stopMediaStream();
        });
    }

    get canRecord() {
        return (
            this.props.record.data.call_status === "post_processing" &&
            this.props.record.data.lock_owned_by_current_user
        );
    }

    async startRecording() {
        if (
            !this.canRecord ||
            this.state.recording ||
            this.state.transcribing ||
            this.state.analyzing
        ) {
            return;
        }

        this.state.error = null;
        this.state.transcript = null;
        this.state.analysis = null;

        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: true,
            });

            this.audioChunks = [];
            this.mediaRecorder = new MediaRecorder(this.mediaStream);

            this.mediaRecorder.addEventListener("dataavailable", (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            });

            this.mediaRecorder.addEventListener("stop", async () => {
                const mimeType =
                    this.mediaRecorder.mimeType || "audio/webm";

                const audioBlob = new Blob(this.audioChunks, {
                    type: mimeType,
                });

                this.stopMediaStream();

                if (!audioBlob.size) {
                    this.state.error =
                        "Die Voice-Note enthält keine Audiodaten.";
                    return;
                }

                await this.transcribeRecording(audioBlob);
            });

            this.mediaRecorder.start();
            this.state.recording = true;
        } catch (error) {
            this.stopMediaStream();
            this.state.error =
                "Mikrofon konnte nicht geöffnet werden.";
        }
    }

    stopRecording() {
        if (!this.mediaRecorder || !this.state.recording) {
            return;
        }

        this.mediaRecorder.stop();
        this.state.recording = false;
    }

    async transcribeRecording(audioBlob) {
        this.state.transcribing = true;
        this.state.error = null;

        try {
            const formData = new FormData();
            formData.append(
                "audio",
                audioBlob,
                this.getAudioFilename(audioBlob.type)
            );
            formData.append("csrf_token", odoo.csrf_token);

            const response = await fetch("/call_ai_crm/transcribe", {
                method: "POST",
                body: formData,
                credentials: "same-origin",
            });

            let result;
            try {
                result = await response.json();
            } catch (error) {
                throw new Error(
                    "Der Server hat keine gültige Antwort geliefert."
                );
            }

            if (!response.ok) {
                throw new Error(
                    result.error ||
                    "Die Voice-Note konnte nicht transkribiert werden."
                );
            }

            this.state.transcript = result.text;
            await this.analyzeTranscript(result.text);
        } catch (error) {
            this.state.error =
                error.message ||
                "Die Voice-Note konnte nicht transkribiert werden.";
        } finally {
            this.state.transcribing = false;
        }
    }

    async analyzeTranscript(transcript) {
        this.state.analyzing = true;
        this.state.analysis = null;

        try {
            const formData = new FormData();
            formData.append("transcript", transcript);
            formData.append("csrf_token", odoo.csrf_token);

            const response = await fetch("/call_ai_crm/analyze", {
                method: "POST",
                body: formData,
                credentials: "same-origin",
            });

            let result;
            try {
                result = await response.json();
            } catch (error) {
                throw new Error(
                    "Der Server hat keine gültige Analyse geliefert."
                );
            }

            if (!response.ok) {
                throw new Error(
                    result.error ||
                    "Das Transkript konnte nicht analysiert werden."
                );
            }

            this.state.analysis = result.analysis;
            await this.applyAnalysisSuggestion(result.analysis);
        } finally {
            this.state.analyzing = false;
        }
    }

    async applyAnalysisSuggestion(analysis) {
        /*
         * Die KI-Werte werden nur in die Entwurfsfelder übernommen.
         * Erst der vorhandene Speichern-Button bestätigt die Daten fachlich.
         */
        const objections = new Set(analysis.objections || []);

        const changes = {
            draft_result: analysis.lead_status || false,
            draft_note: analysis.note || false,
            objection_no_need: objections.has("Kein Bedarf"),
            objection_internal: objections.has("Internes Programm"),
            objection_other_partner: objections.has("Andere Partner"),
            objection_price: objections.has("Kosten / Preis"),
        };

        if (analysis.followup_requested && analysis.followup_datetime) {
            changes.draft_followup = deserializeDateTime(
                analysis.followup_datetime
            );
        } else {
            changes.draft_followup = false;
        }

        await this.props.record.update(changes);
    }

    getAudioFilename(mimeType) {
        if (mimeType.includes("ogg")) {
            return "voice-note.ogg";
        }

        if (mimeType.includes("mp4")) {
            return "voice-note.m4a";
        }

        return "voice-note.webm";
    }

    clearTemporaryData() {
        this.stopMediaStream();
        this.audioChunks = [];
        this.mediaRecorder = null;
        this.state.recording = false;
        this.state.transcribing = false;
        this.state.analyzing = false;
        this.state.transcript = null;
        this.state.analysis = null;
        this.state.error = null;
    }

    stopMediaStream() {
        if (!this.mediaStream) {
            return;
        }

        for (const track of this.mediaStream.getTracks()) {
            track.stop();
        }

        this.mediaStream = null;
    }
}

registry.category("fields").add("voice_note_recorder", {
    component: VoiceNoteRecorder,
    supportedTypes: ["char"],
});
