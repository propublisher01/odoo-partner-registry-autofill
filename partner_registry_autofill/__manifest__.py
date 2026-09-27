{
    "name": "Partner Autofill from Company Registry (BE/FR)",
    "summary": "Fill a company's name and address from the Belgian (VIES) or French (SIRENE) registry",
    "version": "19.0.1.1.0",
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
