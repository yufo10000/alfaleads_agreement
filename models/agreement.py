from enum import Enum

from odoo import api, fields, models
from odoo.exceptions import UserError


class AgreementStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    DECLINED = "declined"
    CANCELLED = "canceled"


class AbstractAgreement(models.AbstractModel):
    _name = "alfaleads_agreement.abstract_agreement"
    _description = "Abstract Agreement"

    lines_attribute_name = None
    AGREEMENT_MODEL = ""
    AGREEMENT_VIEW_REF = ""

    agreement_id = fields.Many2one(
        string="Agreement",
        comodel_name="alfaleads_agreement.agreement",
    )
    active_agreement_processes_id = fields.Many2one(
        comodel_name="alfaleads_agreement.agreement_process",
        string="Active agreement processes",
        compute="_compute_active_agreement_processes",
        store=True,
    )
    active_agreement_status = fields.Selection(
        compute="_compute_active_agreement_status",
        related="active_agreement_processes_id.status",
    )
    has_agreement_route = fields.Boolean(
        string="Has agreement steps", compute="_compute_has_agreement_route"
    )

    @api.depends("active_agreement_processes_id")
    def _compute_has_agreement_route(self):
        for rec in self:
            rec.has_agreement_route = False
            if rec.active_agreement_processes_id:
                rec.has_agreement_route = bool(rec.active_agreement_processes_id.route)

    @api.depends("active_agreement_processes_id")
    def _compute_active_agreement_status(self):
        for rec in self:
            rec.has_agreement_in_draft = False
            if rec.active_agreement_processes_id:
                rec.has_agreement_in_draft = rec.active_agreement_processes_id.status

    @api.depends(
        "agreement_id.agreement_processes_ids",
        "agreement_id.agreement_processes_ids.status",
    )
    def _compute_active_agreement_processes(self):
        for rec in self:
            rec.active_agreement_processes_id = False
            agreement = rec.agreement_id.agreement_processes_ids.sorted(
                key=lambda x: x.create_date
            )
            if agreement:
                rec.active_agreement_processes_id = agreement[-1]

    def action_send_to_approve(self):
        self.ensure_one()
        agreement_processes = self.active_agreement_processes_id
        if agreement_processes.filtered(
            lambda x: x.status
            in [AgreementStatus.DRAFT.value, AgreementStatus.IN_PROGRESS.value]
        ):
            raise UserError("Сan be only one active approval process")
        if not self.agreement_id:
            self.agreement = self.env["alfaleads_agreement.agreement"].create(
                {
                    "lines_attribute_name": self.lines_attribute_name,
                    "related_record": "%s,%s" % (self._name, self.id),
                }
            )
        new_agreement_process = self.env[
            "alfaleads_agreement.agreement_process"
        ].create({"agreement_id": self.agreement_id.id})
        if self.active_agreement_processes_id:
            route_ids = [
                route.copy({"approvers_ids": [(6, 0, route.approvers_ids.ids)]}).id
                for route in agreement_processes.route_ids
            ]
            new_agreement_process.route_ids = [(6, 0, route_ids)]

    def action_start_approving(self):
        self.ensure_one()
        if self.active_agreement_status != AgreementStatus.DRAFT.value:
            raise UserError("There are no active approval processes in 'Draft' status")
        self.active_agreement_processes_id.start()

    def action_open_agreement_process(self):
        self.ensure_one()
        if not self.active_agreement_processes_id:
            raise UserError("There are no active approval processes at the moment")
        return {
            "name": "Payment request",
            "view_mode": "form",
            "target": "current",
            "views": [(False, "form")],
            "res_id": self.active_agreement_processes_id.id,
            "res_model": "alfaleads_agreement.agreement_process",
            "type": "ir.actions.act_window",
        }

    def action_open_agreement(self):
        self.ensure_one()
        if not self.active_agreement_processes_id:
            raise UserError("There are no active approval processes at the moment")
        record_agreements = (
            self.active_agreement_processes_id.record_agreements_ids.filtered(
                lambda x: x.task_id.idx
                          == self.active_agreement_processes_id.current_step
                          and x.task_id.approver_id == self.env.user
            )
        )
        if not record_agreements:
            raise UserError("You don't need to confirm")
        # TODO: move widget in budget
        return {
            "type": "ir.actions.act_window",
            "name": "Agreement",
            "view_type": "form",
            "view_mode": "tree,form",
            "domain": [
                ("id", "in", [record.related_record.id for record in record_agreements])
            ],
            "res_model": self.AGREEMENT_MODEL,
            "target": "new",
            "context": {
                "budget_id": self.id,
                "tree_view_ref": self.AGREEMENT_VIEW_REF,
                "agreement_id": self.active_agreement_processes_id.id,
                "create": False,
                "edit": False,
            },
        }

    def _get_task_by_approver(self):
        return self.active_agreement_processes_id.tasks_ids.filtered(
            lambda x: x.idx == self.active_agreement_processes_id.current_step
                      and x.approver_id == self.env.user
            and x.status == "waiting"
        )

    def action_agreement_save(self):
        self.ensure_one()
        if self.active_agreement_status != AgreementStatus.IN_PROGRESS.value:
            raise UserError(
                "There are no active approval processes in 'In Progress' status"
            )
        task = self._get_task_by_approver()
        if not task:
            raise UserError("You don't need to approve")
        task.save()

    def action_agreement_decline(self):
        self.ensure_one()
        if self.active_agreement_status != AgreementStatus.IN_PROGRESS.value:
            raise UserError(
                "There are no active approval processes in 'In Progress' status"
            )
        task = self._get_task_by_approver()
        if not task:
            raise UserError("You don't need to decline")
        task.decline()

    def agreement_cancel(self):
        for rec in self:
            if rec.active_agreement_processes_id:
                rec.active_agreement_processes_id.cancel()

    def set_approve_by_lines(self, lines):
        self.ensure_one()
        if self.active_agreement_status != AgreementStatus.IN_PROGRESS.value:
            raise UserError(
                "There are no active approval processes in 'In Progress' status"
            )
        task = self._get_task_by_approver()
        if not task:
            raise UserError("You don't need to approve")
        task.set_approve_by_lines(lines)

    def set_decline_by_lines(self, lines):
        self.ensure_one()
        if self.active_agreement_status != AgreementStatus.IN_PROGRESS.value:
            raise UserError(
                "There are no active approval processes in 'In Progress' status"
            )
        task = self._get_task_by_approver()
        if not task:
            raise UserError("You don't need to decline")
        task.set_decline_by_lines(lines)


