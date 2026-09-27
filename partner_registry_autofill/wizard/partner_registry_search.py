from odoo import _, fields, models
from odoo.fields import Command


class PartnerRegistrySearch(models.TransientModel):
    """Fenêtre "Search company by name" : cherche dans le registre et remplit la fiche."""
    _name = "partner.registry.search"
    _description = "Search a company in the registry"

    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    query = fields.Char(string="Company name", required=True)
    searched = fields.Boolean()
    line_ids = fields.One2many("partner.registry.search.line", "wizard_id")

    def action_search(self):
        self.ensure_one()
        results = self.partner_id._registry_search_fr(self.query)
        self.write({
            "searched": True,
            "line_ids": [Command.clear()] + [Command.create(vals) for vals in results],
        })
        # On rouvre la même fenêtre pour afficher les résultats
        return {
            "type": "ir.actions.act_window",
            "name": _("Search company by name"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }


class PartnerRegistrySearchLine(models.TransientModel):
    _name = "partner.registry.search.line"
    _description = "Registry search result"

    wizard_id = fields.Many2one("partner.registry.search", required=True, ondelete="cascade")
    name = fields.Char()
    number = fields.Char(string="SIREN")
    zip = fields.Char()
    city = fields.Char()

    def action_select(self):
        self.ensure_one()
        partner = self.wizard_id.partner_id
        partner.write(partner._registry_fetch_fr(self.number))
        return {"type": "ir.actions.act_window_close"}
