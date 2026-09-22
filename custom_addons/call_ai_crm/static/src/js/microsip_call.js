/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Übergibt eine von Odoo vorbereitete SIP-Adresse an Windows.
 *
 * Die eigentliche Telefonie bleibt außerhalb von Odoo. Windows öffnet
 * für das Protokoll "sip:" die registrierte Anwendung, in unserem Fall
 * MicroSIP. Ein Rückkanal von MicroSIP zu Odoo ist nicht vorgesehen.
 */
function openMicroSip(env, action) {
    const sipUri = action.params?.sip_uri;

    if (!sipUri || !sipUri.startsWith("sip:")) {
        return;
    }

    window.location.href = sipUri;
}

registry.category("actions").add("call_ai_crm_microsip", openMicroSip);
