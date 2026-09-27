from lxml import etree

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerView(TransactionCase):

    def test_autocomplete_widget_removed_from_vat_only(self):
        arch = self.env["res.partner"].get_views([(False, "form")])["views"]["form"]["arch"]
        arch = etree.fromstring(arch)
        for node in arch.xpath("//field[@name='vat']"):
            self.assertNotEqual(node.get("widget"), "field_partner_autocomplete")
        # La recherche par nom de partner_autocomplete reste disponible
        self.assertIn(
            "field_partner_autocomplete",
            [node.get("widget") for node in arch.xpath("//field[@name='name']")],
        )
