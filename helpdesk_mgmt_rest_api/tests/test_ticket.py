# Copyright 2021 Akretion (https://www.akretion.com).
# @author Pierrick Brun <pierrick.brun@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import pathlib

from werkzeug.datastructures import FileStorage

from odoo.http import request

from odoo.addons.base_rest.controllers.main import _PseudoCollection
from odoo.addons.component.core import WorkContext
from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.addons.datamodel.tests.common import TransactionDatamodelCase


class HelpdeskTicketCommonCase(TransactionComponentCase, TransactionDatamodelCase):
    def setUp(self):
        super().setUp()
        collection = _PseudoCollection("helpdesk.rest.services", self.env)
        self.services_env = WorkContext(
            model_name="rest.service.registration",
            collection=collection,
            request=request,
        )

    def create_attachment(self, params=None):
        attrs = {"params": "{}"}
        if params:
            attrs["params"] = json.dumps(params)
        with open(pathlib.Path(__file__).resolve()) as fp:
            attrs["file"] = FileStorage(fp)
            self.attachment_res = self.attachment_service.dispatch(
                "create", params=attrs
            )
        return self.attachment_res

    def generate_ticket_data(self, partner=None):
        data = {
            "description": "My order is late",
            "name": "order num 4",
            "category": {"id": self.ref("helpdesk_mgmt.helpdesk_category_3")},
        }
        if partner:
            data["partner"] = partner
        return data

    def assert_ticket_ok(self, ticket, with_attachment=True):
        self.assertEqual(len(ticket), 1)
        self.assertEqual(ticket.category_id.name, "Odoo")
        if with_attachment:
            self.assertEqual(ticket.attachment_ids.id, self.attachment_res["id"])


class HelpdeskTicketNoaccountCase(HelpdeskTicketCommonCase):
    def setUp(self):
        super().setUp()
        provider = self.services_env.component(usage="component_context_provider")
        params = provider._get_component_context()
        env = self.services_env.collection.env
        self.services_env.collection.env = env(
            context=dict(
                env.context,
                authenticated_partner_id=params.get("authenticated_partner_id"),
            )
        )
        self.service = self.services_env.component(usage="helpdesk_ticket")
        self.attachment_service = self.services_env.component(usage="attachment")

    def test_create_ticket_noaccount(self):
        data = self.generate_ticket_data(
            partner={
                "email": "customer+testststs@example.org",
                "name": "Customer",
            }
        )
        self.service.dispatch("create", params=data)
        ticket = self.env["helpdesk.ticket"].search(
            [("partner_email", "=", "customer+testststs@example.org")]
        )
        self.assert_ticket_ok(ticket, with_attachment=False)
        self.assertEqual(ticket.partner_id.email, ticket.partner_email)

    def test_create_ticket_noaccount_attachment(self):
        data = self.generate_ticket_data(
            partner={
                "email": "customer+testststs@example.org",
                "name": "Customer",
            }
        )
        res = self.service.dispatch("create", params=data)
        self.assertEqual(len(res["attachments"]), 0)
        self.create_attachment(
            params={"res_model": "helpdesk.ticket", "res_id": res["id"]}
        )
        ticket = self.env["helpdesk.ticket"].search(
            [("partner_email", "=", "customer+testststs@example.org")]
        )
        self.assert_ticket_ok(ticket, with_attachment=True)
        self.assertEqual(ticket.partner_id.email, ticket.partner_email)


class HelpdeskTicketAuthenticatedCase(HelpdeskTicketCommonCase):
    def setUp(self):
        super().setUp()
        env = self.services_env.collection.env
        self.services_env.collection.env = env(
            context=dict(
                env.context,
                authenticated_partner_id=self.env.ref("base.res_partner_1").id,
            )
        )
        self.service = self.services_env.component(usage="helpdesk_ticket")
        self.attachment_service = self.services_env.component(usage="attachment")

    def test_create_ticket_account_attachment(self):
        data = self.generate_ticket_data()
        res = self.service.dispatch("create", params=data)
        self.create_attachment(
            params={"res_model": "helpdesk.ticket", "res_id": res["id"]}
        )
        ticket = self.env["helpdesk.ticket"].search([("id", "=", res["id"])])
        self.assert_ticket_ok(ticket, with_attachment=True)

    def test_ticket_message(self):
        data = self.generate_ticket_data()
        res = self.service.dispatch("create", params=data)
        ticket = self.env["helpdesk.ticket"].search([("id", "=", res["id"])])
        self.assert_ticket_ok(ticket, with_attachment=False)
        message_data = {"body": "Also here is a picture"}
        self.service.dispatch("message_post", ticket.id, params=message_data)
        self.assertEqual(len(ticket.message_ids), 2)  # There is a technical message
        last_message = ticket.message_ids.sorted(key=lambda m: m.create_date)[0]
        self.assertEqual(len(last_message.attachment_ids), 0)
        attachment = self.create_attachment()
        message_data = {
            "body": "Forgot the attachment !",
            "attachments": [{"id": attachment.get("id")}],
        }
        self.service.dispatch("message_post", ticket.id, params=message_data)
        self.assertEqual(len(ticket.message_ids), 3)  # There is a technical message
        last_message = ticket.message_ids.sorted(key=lambda m: m.create_date)[0]
        self.assertEqual(len(last_message.attachment_ids), 1)
