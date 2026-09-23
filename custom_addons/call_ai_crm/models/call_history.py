from odoo import models, fields, api


class CallHistory(models.Model):
    _name = 'call.history'
    _description = 'Anrufhistorie'
    _order = 'call_start desc, id desc'

    # ---------------------------------------------------------
    # GRUNDDATEN DES TELEFONATS
    # ---------------------------------------------------------

    # Jeder Eintrag der Anrufhistorie gehört genau zu einem Kontakt.
    partner_id = fields.Many2one(
        'res.partner',
        string="Kontakt",
        required=True,
        ondelete='cascade'
    )

    # Beginn und Ende werden beim Telefonat automatisch gesetzt.
    call_start = fields.Datetime(
        string="Start",
        required=True
    )

    call_end = fields.Datetime(
        string="Ende"
    )

    # Die Dauer wird bei einem regulär beendeten Telefonat berechnet.
    # Bei einem automatisch abgebrochenen Vorgang bleibt sie unbestimmt.
    duration = fields.Float(
        string="Dauer (Minuten)"
    )

    # Die tatsächlich verwendete Telefonnummer wird als Snapshot gespeichert.
    # Dadurch bleibt sie auch erhalten, wenn sich die Nummer des Kontakts
    # später ändert.
    phone_number = fields.Char(
        string="Telefonnummer"
    )

    # ---------------------------------------------------------
    # MITARBEITER
    # ---------------------------------------------------------

    # Der angemeldete Odoo-Benutzer wird als Mitarbeiter gespeichert.
    # Die Relation bleibt die eigentliche Zuordnung zum Benutzer.
    advisor_id = fields.Many2one(
        'res.users',
        string="Mitarbeiter",
        ondelete='set null'
    )

    # Für die kompakte Darstellung in der Anrufhistorie wird aus dem
    # Namen des Mitarbeiters automatisch ein Kürzel gebildet.
    advisor_initials = fields.Char(
        string="MA",
        compute="_compute_advisor_initials"
    )

    # ---------------------------------------------------------
    # GESPRÄCHSERGEBNIS
    # ---------------------------------------------------------

    # Der Status wird als historischer Snapshot gespeichert.
    # "Undefiniert" wird ausschließlich für automatisch beendete
    # Vorgänge verwendet, bei denen keine Benutzerbestätigung vorliegt.
    # Dieser Wert gehört bewusst nicht zum Leadstatus des Kontakts.
    result_stage = fields.Selection([
        ('new', 'Neu'),
        ('no_interest', 'Kein Interesse'),
        ('interested', 'Interessiert'),
        ('very_interested', 'Sehr interessiert'),
        ('customer', 'Kunde'),
        ('undefined', 'Undefiniert')
    ], string="Ergebnis")

    # ---------------------------------------------------------
    # EINWÄNDE
    # ---------------------------------------------------------

    # Für das MVP werden die vier häufigsten Einwände fest vorgegeben.
    # Mehrere Einwände können gleichzeitig zu einem Gespräch gehören.
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

    # Die strukturierten Boolean-Felder bleiben erhalten.
    # Dieses Feld fasst lediglich die gesetzten Einwände für die
    # kompakte Darstellung in der Anrufhistorie zusammen.
    objections_display = fields.Char(
        string="Einwände",
        compute="_compute_objections_display"
    )

    # ---------------------------------------------------------
    # NACHBEARBEITUNG
    # ---------------------------------------------------------

    # Die Gesprächsnotiz enthält nach der Bestätigung den endgültigen Inhalt.
    # Später kann die KI hierfür einen Vorschlag liefern, den der Benutzer
    # vor dem Speichern prüfen und ändern kann.
    note = fields.Text(
        string="Gesprächsnotiz"
    )

    # Eine Wiedervorlage gehört zu dem Gespräch, aus dem sie entstanden ist.
    # Datetime speichert neben dem Datum auch die gewünschte Uhrzeit.
    followup_date = fields.Datetime(
        string="Wiedervorlage"
    )


    # Anzeigehilfen für die Listenansicht. Die Originalwerte bleiben
    # sekundengenau gespeichert und werden nur für den Benutzer formatiert.
    call_start_display = fields.Char(
        string="Datum",
        compute="_compute_time_display"
    )

    duration_display = fields.Char(
        string="Dauer",
        compute="_compute_time_display"
    )

    followup_date_display = fields.Char(
        string="Wiedervorlage",
        compute="_compute_time_display"
    )

    @api.depends('call_start', 'duration', 'followup_date')
    @api.depends_context('tz')
    def _compute_time_display(self):
        """Formatiert Zeitwerte für die kompakte Anrufhistorie."""
        for rec in self:
            if rec.call_start:
                local_call_start = fields.Datetime.context_timestamp(
                    rec, rec.call_start
                )
                rec.call_start_display = local_call_start.strftime(
                    "%d.%m.%Y %H:%M"
                )
            else:
                rec.call_start_display = False

            total_seconds = max(0, round((rec.duration or 0.0) * 60))
            minutes, seconds = divmod(total_seconds, 60)
            rec.duration_display = f"{minutes}:{seconds:02d} min"

            if rec.followup_date:
                local_followup = fields.Datetime.context_timestamp(
                    rec, rec.followup_date
                )
                rec.followup_date_display = local_followup.strftime(
                    "%d.%m.%Y %H:%M"
                )
            else:
                rec.followup_date_display = False


    # ---------------------------------------------------------
    # ANZEIGEFELDER
    # ---------------------------------------------------------

    @api.depends('advisor_id', 'advisor_id.name')
    def _compute_advisor_initials(self):
        """Bildet ein kurzes Mitarbeiterkürzel aus dem Benutzernamen."""
        for record in self:
            name = record.advisor_id.name or ''

            # Der Name wird in einzelne Bestandteile zerlegt.
            # Aus jedem Bestandteil wird der erste Buchstabe verwendet.
            name_parts = name.split()

            record.advisor_initials = ''.join(
                part[0].upper()
                for part in name_parts
                if part
            )

    @api.depends(
        'objection_no_need',
        'objection_internal',
        'objection_other_partner',
        'objection_price'
    )
    def _compute_objections_display(self):
        """Fasst die gesetzten Einwände für die Listenansicht zusammen."""
        for record in self:
            objections = []

            if record.objection_no_need:
                objections.append('Kein Bedarf')

            if record.objection_internal:
                objections.append('Internes Programm')

            if record.objection_other_partner:
                objections.append('Andere Partner')

            if record.objection_price:
                objections.append('Kosten / Preis')

            record.objections_display = ' · '.join(objections)