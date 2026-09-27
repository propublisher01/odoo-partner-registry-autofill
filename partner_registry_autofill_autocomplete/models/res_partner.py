from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        # partner_autocomplete ajoute ses suggestions IAP sur les champs name, vat et duns.
        # On les retire du champ TVA : c'est notre onchange qui interroge le registre officiel.
        # Ce module dépend de partner_autocomplete, donc son _get_view est déjà passé ici.
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "form":
            for node in arch.xpath("//field[@name='vat'][@widget='field_partner_autocomplete']"):
                del node.attrib["widget"]
        return arch, view