class Agreement(models.Model):
    _name = "alfaleads_agreement.agreement"
    _description = "Agreement"

    related_record = fields.Reference(
        selection="_select_target_model", string="Source Record"
    )
    lines_attribute_name = fields.Char(string="Lines attribute name")
    agreement_processes_ids = fields.One2many(
        comodel_name="alfaleads_agreement.agreement_process",
        inverse_name="agreement_id",
    )

    @api.model
    def _select_target_model(self):
        return [
            (model.model, model.name)
            for model in self.env["ir.model"].sudo().search([])
        ]


class AgreementProcess(models.Model):
    _name = "alfaleads_agreement.agreement_process"
    _description = "Agreement Process"

    agreement_id = fields.Many2one(
        comodel_name="alfaleads_agreement.agreement", ondelete="cascade"
    )
    steps_ids = fields.One2many(
        comodel_name="alfaleads_agreement.agreement_step",
        inverse_name="agreement_process_id",
    )
    tasks_ids = fields.One2many(
        comodel_name="alfaleads_agreement.agreement_task",
        inverse_name="agreement_process_id",
    )
    record_agreements_ids = fields.One2many(
        comodel_name="alfaleads_agreement.record_agreement",
        inverse_name="agreement_process_id",
    )
    status = fields.Selection(
        selection=[
            (AgreementStatus.DRAFT.value, "Draft"),
            (AgreementStatus.IN_PROGRESS.value, "In Progress"),
            (AgreementStatus.APPROVED.value, "Approved"),
            (AgreementStatus.DECLINED.value, "Declined"),
            (AgreementStatus.CANCELLED.value, "Canceled"),
        ],
        string="Agreement status",
        default="draft",
    )
    route_ids = fields.One2many(
        comodel_name="alfaleads_agreement.agreement_route_line",
        inverse_name="agreement_id",
    )

    current_step = fields.Integer(string="Current step", readonly=True, default=0)

    def start(self):
        for record in self:
            record._start()

    def _start(self):
        self.ensure_one()
        if not self.route_ids:
            return
        self.create_next_step()
        self.status = "in_progress"

    def create_next_step(self):
        self.ensure_one()
        if self.status not in ["in_progress", "draft"]:
            return

        step = self.current_step + 1
        route_line = self.route_ids.filtered(lambda r: r.idx == step)
        self.decline_lines()
        if not route_line and step > 1:
            return self.finish()
        if not route_line and step == 1:
            raise ValueError("No data for the first step of approval")
        self.env["alfaleads_agreement.agreement_step"].create(
            [{"idx": step, "agreement_process_id": self.id}], route_line[0]
        )
        self.current_step = step

    def decline_lines(self):
        for record_agreement in self.record_agreements_ids.filtered(
                lambda x: self.current_step == x.task_id.idx and x.status == "declined"
        ):
            record_agreement.related_record.decline()

    def finish(self):
        # TODO: check all steps and tasks has status APPROVED
        amount_approved = {}
        for record_agreement in self.record_agreements_ids.filtered(
                lambda x: self.current_step == x.task_id.idx
        ):
            if record_agreement.status == "approved":
                if record_agreement.related_record not in amount_approved:
                    amount_approved[record_agreement.related_record] = 1
                else:
                    amount_approved[record_agreement.related_record] += 1
        for related_record in amount_approved:
            if amount_approved[related_record] == len(
                self.record_agreements_ids.filtered(
                    lambda x: self.current_step == x.task_id.idx
                    and related_record == x.related_record
                )
            ):
                related_record.approve()
        self.write({"status": AgreementStatus.APPROVED.value})

    def cancel(self):
        self.write({"status": AgreementStatus.CANCELLED.value})

    def decline(self):
        for record_agreement in self.record_agreements_ids:
            record_agreement.related_record.decline()
        self.write({"status": AgreementStatus.DECLINED.value})


