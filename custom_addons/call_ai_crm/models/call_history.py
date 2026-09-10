from odoo import models, fields


class CallHistory(models.Model):
    _name = 'call.history'
    _description = 'Call History'
    _order = 'call_start desc, id desc'

    partner_id = fields.Many2one('res.partner', string="Kontakt", required=True)
    call_start = fields.Datetime("Start")
    call_end = fields.Datetime("Ende")
    duration = fields.Float("Dauer (Minuten)")
    