# Copyright 2022 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Helpdesk Purchase",
    "summary": """
        Many2many fields on both helpdesk.ticket and purchase.order to related X SO to 1 Ticket
        and X Tickets to 1 SO.""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Akretion",
    "website": "https://github.com/OCA/helpdesk",
    "depends": ["helpdesk_mgmt", "purchase"],
    "data": [
        # Views
        "views/purchase_order.xml",
        "views/helpdesk_ticket.xml",
    ],
    "demo": [],
}