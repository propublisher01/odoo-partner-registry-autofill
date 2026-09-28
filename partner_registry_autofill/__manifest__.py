{
    "name": "Company Autofill Belgium & France: VAT, VIES, BCE/KBO, SIREN/SIRET (Free)",
    "summary": "Type a VAT, BCE/KBO, SIREN or SIRET number and Odoo fills in the company name and address from official registries (VIES, INSEE SIRENE). Search French companies by name. Free: no IAP credits, no API key.",
    "version": "19.0.1.1.2",
    "category": "Sales/CRM",
    "author": "Marc Frankard",
    "website": "https://www.propublisher.be",
    "support": "support@propublisher.be",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "wizard/partner_registry_search_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
}
