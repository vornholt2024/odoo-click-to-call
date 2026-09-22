/** @odoo-module **/

import { Component, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Voice-Note-Aufnahme für die Nachbearbeitung eines Telefonats.
 *
 * Die Aufnahme entsteht im Browser und wird nach dem Stoppen an das
 * Odoo-Backend übertragen. Erst das Backend kommuniziert mit OpenAI,
 * damit der API-Schlüssel niemals an den Browser ausgeliefert wird.
 */
export class VoiceNoteRecorder extends Component {
    static template = "call_ai_crm.VoiceNoteRecorder";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({
            recording: false,
            transcribing: false,
            transcript: null,
            error: null,
        });

        this.mediaRecorder = null;
        this.mediaStream = null;
        this.audioChunks = [];

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
        if (!this.canRecord || this.state.recording || this.state.transcribing) {
            return;
        }

        this.state.error = null;
        this.state.transcript = null;

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
        } catch (error) {
            this.state.error =
                error.message ||
                "Die Voice-Note konnte nicht transkribiert werden.";
        } finally {
            this.state.transcribing = false;
        }
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
