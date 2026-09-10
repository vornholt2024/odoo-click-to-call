from odoo import models, fields, api
from odoo.exceptions import UserError
import re


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ----------------------------
    # LEAD FELDER (WICHTIG!)
    # ----------------------------
    is_lead = fields.Boolean("Lead")

    lead_status = fields.Selection([
        ('new', 'Neu'),
        ('contacted', 'Kontaktiert'),
        ('interested', 'Interessiert'),
        ('callback', 'Rückruf'),
        ('closed', 'Abgeschlossen')
    ], string="Lead Status", default='new')

    next_call_date = fields.Date("Wiedervorlage")

    # ----------------------------
    # EINWÄNDE
    # ----------------------------
    objection_no_need = fields.Boolean("Kein Bedarf")
    objection_internal = fields.Boolean("Intern gelöst")
    objection_no_interest = fields.Boolean("Kein Interesse")
    objection_other = fields.Boolean("Sonstiges")

    # ----------------------------
    # CALL STATUS
    # ----------------------------
    call_status = fields.Selection([
        ('idle', 'Bereit'),
        ('in_call', 'Im Gespräch'),
        ('done', 'Beendet')
    ], string="Call Status", default='idle')

    call_start = fields.Datetime("Anruf Start")
    call_end = fields.Datetime("Anruf Ende")
    call_duration = fields.Float("Dauer (Minuten)", compute="_compute_duration")

    # ----------------------------
    # KPI
    # ----------------------------
    call_count = fields.Integer("Anrufe", compute="_compute_call_stats")
    call_total_duration = fields.Float("Gesamtdauer", compute="_compute_call_stats")

    call_history_ids = fields.One2many(
        'call.history', 'partner_id', string="Call History"
    )

    # ----------------------------
    # FORMATTER
    # ----------------------------
    def _format_phone_number(self, number):
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

    # ----------------------------
    # CALL START
    # ----------------------------
    def action_start_call(self):
        self.ensure_one()

        raw_number = self.phone or self.mobile

        if not raw_number:
            raise UserError("Keine Telefonnummer vorhanden.")

        number = self._format_phone_number(raw_number)

        if not number:
            raise UserError("Telefonnummer ist ungültig.")

        self.call_start = fields.Datetime.now()
        self.call_status = 'in_call'

    # ----------------------------
    # CALL ENDE
    # ----------------------------
    def action_end_call(self):
        for rec in self:
            rec.call_end = fields.Datetime.now()
            rec.call_status = 'done'

            if rec.call_start:
                rec.env['call.history'].create({
                    'partner_id': rec.id,
                    'call_start': rec.call_start,
                    'call_end': rec.call_end,
                    'duration': rec.call_duration
                })

            rec.call_start = False
            rec.call_end = False

    # ----------------------------
    # EINWÄNDE UMSCHALTEN
    # ----------------------------

    def action_toggle_no_need(self):
        """Schaltet den Einwand 'Kein Bedarf' um."""
        self.ensure_one()
        self.objection_no_need = not self.objection_no_need

    def action_toggle_internal(self):
        """Schaltet den Einwand 'Intern gelöst' um."""
        self.ensure_one()
        self.objection_internal = not self.objection_internal

    def action_toggle_no_interest(self):
        """Schaltet den Einwand 'Kein Interesse' um."""
        self.ensure_one()
        self.objection_no_interest = not self.objection_no_interest

    def action_toggle_other(self):
        """Schaltet den Einwand 'Sonstiges' um."""
        self.ensure_one()
        self.objection_other = not self.objection_other

    # ----------------------------
    # COMPUTE
    # ----------------------------
    def _compute_duration(self):
        for rec in self:
            if rec.call_start and rec.call_end:
                delta = rec.call_end - rec.call_start
                rec.call_duration = delta.total_seconds() / 60
            else:
                rec.call_duration = 0

    def _compute_call_stats(self):
        for rec in self:
            rec.call_count = len(rec.call_history_ids)
            rec.call_total_duration = sum(rec.call_history_ids.mapped('duration'))