class AgreementStep(models.Model):
    _name = "alfaleads_agreement.agreement_step"
    _description = "Agreement Step"
    idx = fields.Integer(string="Order")
    agreement_process_id = fields.Many2one(
        comodel_name="alfaleads_agreement.agreement_process"
    )
    tasks_ids = fields.One2many(
        comodel_name="alfaleads_agreement.agreement_task",
        inverse_name="agreement_step_id",
    )

    def create(self, vals_list, route_line=None):
        records = super().create(vals_list)
        if route_line and route_line.approvers_ids:
            for record in records:
                record._create_tasks(route_line.approvers_ids)
        return records

    def _create_tasks(self, approvers):
        self.ensure_one()
        for approver in approvers:
            self.env["alfaleads_agreement.agreement_task"].create(
                [{"agreement_step_id": self.id, "approver_id": approver.id}]
            )

    def try_move_to_next_step(self):
        for rec in self:
            approved_tasks = rec.tasks_ids.filtered(lambda x: x.status == "approved")
            if len(rec.tasks_ids) == len(approved_tasks):
                rec.agreement_process_id.create_next_step()


class AgreementTask(models.Model):
    _name = "alfaleads_agreement.agreement_task"
    _description = "Agreement Task"

    _inherit = ["mail.thread", "mail.activity.mixin"]

    agreement_step_id = fields.Many2one(
        comodel_name="alfaleads_agreement.agreement_step"
    )
    idx = fields.Integer(related="agreement_step_id.idx")
    agreement_process_id = fields.Many2one(
        related="agreement_step_id.agreement_process_id"
    )
    record_agreements_ids = fields.One2many(
        comodel_name="alfaleads_agreement.record_agreement",
        inverse_name="task_id",
    )
    approver_id = fields.Many2one(comodel_name="res.users", string="Approver")
    status = fields.Selection(
        selection=[
            ("waiting", "Waiting for approval"),
            ("approved", "Approved"),
            ("declined", "Declined"),
        ],
        string="Approving status",
        default="waiting",
    )
    approver_comments = fields.Text(string="Approver Comments")

    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.create_lines_agreement()
        return records

    def create_lines_agreement(self):
        self.ensure_one()
        if (
            self.agreement_process_id.agreement_id.lines_attribute_name
            and self.agreement_process_id.agreement_id.related_record
        ):
            self._create_lines_agreement()

    def _create_lines_agreement(self):
        lines = getattr(
            self.agreement_process_id.agreement_id.related_record,
            self.agreement_process_id.agreement_id.lines_attribute_name,
        )
        self.env["alfaleads_agreement.record_agreement"].create(
            [
                {"task_id": self.id, "related_record": "%s,%s" % (line._name, line.id)}
                for line in lines
            ]
        )
        for line in lines:
            if hasattr(line, "agreement_process_id"):
                line.agreement_process_id = self.agreement_process_id

    def decline(self):
        self.write({"status": "declined"})
        for rec in self:
            rec.agreement_process_id.decline()

    def save(self):
        self.write({"status": "approved"})
        for rec in self:
            record_agreements = rec.record_agreements_ids.filtered(
                lambda x: x.task_id.idx == x.agreement_process_id.current_step
                          and x.task_id.approver_id == self.env.user
            )
            waiting_record_agreements = record_agreements.filtered(
                lambda x: x.status == "waiting"
            )
            if waiting_record_agreements:
                raise UserError("You need to make a decision on all lines")
            declined_record_agreements = record_agreements.filtered(
                lambda x: x.status == "declined"
            )
            if len(record_agreements) == len(declined_record_agreements):
                rec.decline()
            else:
                rec.agreement_step_id.try_move_to_next_step()

    def set_approve_by_lines(self, lines):
        for record in self:
            for record_agreement in record.record_agreements_ids.filtered(
                lambda x: x.task_id.idx == x.agreement_process_id.current_step
                and x.task_id.approver_id == self.env.user
            ):
                if record_agreement.related_record in lines:
                    record_agreement.approve()

    def set_decline_by_lines(self, lines):
        for record in self:
            for record_agreement in record.record_agreements_ids.filtered(
                lambda x: x.task_id.idx == x.agreement_process_id.current_step
                and x.task_id.approver_id == self.env.user
            ):
                if record_agreement.related_record in lines:
                    record_agreement.decline()


class RecordAgreement(models.Model):
    _name = "alfaleads_agreement.record_agreement"
    _description = "Records Agreement"

    task_id = fields.Many2one(comodel_name="alfaleads_agreement.agreement_task")
    related_record = fields.Reference(
        selection="_select_target_model", string="Source Record"
    )
    agreement_process_id = fields.Many2one(related="task_id.agreement_process_id")

    @api.model
    def _select_target_model(self):
        return [
            (model.model, model.name)
            for model in self.env["ir.model"].sudo().search([])
        ]

    status = fields.Selection(
        selection=[
            ("waiting", "Waiting for approval"),
            ("approved", "Approved"),
            ("declined", "Declined"),
        ],
        string="Approving status",
        default="waiting",
    )
    approver_comments = fields.Text(string="Approver Comments")

    def approve(self):
        self.set_status("approved")

    def decline(self):
        self.set_status("declined")

    def set_status(self, status):
        for record in self:
            record.status = status
