from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # 🟢 Lead
    is_lead = fields.Boolean(string="B2B Lead")

    lead_status = fields.Selection([
        ('new', 'Neu'),
        ('contacted', 'Kontaktiert'),
        ('interested', 'Interessiert'),
        ('callback', 'Wiedervorlage'),
        ('closed', 'Abgeschlossen')
    ], string="Lead Status", default='new')

    next_call_date = fields.Date(string="Wiedervorlage")

    # 🔥 EINWÄNDE
    objection_no_need = fields.Boolean(string="Kein Bedarf")
    objection_internal = fields.Boolean(string="Internes Programm")
    objection_no_interest = fields.Boolean(string="Kein Interesse")
    objection_other = fields.Boolean(string="Andere Partner")

    # 🔵 CALL
    call_status = fields.Selection([
        ('idle', 'Bereit'),
        ('in_call', 'Im Gespräch'),
    ], string="Call Status", default='idle')

    call_start = fields.Datetime(string="Anruf Start")
    call_end = fields.Datetime(string="Anruf Ende")

    call_duration = fields.Float(
        string="Dauer (Minuten)",
        compute="_compute_duration",
        store=True
    )

    call_history_ids = fields.One2many(
        'call.history',
        'partner_id',
        string="Call History"
    )

    # 🔢 KPIs
    call_count = fields.Integer(
        string="Anrufe gesamt",
        compute="_compute_call_stats",
        store=True
    )

    call_total_duration = fields.Float(
        string="Gesamtdauer (Min)",
        compute="_compute_call_stats",
        store=True
    )

    # ▶️ CALL START
    def action_start_call(self):
        for rec in self:
            rec.call_start = fields.Datetime.now()
            rec.call_status = 'in_call'

    # ⏹️ CALL ENDE
    def action_end_call(self):
        for rec in self:
            rec.call_end = fields.Datetime.now()
            rec.call_status = 'idle'

            if rec.call_start and rec.call_end:
                duration = (rec.call_end - rec.call_start).total_seconds() / 60

                self.env['call.history'].create({
                    'partner_id': rec.id,
                    'call_start': rec.call_start,
                    'call_end': rec.call_end,
                    'duration': duration,
                })

            rec.lead_status = 'contacted'

    # 🔘 EINWÄNDE TOGGLE
    def objection_1(self):
        for rec in self:
            rec.objection_no_need = not rec.objection_no_need

    def objection_2(self):
        for rec in self:
            rec.objection_internal = not rec.objection_internal

    def objection_3(self):
        for rec in self:
            rec.objection_no_interest = not rec.objection_no_interest

    def objection_4(self):
        for rec in self:
            rec.objection_other = not rec.objection_other

    # ⏱️ DAUER
    @api.depends('call_start', 'call_end')
    def _compute_duration(self):
        for rec in self:
            if rec.call_start and rec.call_end:
                rec.call_duration = (rec.call_end - rec.call_start).total_seconds() / 60
            else:
                rec.call_duration = 0

    # 📊 KPIs
    @api.depends('call_history_ids', 'call_history_ids.duration')
    def _compute_call_stats(self):
        for rec in self:
            calls = rec.call_history_ids
            rec.call_count = len(calls)
            rec.call_total_duration = sum(c.duration for c in calls)
