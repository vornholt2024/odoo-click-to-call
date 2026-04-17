from odoo import models, fields


class CallHistory(models.Model):
    _name = 'call.history'
    _description = 'Call History'

    partner_id = fields.Many2one('res.partner', string="Kontakt")  # 🔥 DAS MUSS DA SEIN
    call_start = fields.Datetime(string="Start")
    call_end = fields.Datetime(string="Ende")
    duration = fields.Float(string="Dauer (Minuten)")

    