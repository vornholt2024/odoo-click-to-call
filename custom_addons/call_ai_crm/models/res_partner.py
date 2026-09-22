from datetime import timedelta

import re

from odoo import models, fields, api
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ---------------------------------------------------------
    # B2B-AKQUISE / LEAD
    # ---------------------------------------------------------

    # Kennzeichnet, ob der Kontakt für die B2B-Akquise verwendet wird.
    # Wird die Akquise deaktiviert, bleiben vorhandene Daten erhalten.
    is_lead = fields.Boolean(
        string="B2B-Akquise aktiv"
    )

    # Aktueller fachlicher Status des Kontakts.
    # "Kein Interesse" und "Kunde" bilden die beiden Endzustände
    # des Leadprozesses.
    lead_status = fields.Selection([
        ('new', 'Neu'),
        ('no_interest', 'Kein Interesse'),
        ('interested', 'Interessiert'),
        ('very_interested', 'Sehr interessiert'),
        ('customer', 'Kunde')
    ], string="Leadstatus", default='new')

    # Dauerhafte Informationen zum Kontakt, die nicht nur zu einem
    # einzelnen Telefonat gehören.
    contact_notes = fields.Text(
        string="Kurznotizen zum Kontakt"
    )

    # Nächste geplante Wiedervorlage.
    # Datetime wird verwendet, damit Datum und Uhrzeit gespeichert werden.
    next_call_date = fields.Datetime(
        string="Nächste Wiedervorlage"
    )

    # ---------------------------------------------------------
    # STATUS DES AKTUELLEN TELEFONATS
    # ---------------------------------------------------------

    # Der Status bildet den einfachen Ablauf des Telefonats ab:
    # Bereit -> Im Gespräch -> Nachbearbeitung -> Bereit.
    call_status = fields.Selection([
        ('idle', 'Bereit'),
        ('in_call', 'Im Gespräch'),
        ('post_processing', 'Nachbearbeitung')
    ], string="Gesprächsstatus", default='idle')

    call_start = fields.Datetime(
        string="Anruf Start"
    )

    call_end = fields.Datetime(
        string="Anruf Ende"
    )

    call_duration = fields.Float(
        string="Dauer (Minuten)",
        compute="_compute_duration"
    )

    # Verweist während der Nachbearbeitung auf den bereits angelegten
    # Eintrag der Anrufhistorie.
    current_call_history_id = fields.Many2one(
        'call.history',
        string="Aktueller History-Eintrag",
        ondelete='set null'
    )

    # ---------------------------------------------------------
    # SOFT-LOCK / RESERVIERUNG
    # ---------------------------------------------------------

    # Der Kontakt wird beim Start eines Telefonats für den aktuellen
    # Mitarbeiter reserviert. Andere Mitarbeiter können den Kontakt
    # weiterhin ansehen, aber nicht gleichzeitig bearbeiten.
    lock_user_id = fields.Many2one(
        'res.users',
        string="Reserviert von",
        ondelete='set null',
        copy=False
    )

    # Beim Gesprächsstart beträgt die Reservierungszeit 30 Minuten.
    # Laufende Gespräche werden durch den Cronjob jeweils um zehn
    # Minuten verlängert. Nach spätestens 90 Minuten wird ein noch
    # offener Vorgang automatisch als undefiniert abgeschlossen.
    lock_until = fields.Datetime(
        string="Reserviert bis",
        copy=False
    )

    # Diese Felder dienen ausschließlich der Steuerung der Oberfläche.
    # Sie werden nicht zusätzlich in der Datenbank gespeichert.
    lock_active = fields.Boolean(
        string="Reservierung aktiv",
        compute="_compute_lock_state"
    )

    lock_owned_by_current_user = fields.Boolean(
        string="Eigene Reservierung",
        compute="_compute_lock_state"
    )

    lock_owned_by_other_user = fields.Boolean(
        string="Von anderem Mitarbeiter reserviert",
        compute="_compute_lock_state"
    )

    # ---------------------------------------------------------
    # NACHBEARBEITUNG / ENTWURF
    # ---------------------------------------------------------

    # Diese Werte werden zunächst nur als Entwurf gespeichert.
    # Erst durch die Bestätigung werden sie in die Anrufhistorie
    # und gegebenenfalls in den aktuellen Kontakt übernommen.
    draft_result = fields.Selection([
        ('new', 'Neu'),
        ('no_interest', 'Kein Interesse'),
        ('interested', 'Interessiert'),
        ('very_interested', 'Sehr interessiert'),
        ('customer', 'Kunde')
    ], string="Status nach dem Telefonat")

    draft_note = fields.Text(
        string="Gesprächsnotiz"
    )

    draft_followup = fields.Datetime(
        string="Wiedervorlage"
    )

    # Technisches Ankerfeld für das Voice-Note-Widget im Browser.
    # Die Aufnahme selbst wird in diesem ersten Schritt noch nicht in
    # der Datenbank gespeichert, sondern nur lokal im Browser gehalten.
    voice_note_control = fields.Char(
        string="Voice-Note",
        compute="_compute_voice_note_control"
    )

    # ---------------------------------------------------------
    # EINWÄNDE DES AKTUELLEN GESPRÄCHS
    # ---------------------------------------------------------

    objection_no_need = fields.Boolean(
        string="Kein Bedarf"
    )

    objection_internal = fields.Boolean(
        string="Internes Programm"
    )

    objection_other_partner = fields.Boolean(
        string="Andere Partner"
    )

    objection_price = fields.Boolean(
        string="Kosten / Preis"
    )

    # ---------------------------------------------------------
    # ANRUFHISTORIE UND KPI
    # ---------------------------------------------------------

    call_history_ids = fields.One2many(
        'call.history',
        'partner_id',
        string="Anrufhistorie"
    )

    call_count = fields.Integer(
        string="Anrufe gesamt",
        compute="_compute_call_stats"
    )

    call_total_duration = fields.Float(
        string="Gesamtdauer",
        compute="_compute_call_stats"
    )

    call_average_duration = fields.Float(
        string="Ø Gesprächsdauer",
        compute="_compute_call_stats"
    )

    last_call_date = fields.Datetime(
        string="Letzter Anruf",
        compute="_compute_call_stats"
    )

    # ---------------------------------------------------------
    # TELEFONNUMMER AUFBEREITEN
    # ---------------------------------------------------------

    def _format_phone_number(self, number):
        """Bereitet eine Telefonnummer für die spätere Telefonie auf."""
        if not number:
            return False

        number = re.sub(r"[^\d+]", "", number)

        if number.startswith("+49"):
            number = "0049" + number[3:]

        elif number.startswith("0"):
            number = "0049" + number[1:]

        if not number.startswith("00"):
            return False

        return number

    # ---------------------------------------------------------
    # SOFT-LOCK / RESERVIERUNG
    # ---------------------------------------------------------

    @api.depends('lock_user_id', 'lock_until')
    @api.depends_context('uid')
    def _compute_lock_state(self):
        """Bestimmt den aktuellen Zustand der Kontaktreservierung."""
        now = fields.Datetime.now()

        for rec in self:
            active = bool(
                rec.lock_user_id
                and rec.lock_until
                and rec.lock_until > now
            )

            rec.lock_active = active

            rec.lock_owned_by_current_user = bool(
                active
                and rec.lock_user_id.id == self.env.user.id
            )

            rec.lock_owned_by_other_user = bool(
                active
                and rec.lock_user_id.id != self.env.user.id
            )

    def _check_call_lock(self):
        """Verhindert den Start bei einer fremden Reservierung."""
        self.ensure_one()

        now = fields.Datetime.now()

        if (
            self.lock_user_id
            and self.lock_until
            and self.lock_until > now
            and self.lock_user_id != self.env.user
        ):
            local_lock_until = fields.Datetime.context_timestamp(
                self,
                self.lock_until
            )

            raise UserError(
                "Der Kontakt wird bereits von "
                f"{self.lock_user_id.name} bearbeitet.\n"
                "Reserviert bis: "
                f"{local_lock_until.strftime('%d.%m.%Y %H:%M')}"
            )

    def _check_call_owner(self):
        """
        Prüft den Eigentümer eines laufenden Arbeitsvorgangs.

        Für diese Prüfung ist bewusst nicht entscheidend, ob lock_until
        bereits erreicht wurde. Ein langes Telefonat darf nicht dazu
        führen, dass der ursprüngliche Mitarbeiter sein eigenes Gespräch
        nicht mehr beenden kann.
        """
        self.ensure_one()

        if not self.lock_user_id:
            raise UserError(
                "Für dieses Telefonat besteht keine Benutzerzuordnung."
            )

        if self.lock_user_id != self.env.user:
            raise UserError(
                "Dieses Telefonat wird von "
                f"{self.lock_user_id.name} bearbeitet."
            )

    def _reserve_call_contact(self):
        """Reserviert den Kontakt beim Gesprächsstart für 30 Minuten."""
        self.ensure_one()

        now = fields.Datetime.now()

        self.write({
            'lock_user_id': self.env.user.id,
            'lock_until': now + timedelta(minutes=30),
        })

    def _set_post_processing_lock(self):
        """Setzt ab Gesprächsende zehn Minuten für die Nachbearbeitung."""
        self.ensure_one()

        end_time = self.call_end or fields.Datetime.now()

        self.write({
            'lock_until': end_time + timedelta(minutes=10),
        })

    def _release_call_lock(self):
        """Hebt die Reservierung vollständig auf."""
        self.ensure_one()

        self.write({
            'lock_user_id': False,
            'lock_until': False,
        })

    def _create_undefined_call_history(self):
        """
        Speichert einen automatisch abgebrochenen Vorgang minimal.

        Es werden nur Daten übernommen, die bereits unabhängig von einer
        fachlichen Benutzerbestätigung feststehen. Unbestätigte Einwände,
        Notizen, Wiedervorlagen und eine vermeintliche Gesprächsdauer
        werden bewusst nicht gespeichert.
        """
        self.ensure_one()

        raw_number = self.phone or self.mobile
        phone_number = self._format_phone_number(raw_number)

        return self.env['call.history'].create({
            'partner_id': self.id,
            'call_start': self.call_start,
            'phone_number': phone_number or raw_number,
            'advisor_id': self.lock_user_id.id,
            'result_stage': 'undefined',
        })

    @api.model
    def _cron_process_expired_call_locks(self):
        """
        Verarbeitet abgelaufene Reservierungen.

        Laufende Gespräche werden bis zu einer Gesamtdauer von 90 Minuten
        jeweils um zehn Minuten verlängert. Danach wird der Vorgang ohne
        unbestätigte Gesprächsinhalte als undefiniert protokolliert.

        Abgelaufene Nachbearbeitungen werden beendet. Übrig gebliebene
        Reservierungen ohne aktiven Vorgang werden ebenfalls entfernt.
        """
        now = fields.Datetime.now()

        partners = self.search([
            ('lock_user_id', '!=', False),
            ('lock_until', '!=', False),
            ('lock_until', '<=', now),
        ])

        for partner in partners:

            if partner.call_status == 'in_call':

                # Ohne Startzeit kann keine verlässliche Laufzeit bestimmt
                # werden. Der verwaiste Zustand wird deshalb freigegeben,
                # ohne eine Gesprächsdauer oder History zu erfinden.
                if not partner.call_start:
                    partner._clear_call_draft()

                    partner.write({
                        'call_status': 'idle',
                        'call_start': False,
                        'call_end': False,
                        'current_call_history_id': False,
                        'lock_user_id': False,
                        'lock_until': False,
                    })

                    continue

                maximum_call_time = (
                    partner.call_start + timedelta(minutes=90)
                )

                if now >= maximum_call_time:
                    # Die 90 Minuten sind ausschließlich eine technische
                    # Sicherheitsgrenze. Sie werden nicht als tatsächliche
                    # Gesprächsdauer gespeichert.
                    partner._create_undefined_call_history()

                    # Unbestätigte Daten des Benutzers oder spätere
                    # KI-Vorschläge dürfen nicht in die History gelangen.
                    partner._clear_call_draft()

                    partner.write({
                        'call_status': 'idle',
                        'call_start': False,
                        'call_end': False,
                        'current_call_history_id': False,
                        'lock_user_id': False,
                        'lock_until': False,
                    })

                else:
                    # Das Telefonat liegt noch innerhalb der zulässigen
                    # Sicherheitszeit. Der Lock wird um höchstens zehn Minuten
                    # verlängert, jedoch niemals über die Sicherheitsgrenze
                    # von 90 Minuten hinaus.
                    next_lock_until = min(
                        now + timedelta(minutes=10),
                        maximum_call_time
                    )

                    partner.write({
                        'lock_until': next_lock_until,
                    })

            elif partner.call_status == 'post_processing':
                # Die Nachbearbeitungszeit ist abgelaufen.
                # Der beim manuellen Gesprächsende erzeugte History-Eintrag
                # bleibt erhalten; unbestätigte Entwurfsdaten verfallen.
                partner._clear_call_draft()

                partner.write({
                    'call_status': 'idle',
                    'call_start': False,
                    'call_end': False,
                    'current_call_history_id': False,
                    'lock_user_id': False,
                    'lock_until': False,
                })

            else:
                # Es läuft weder ein Telefonat noch eine Nachbearbeitung.
                partner.write({
                    'lock_user_id': False,
                    'lock_until': False,
                })

        return True

    # ---------------------------------------------------------
    # TELEFONAT STARTEN
    # ---------------------------------------------------------

    def action_start_call(self):
        """Startet die Erfassung eines neuen Telefonats."""
        self.ensure_one()

        # Ein neues Akquisegespräch darf nur gestartet werden,
        # wenn der Kontakt ausdrücklich für die B2B-Akquise aktiviert ist.
        # Vorhandene Historien und Kontaktdaten bleiben davon unberührt.
        if not self.is_lead:
            raise UserError(
                "Die B2B-Akquise ist für diesen Kontakt nicht aktiviert."
            )

        if self.call_status != 'idle':
            raise UserError(
                "Das aktuelle Gespräch muss zuerst abgeschlossen werden."
            )

        self._check_call_lock()

        raw_number = self.phone or self.mobile

        if not raw_number:
            raise UserError("Keine Telefonnummer vorhanden.")

        number = self._format_phone_number(raw_number)

        if not number:
            raise UserError("Telefonnummer ist ungültig.")

        self._reserve_call_contact()

        self._clear_call_draft()

        self.write({
            'call_start': fields.Datetime.now(),
            'call_end': False,
            'call_status': 'in_call',
        })

        # MicroSIP läuft auf dem Windows-Arbeitsplatz und wird deshalb
        # nicht aus dem Python-Backend gestartet. Die Client-Action wird
        # im Browser ausgeführt und übergibt die SIP-Adresse an Windows.
        sip_number = number

        if sip_number.startswith("0049"):
            sip_number = "+49" + sip_number[4:]

        return {
            'type': 'ir.actions.client',
            'tag': 'call_ai_crm_microsip',
            'params': {
                'sip_uri': f"sip:{sip_number}",
            },
        }

    # ---------------------------------------------------------
    # TELEFONAT BEENDEN
    # ---------------------------------------------------------

    def action_end_call(self):
        """Beendet das Telefonat und startet die Nachbearbeitung."""
        self.ensure_one()

        if self.call_status != 'in_call':
            raise UserError("Es läuft aktuell kein Telefonat.")

        self._check_call_owner()

        if not self.call_start:
            raise UserError(
                "Für das Telefonat ist keine Startzeit vorhanden."
            )

        call_end = fields.Datetime.now()
        delta = call_end - self.call_start
        duration = delta.total_seconds() / 60

        raw_number = self.phone or self.mobile
        phone_number = self._format_phone_number(raw_number)

        # Bei einem regulären Gesprächsende sind Start, Ende und Dauer
        # tatsächlich durch die Benutzeraktion bestimmt.
        history = self.env['call.history'].create({
            'partner_id': self.id,
            'call_start': self.call_start,
            'call_end': call_end,
            'duration': duration,
            'phone_number': phone_number or raw_number,
            'advisor_id': self.env.user.id,
        })

        self.write({
            'call_end': call_end,
            'current_call_history_id': history.id,
            'call_status': 'post_processing',
            'draft_result': self.lead_status,
            'lock_until': call_end + timedelta(minutes=10),
        })

        return True

    # ---------------------------------------------------------
    # EINWÄNDE UMSCHALTEN
    # ---------------------------------------------------------

    def action_toggle_no_need(self):
        """Schaltet den Einwand 'Kein Bedarf' um."""
        self.ensure_one()
        self._check_call_owner()

        if self.call_status != 'post_processing':
            raise UserError(
                "Einwände können nur in der Nachbearbeitung geändert werden."
            )

        self.objection_no_need = not self.objection_no_need

    def action_toggle_internal(self):
        """Schaltet den Einwand 'Internes Programm' um."""
        self.ensure_one()
        self._check_call_owner()

        if self.call_status != 'post_processing':
            raise UserError(
                "Einwände können nur in der Nachbearbeitung geändert werden."
            )

        self.objection_internal = not self.objection_internal

    def action_toggle_other_partner(self):
        """Schaltet den Einwand 'Andere Partner' um."""
        self.ensure_one()
        self._check_call_owner()

        if self.call_status != 'post_processing':
            raise UserError(
                "Einwände können nur in der Nachbearbeitung geändert werden."
            )

        self.objection_other_partner = not self.objection_other_partner

    def action_toggle_price(self):
        """Schaltet den Einwand 'Kosten / Preis' um."""
        self.ensure_one()
        self._check_call_owner()

        if self.call_status != 'post_processing':
            raise UserError(
                "Einwände können nur in der Nachbearbeitung geändert werden."
            )

        self.objection_price = not self.objection_price

    # ---------------------------------------------------------
    # NACHBEARBEITUNG SPEICHERN
    # ---------------------------------------------------------

    def action_save_call_processing(self):
        """Übernimmt die bestätigten Gesprächsdaten."""
        self.ensure_one()

        if self.call_status != 'post_processing':
            raise UserError(
                "Es befindet sich kein Telefonat in der Nachbearbeitung."
            )

        self._check_call_owner()

        history = self.current_call_history_id

        if not history:
            raise UserError(
                "Der zugehörige Eintrag der Anrufhistorie "
                "wurde nicht gefunden."
            )

        history.write({
            'result_stage': self.draft_result,
            'objection_no_need': self.objection_no_need,
            'objection_internal': self.objection_internal,
            'objection_other_partner': self.objection_other_partner,
            'objection_price': self.objection_price,
            'note': self.draft_note,
            'followup_date': self.draft_followup,
        })

        if self.draft_result:
            self.lead_status = self.draft_result

        # Eine bereits bestehende Wiedervorlage wird nicht gelöscht,
        # nur weil beim aktuellen Gespräch kein neuer Termin eingetragen wurde.
        # Ein neuer Termin ersetzt die bisherige Wiedervorlage.
        if self.draft_followup:
            self.next_call_date = self.draft_followup

        self._finish_call_processing()

        return True

    # ---------------------------------------------------------
    # NACHBEARBEITUNG VERWERFEN
    # ---------------------------------------------------------

    def action_discard_call_processing(self):
        """Verwirft nur die unbestätigte Nachbearbeitung."""
        self.ensure_one()

        if self.call_status != 'post_processing':
            raise UserError(
                "Es befindet sich kein Telefonat in der Nachbearbeitung."
            )

        self._check_call_owner()

        # Der regulär erzeugte History-Eintrag bleibt bestehen.
        self._finish_call_processing()

        return True

    # ---------------------------------------------------------
    # HILFSMETHODEN FÜR DIE NACHBEARBEITUNG
    # ---------------------------------------------------------

    def _clear_call_draft(self):
        """Entfernt die Entwurfsdaten des aktuellen Gesprächs."""
        self.write({
            'draft_result': False,
            'draft_note': False,
            'draft_followup': False,
            'objection_no_need': False,
            'objection_internal': False,
            'objection_other_partner': False,
            'objection_price': False,
        })

    def _finish_call_processing(self):
        """Setzt den Kontakt nach der Nachbearbeitung wieder auf Bereit."""
        self.ensure_one()

        self._clear_call_draft()

        self.write({
            'call_status': 'idle',
            'call_start': False,
            'call_end': False,
            'current_call_history_id': False,
            'lock_user_id': False,
            'lock_until': False,
        })

    # ---------------------------------------------------------
    # BERECHNUNGEN
    # ---------------------------------------------------------

    def _compute_voice_note_control(self):
        """Stellt das technische Ankerfeld für das Browser-Widget bereit."""
        for rec in self:
            rec.voice_note_control = ''

    @api.depends('call_start', 'call_end')
    def _compute_duration(self):
        """Berechnet die Dauer des aktuell bearbeiteten Telefonats."""
        for rec in self:
            if rec.call_start and rec.call_end:
                delta = rec.call_end - rec.call_start
                rec.call_duration = delta.total_seconds() / 60
            else:
                rec.call_duration = 0

    @api.depends(
        'call_history_ids',
        'call_history_ids.duration',
        'call_history_ids.call_start',
        'call_history_ids.result_stage'
    )
    def _compute_call_stats(self):
        """Berechnet die Kennzahlen aus der vorhandenen Anrufhistorie."""
        for rec in self:
            history = rec.call_history_ids

            # Auch ein automatisch als undefiniert protokollierter
            # Anruf gehört zur Anzahl der gestarteten Anrufe.
            rec.call_count = len(history)

            # Undefinierte Vorgänge besitzen keine bestätigte Dauer.
            # Sie dürfen Gesamt- und Durchschnittsdauer daher nicht
            # verfälschen.
            timed_history = history.filtered(
                lambda call: call.result_stage != 'undefined'
            )

            rec.call_total_duration = sum(
                timed_history.mapped('duration')
            )

            if timed_history:
                rec.call_average_duration = (
                    rec.call_total_duration / len(timed_history)
                )
            else:
                rec.call_average_duration = 0

            call_dates = history.mapped('call_start')

            rec.last_call_date = (
                max(call_dates)
                if call_dates
                else False
            )