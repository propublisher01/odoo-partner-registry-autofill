# Partner Autofill from Company Registry (BE/FR)

Odoo 19 modules that fill a company contact's legal name and address from official registries,
as soon as a VAT or company number is typed.

| Country | Numbers accepted | Source |
|---|---|---|
| Belgium | Enterprise / VAT number (`BE0403170701`, `0403.170.701`) | [VIES](https://ec.europa.eu/taxation_customs/vies/) (European Commission) |
| France | SIREN, SIRET, VAT number | [SIRENE](https://recherche-entreprises.api.gouv.fr/) (INSEE, api.gouv.fr) |

Free: no IAP credits, no API key.

## Modules

- **partner_registry_autofill**: autofill on the VAT field of contacts, plus an *Update from registry* button on saved companies.
- **partner_registry_autofill_autocomplete**: technical bridge, installed automatically when Odoo's *Partner Autocomplete* is present. It removes the IAP suggestions from the VAT field only; name search keeps working.

## Installation

Add this repository to your addons path, update the apps list and install *Partner Autofill from Company Registry (BE/FR)*.
The Odoo server needs outgoing internet access to reach the registries.

## Translations

English, French, Dutch.

## Support

Marc Frankard, [support@propublisher.be](mailto:support@propublisher.be), [www.propublisher.be](https://www.propublisher.be)

## License

LGPL-3.0, see [LICENSE](LICENSE).
