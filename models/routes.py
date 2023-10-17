from odoo import api, fields, models
from odoo.exceptions import UserError

DEFAULT_IDX = 1


class AgreementRoute(models.Model):
    _name = "alfaleads_agreement.agreement_route_ref"
    _description = "Agreement route"

    _inherit = ["alfaleads_utils.base_ref"]

    lines_ids = fields.One2many(
        comodel_name="alfaleads_agreement.agreement_route_line",
        inverse_name="route_ref_id",
    )
    is_default = fields.Boolean(string="Use Route As Default", default=False)


class RouteLine(models.Model):
    _name = "alfaleads_agreement.agreement_route_line"
    _description = "Agreement Route Line"

    idx = fields.Integer(string="Order", default=DEFAULT_IDX)
    route_ref_id = fields.Many2one(
        comodel_name="alfaleads_agreement.agreement_route_ref"
    )
    agreement_id = fields.Many2one(comodel_name="alfaleads_agreement.agreement_process")
    approvers_ids = fields.Many2many(comodel_name="res.users", string="Approvers")

    @api.constrains("idx")
    def _check_idx(self):
        for record in self:
            if record.idx < 1:
                raise UserError("Order cannot be less then 1")
