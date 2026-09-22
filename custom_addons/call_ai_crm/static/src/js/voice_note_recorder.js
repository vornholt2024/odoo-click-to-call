/** @odoo-module **/

import { Component, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Kleine Voice-Note-Aufnahme für die Nachbearbeitung eines Telefonats.
 *
 * Die Aufnahme bleibt in diesem ersten Entwicklungsschritt vollständig
 * im Browser. Damit kann die Mikrofonaufnahme unabhängig von Whisper
 * und der späteren KI-Anbindung getestet werden.
 */
export class VoiceNoteRecorder extends Component {
    static template = "call_ai_crm.VoiceNoteRecorder";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({
            recording: false,
            audioUrl: null,
            error: null,
        });

        this.mediaRecorder = null;
        this.mediaStream = null;
        this.audioChunks = [];

        onWillUnmount(() => {
            this.stopMediaStream();

            if (this.state.audioUrl) {
                URL.revokeObjectURL(this.state.audioUrl);
            }
        });
    }

    get canRecord() {
        return (
            this.props.record.data.call_status === "post_processing" &&
            this.props.record.data.lock_owned_by_current_user
        );
    }

    async startRecording() {
        if (!this.canRecord || this.state.recording) {
            return;
        }

        this.state.error = null;

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

            this.mediaRecorder.addEventListener("stop", () => {
                const mimeType =
                    this.mediaRecorder.mimeType || "audio/webm";

                const audioBlob = new Blob(this.audioChunks, {
                    type: mimeType,
                });

                if (this.state.audioUrl) {
                    URL.revokeObjectURL(this.state.audioUrl);
                }

                this.state.audioUrl = URL.createObjectURL(audioBlob);
                this.stopMediaStream();
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
