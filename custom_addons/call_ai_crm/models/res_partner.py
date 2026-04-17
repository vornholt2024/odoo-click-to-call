from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # 🟢 Lead-Logik (Business)
    is_lead = fields.Boolean(string="B2B Lead")

    lead_status = fields.Selection([
        ('new', 'Neu'),
        ('contacted', 'Kontaktiert'),
        ('interested', 'Interessiert'),
        ('callback', 'Wiedervorlage'),
        ('closed', 'Abgeschlossen')
    ], string="Lead Status", default='new')

    next_call_date = fields.Date(string="Wiedervorlage")

    # 🔵 Call-Logik (technisch)
    call_status = fields.Selection([
        ('idle', 'Kein Anruf'),
        ('in_call', 'Im Gespräch'),
        ('called', 'Anruf beendet')
    ], string="Call Status", default='idle')

    call_start = fields.Datetime(string="Anruf Start")
    call_end = fields.Datetime(string="Anruf Ende")

    call_duration = fields.Float(
        string="Dauer (Minuten)",
        compute="_compute_duration",
        store=True
    )

    # 📊 Call History Relation
    call_history_ids = fields.One2many(
        'call.history',
        'partner_id',
        string="Call History"
    )

    # ▶️ Start Call
    def action_start_call(self):
        for rec in self:
            rec.call_start = fields.Datetime.now()
            rec.call_status = 'in_call'

    # ⏹️ End Call
    def action_end_call(self):
        for rec in self:
            rec.call_end = fields.Datetime.now()
            rec.call_status = 'called'

            if rec.call_start and rec.call_end:
                duration = (rec.call_end - rec.call_start).total_seconds() / 60

                self.env['call.history'].create({
                    'partner_id': rec.id,
                    'call_start': rec.call_start,
                    'call_end': rec.call_end,
                    'duration': duration
                })

            # 💥 optional: automatisch Lead aktualisieren
            rec.lead_status = 'contacted'

    # ⏱️ Dauer berechnen
    def _compute_duration(self):
        for rec in self:
            if rec.call_start and rec.call_end:
                delta = rec.call_end - rec.call_start
                rec.call_duration = delta.total_seconds() / 60
            else:
                rec.call_duration = 0