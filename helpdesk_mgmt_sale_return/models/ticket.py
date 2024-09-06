# Copyright 2021 Akretion (https://www.akretion.com).
# @author Pierrick Brun <pierrick.brun@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    return_picking_ids = fields.Many2many(comodel_name="stock.picking")
    return_count = fields.Integer(
        string="Returns", compute="_compute_return_picking_ids"
    )

    @api.depends("return_picking_ids")
    def _compute_return_picking_ids(self):
        for record in self:
            record.return_count = len(record.return_picking_ids)

    def return_sale_lines(self):
        for picking in (
            self.sale_line_ids.mapped("move_ids")
            .mapped("picking_id")
            .filtered(
                lambda p: p.picking_type_id.code == "outgoing" and p.state != "cancel"
            )
        ):
            return_wizard = (
                self.env["stock.return.picking"]
                .with_context(active_id=picking.id, active_model=picking._name)
                .create({})
            )
            return_wizard._onchange_picking_id()
            moves_to_return = (
                self.mapped("sale_line_ids")
                .mapped("move_ids")
                .filtered(lambda m: m.picking_id == picking)
            )
            # remove lines we are not returning (added by onchange_picking_id)
            return_wizard.product_return_moves.filtered(
                lambda m: m.move_id not in moves_to_return
            ).unlink()
            for return_move in return_wizard.product_return_moves:
                for sale_line in self.sale_line_ids:
                    if (
                        return_move.product_id == sale_line.product_id
                        and return_move.move_id in sale_line.move_ids
                        and sale_line.qty < return_move.quantity
                    ):
                        return_move.quantity = sale_line.qty

            res = return_wizard._create_returns()
            self.return_picking_ids |= self.env["stock.picking"].browse(res[0])
        self.stage_id = self.env.ref("helpdesk_mgmt.helpdesk_ticket_stage_awaiting")

    def action_view_returns(self):
        """
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        """
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_picking_tree_all"
        )

        pickings = self.mapped("return_picking_ids")
        if len(pickings) > 1:
            action["domain"] = [("id", "in", pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref("stock.view_picking_form").id, "form")]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = pickings.id
        # Prepare the context.
        picking_id = pickings.filtered(lambda p: p.picking_type_id.code == "outgoing")
        if picking_id:
            picking_id = picking_id[0]
        else:
            picking_id = pickings[0]
        action["context"] = dict(
            self._context,
            default_partner_id=self.partner_id.id,
            default_picking_type_id=picking_id.picking_type_id.id,
            default_origin=self.name,
            default_group_id=picking_id.group_id.id,
        )
        return action


class HelpdeskTicketSaleLine(models.Model):
    _inherit = "helpdesk.ticket.sale.line"

    move_ids = fields.One2many(related="sale_line_id.move_ids", readonly=True)
