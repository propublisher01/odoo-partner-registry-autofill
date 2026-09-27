import re

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

TIMEOUT = 10
VIES_URL = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/BE/vat/%s"
SIRENE_URL = "https://recherche-entreprises.api.gouv.fr/search"

# SIRENE renvoie les adresses en majuscules, parfois avec un type de voie abrégé
FR_STREET_TYPES = {
    "ALL": "Allée", "AV": "Avenue", "BD": "Boulevard", "CHE": "Chemin", "CRS": "Cours",
    "FG": "Faubourg", "IMP": "Impasse", "PAS": "Passage", "PL": "Place", "QUA": "Quai",
    "R": "Rue", "RTE": "Route", "SQ": "Square",
}
FR_SMALL_WORDS = {"à", "au", "aux", "de", "des", "du", "en", "et", "la", "le", "les", "sous", "sur"}


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.onchange("vat")
    def _onchange_vat_registry_autofill(self):
        """Remplit la fiche dès qu'un numéro complet est saisi dans le champ TVA,
        sans avoir besoin d'enregistrer la fiche d'abord."""
        number = self._registry_normalize(self.vat)
        # On ne relance pas l'appel si la fiche a déjà été remplie pour ce numéro
        if not self._registry_is_complete(number) or number.endswith(self.company_registry or "#"):
            return
        try:
            vals = self._registry_fetch(number)
        except UserError as e:
            return {"warning": {"title": _("Company registry"), "message": str(e)}}
        self.update(vals)

    def action_autofill_from_registry(self):
        """Bouton "Update from registry" : met à jour une fiche existante à partir du numéro saisi."""
        self.ensure_one()
        number = self._registry_normalize(self.vat or self.company_registry)
        if not number:
            raise UserError(_("Enter a VAT or company registry number first."))
        self.write(self._registry_fetch(number))

    @api.model
    def _registry_normalize(self, number):
        return re.sub(r"[^0-9A-Z]", "", (number or "").upper())

    @api.model
    def _registry_is_complete(self, number):
        return bool(
            re.fullmatch(r"BE[01]?\d{9}", number)
            or re.fullmatch(r"FR[0-9A-Z]{2}\d{9}", number)
            or re.fullmatch(r"\d{9}|\d{10}|\d{14}", number)
        )

    def _registry_fetch(self, number):
        """Détecte le pays à partir du numéro et interroge le bon registre."""
        if number.startswith("BE"):
            return self._registry_fetch_be(number[2:])
        if number.startswith("FR"):
            return self._registry_fetch_fr(number[-9:])
        if len(number) in (9, 14) and self.country_id.code != "BE":
            # 9 chiffres = SIREN, 14 chiffres = SIRET (dont les 9 premiers sont le SIREN)
            return self._registry_fetch_fr(number[:9])
        if len(number) in (9, 10):
            return self._registry_fetch_be(number)
        raise UserError(_("Unrecognized number: %s", number))

    def _registry_get_json(self, url, params=None):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            raise UserError(_("The registry could not be reached: %s", e)) from e
        return response.json()

    def _registry_fetch_be(self, number):
        # Le numéro d'entreprise belge a 10 chiffres ; les anciens en ont 9 (on ajoute le 0).
        number = number.zfill(10)
        data = self._registry_get_json(VIES_URL % number)
        if not data.get("isValid"):
            raise UserError(_("No active Belgian company found for number %s.", number))

        # VIES renvoie l'adresse en 2 lignes : "Rue 12\n1000 Bruxelles"
        lines = [line.strip() for line in (data.get("address") or "").split("\n") if line.strip()]
        vals = {
            "name": data.get("name"),
            "vat": "BE%s" % number,
            "company_registry": number,
            "country_id": self.env.ref("base.be").id,
            "is_company": True,
        }
        if lines:
            match = re.match(r"(\d{4})\s+(.+)", lines[-1])
            if match:
                vals.update(zip=match.group(1), city=match.group(2))
                lines = lines[:-1]
            vals["street"] = ", ".join(lines)
        return vals

    def _registry_fetch_fr(self, siren):
        data = self._registry_get_json(SIRENE_URL, params={"q": siren, "per_page": 1})
        results = [r for r in data.get("results", []) if r.get("siren") == siren]
        if not results:
            raise UserError(_("No French company found for SIREN %s.", siren))

        company = results[0]
        siege = company.get("siege") or {}
        street = " ".join(
            part for part in (
                siege.get("numero_voie"),
                siege.get("indice_repetition"),
                FR_STREET_TYPES.get(siege.get("type_voie"), siege.get("type_voie")),
                siege.get("libelle_voie"),
            ) if part
        )
        # Clé de TVA française : (12 + 3 * (SIREN mod 97)) mod 97
        vat_key = (12 + 3 * (int(siren) % 97)) % 97
        return {
            # nom_complet ajoute le sigle entre parenthèses : "TOTALENERGIES SE (TOTALENERGIE SE)"
            "name": company.get("nom_raison_sociale") or company.get("nom_complet"),
            "vat": "FR%02d%s" % (vat_key, siren),
            "company_registry": siren,
            "street": self._registry_title_case(street),
            "street2": self._registry_title_case(siege.get("complement_adresse")) or False,
            "zip": siege.get("code_postal"),
            "city": self._registry_title_case(siege.get("libelle_commune")),
            "country_id": self.env.ref("base.fr").id,
            "is_company": True,
        }

    @api.model
    def _registry_title_case(self, text):
        """"RUE DE LA PAIX" -> "Rue de la Paix", "LES SABLES-D'OLONNE" -> "Les Sables-d'Olonne"."""
        if not text:
            return text

        def fix(part, first):
            # "d'olonne" -> "d'Olonne" ; en tête de texte : "L'Hay"
            prefix, body = re.match(r"^((?:[dl]')?)(.*)$", part).groups()
            if not prefix and not first and body in FR_SMALL_WORDS:
                return body
            return (prefix.capitalize() if first else prefix) + body.capitalize()

        words = text.lower().split()
        return " ".join(
            "-".join(fix(part, first=(i == 0 and j == 0)) for j, part in enumerate(word.split("-")))
            for i, word in enumerate(words)
        )
