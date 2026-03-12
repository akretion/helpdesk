# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # helpesk_mgmt_sale in v15 is a complete different module
    # this migration try to convert to the oca module
    # instead of our implementation

    tickets_with_so = env["helpdesk.ticket"].search([["sale_id", "!=", False]])
    for ticket in tickets_with_so:
        ticket.sale_id.ticket_id = ticket.id
