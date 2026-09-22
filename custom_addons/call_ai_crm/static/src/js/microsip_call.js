/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Übergibt eine von Odoo vorbereitete SIP-Adresse an Windows.
 *
 * Die eigentliche Telefonie bleibt außerhalb von Odoo. Windows öffnet
 * für das Protokoll "sip:" die registrierte Anwendung, in unserem Fall
 * MicroSIP. Ein Rückkanal von MicroSIP zu Odoo ist nicht vorgesehen.
 *
 * Nach dem Protokollaufruf wird nur die aktuelle Odoo-Ansicht neu geladen.
 * Dadurch werden Gesprächsstatus und Reservierung aktualisiert, ohne die
 * komplette Browserseite neu zu laden und den geöffneten Notebook-Reiter
 * zu verlieren.
 */
async function openMicroSip(env, action) {
    const sipUri = action.params?.sip_uri;

    if (!sipUri || !sipUri.startsWith("sip:")) {
        return;
    }

    window.location.href = sipUri;

    // Der SIP-Aufruf wird zuerst an Windows übergeben. Anschließend lädt
    // Odoo nur die aktuelle Ansicht neu; der geöffnete Notebook-Reiter
    // bleibt dadurch erhalten.
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
    await env.services.action.doAction({
        type: "ir.actions.client",
        tag: "soft_reload",
    });
}

registry.category("actions").add("call_ai_crm_microsip", openMicroSip);
