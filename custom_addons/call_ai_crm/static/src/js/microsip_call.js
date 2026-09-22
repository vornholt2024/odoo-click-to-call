/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Übergibt eine von Odoo vorbereitete SIP-Adresse an Windows.
 *
 * Die eigentliche Telefonie bleibt außerhalb von Odoo. Windows öffnet
 * für das Protokoll "sip:" die registrierte Anwendung, in unserem Fall
 * MicroSIP. Ein Rückkanal von MicroSIP zu Odoo ist nicht vorgesehen.
 *
 * Nach dem Start wird die aktuelle Odoo-Ansicht neu geladen, damit der
 * bereits im Backend gespeicherte Gesprächsstatus und die Reservierung
 * ohne manuelles Aktualisieren sichtbar werden.
 */
function openMicroSip(env, action) {
    const sipUri = action.params?.sip_uri;

    if (!sipUri || !sipUri.startsWith("sip:")) {
        return;
    }

    window.location.href = sipUri;

    // Der Protokollaufruf wird zuerst an Windows übergeben. Eine kurze
    // Verzögerung verhindert, dass der anschließende Reload diesen Aufruf
    // unmittelbar wieder verdrängt.
    window.setTimeout(() => {
        window.location.reload();
    }, 1000);
}

registry.category("actions").add("call_ai_crm_microsip", openMicroSip);
