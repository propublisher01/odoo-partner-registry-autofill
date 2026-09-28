from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase, tagged

# On remplace requests.get *dans notre module* : aucun appel réseau pendant les tests
REQUESTS_GET = "odoo.addons.partner_registry_autofill.models.res_partner.requests.get"

VIES_ELECTRABEL = {
    "isValid": True,
    "name": "SA ELECTRABEL",
    "address": "Boulevard Simon Bolivar 36\n1000 Bruxelles",
}
VIES_INVALID = {"isValid": False, "name": "---", "address": "---"}
SIRENE_TOTAL = {
    "results": [{
        "siren": "542051180",
        "nom_complet": "TOTALENERGIES SE (TOTALENERGIE SE)",
        "nom_raison_sociale": "TOTALENERGIES SE",
        "siege": {
            "siret": "54205118000066",
            "numero_voie": "2",
            "type_voie": "PL",
            "libelle_voie": "JEAN MILLIER",
            "complement_adresse": "LA DEFENSE 6",
            "code_postal": "92400",
            "libelle_commune": "COURBEVOIE",
        },
    }],
}


def mock_response(data):
    response = MagicMock()
    response.json.return_value = data
    return response


@tagged("post_install", "-at_install")
class TestRegistryAutofill(TransactionCase):

    def test_onchange_belgian_vat(self):
        with patch(REQUESTS_GET, return_value=mock_response(VIES_ELECTRABEL)) as get:
            form = Form(self.env["res.partner"])
            form.vat = "BE 0403.170.701"
        self.assertIn("0403170701", get.call_args.args[0])
        self.assertEqual(form.name, "SA ELECTRABEL")
        self.assertEqual(form.street, "Boulevard Simon Bolivar 36")
        self.assertEqual(form.zip, "1000")
        self.assertEqual(form.city, "Bruxelles")
        self.assertEqual(form.country_id, self.env.ref("base.be"))
        self.assertEqual(form.vat, "BE0403170701")
        self.assertEqual(form.additional_identifiers["BE_EN"], "0403170701")
        self.assertTrue(form.is_company)

    def test_onchange_french_siret(self):
        with patch(REQUESTS_GET, return_value=mock_response(SIRENE_TOTAL)) as get:
            form = Form(self.env["res.partner"])
            form.vat = "542 051 180 00064"
        # Seul le SIREN (9 premiers chiffres du SIRET) est envoyé à l'API
        self.assertEqual(get.call_args.kwargs["params"]["q"], "542051180")
        self.assertEqual(form.name, "TOTALENERGIES SE")
        # Type de voie développé et casse normale (le nom de société garde ses majuscules)
        self.assertEqual(form.street, "2 Place Jean Millier")
        self.assertEqual(form.street2, "La Defense 6")
        self.assertEqual(form.zip, "92400")
        self.assertEqual(form.city, "Courbevoie")
        self.assertEqual(form.country_id, self.env.ref("base.fr"))
        # Numéro de TVA intracommunautaire calculé à partir du SIREN
        self.assertEqual(form.vat, "FR59542051180")
        self.assertEqual(form.additional_identifiers["FR_SIREN"], "542051180")
        self.assertEqual(form.additional_identifiers["FR_SIRET"], "54205118000066")

    def test_title_case(self):
        title_case = self.env["res.partner"]._registry_title_case
        self.assertEqual(title_case("RUE DE LA PAIX"), "Rue de la Paix")
        self.assertEqual(title_case("BOULOGNE-SUR-MER"), "Boulogne-sur-Mer")
        self.assertEqual(title_case("LES SABLES-D'OLONNE"), "Les Sables-d'Olonne")
        self.assertEqual(title_case("CHEMIN D'ARMOR"), "Chemin d'Armor")
        self.assertEqual(title_case("L'HAY-LES-ROSES"), "L'Hay-les-Roses")

    def test_onchange_unknown_number_returns_warning(self):
        partner = self.env["res.partner"].new({"name": "Draft", "vat": "BE0000000097"})
        with patch(REQUESTS_GET, return_value=mock_response(VIES_INVALID)):
            result = partner._onchange_vat_registry_autofill()
        self.assertIn("warning", result)
        self.assertEqual(partner.name, "Draft")

    def test_onchange_incomplete_number_does_not_call_registry(self):
        with patch(REQUESTS_GET) as get:
            form = Form(self.env["res.partner"])
            form.name = "Draft"
            form.vat = "BE0403"
        get.assert_not_called()

    def test_button_updates_existing_partner(self):
        partner = self.env["res.partner"].create({"name": "Old name", "vat": "BE0403170701"})
        with patch(REQUESTS_GET, return_value=mock_response(VIES_ELECTRABEL)):
            partner.action_autofill_from_registry()
        self.assertEqual(partner.name, "SA ELECTRABEL")
        self.assertEqual(partner.city, "Bruxelles")

    def test_button_registry_unreachable(self):
        partner = self.env["res.partner"].create({"name": "Test", "vat": "BE0403170701"})
        with patch(REQUESTS_GET, side_effect=requests.ConnectionError("timeout")):
            with self.assertRaises(UserError):
                partner.action_autofill_from_registry()
        self.assertEqual(partner.name, "Test")

    def test_button_unrecognized_number(self):
        partner = self.env["res.partner"].create({"name": "Test", "vat": "XX123"})
        with patch(REQUESTS_GET) as get, self.assertRaises(UserError):
            partner.action_autofill_from_registry()
        get.assert_not_called()

    def test_search_by_name_and_select(self):
        partner = self.env["res.partner"].create({"name": "total energies", "is_company": True})
        # 1er appel : recherche par nom, 2e appel : fiche complète de l'entreprise choisie
        with patch(REQUESTS_GET, side_effect=[mock_response(SIRENE_TOTAL), mock_response(SIRENE_TOTAL)]) as get:
            action = partner.action_open_registry_search()
            wizard = self.env["partner.registry.search"].browse(action["res_id"])
            self.assertEqual(get.call_args.kwargs["params"]["q"], "total energies")
            self.assertEqual(get.call_args.kwargs["params"]["etat_administratif"], "A")
            self.assertEqual(wizard.line_ids.mapped("name"), ["TOTALENERGIES SE"])
            self.assertEqual(wizard.line_ids.city, "Courbevoie")
            wizard.line_ids.action_select()
        self.assertEqual(partner.name, "TOTALENERGIES SE")
        self.assertEqual(partner.vat, "FR59542051180")
        self.assertEqual(partner.city, "Courbevoie")

    def test_search_by_name_no_result(self):
        partner = self.env["res.partner"].create({"name": "zzzz", "is_company": True})
        with patch(REQUESTS_GET, return_value=mock_response({"results": []})):
            action = partner.action_open_registry_search()
        wizard = self.env["partner.registry.search"].browse(action["res_id"])
        self.assertTrue(wizard.searched)
        self.assertFalse(wizard.line_ids)
        self.assertEqual(partner.name, "zzzz")
