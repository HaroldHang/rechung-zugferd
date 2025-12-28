from typing import Dict, Any
from app.domain.rechnung_model import Rechnung


def _party(p: Any) -> Dict[str, Any]:
    return {
        "PartyName": p.name,
        "PostalAddress": {
            "StreetName": p.anschrift.strasse,
            "CityName": p.anschrift.ort,
            "PostalZone": p.anschrift.plz,
            "Country": {"IdentificationCode": p.anschrift.land},
        },
        "PartyTaxScheme": {
            "CompanyID": p.steuernummer or p.umsatzsteuer_id or "",
        },
    }


def map_to_ubl(rechnung: Rechnung) -> Dict[str, Any]:
    invoice_type_code = "380" if rechnung.dokument.rechnungsart == "RECHNUNG" else "381"

    # Tax breakdown
    subtotals = []
    for b in (rechnung.umsatzsteuer_aufschluesselung or []):
        subtotals.append({
            "TaxableAmount": b.steuerbasisbetrag,
            "TaxAmount": b.steuerbetrag,
            "TaxCategory": {
                "ID": b.kategorie,
                "Percent": b.satz,
            },
        })

    lines = []
    for pos in rechnung.positionen:
        lines.append({
            "ID": str(pos.positionsnummer),
            "InvoicedQuantity": {"value": pos.menge, "unitCode": pos.einheit},
            "LineExtensionAmount": pos.positionsbetrag_netto,
            "Item": {
                "Description": pos.beschreibung,
                "ClassifiedTaxCategory": {
                    "ID": pos.umsatzsteuer.kategorie,
                    "Percent": pos.umsatzsteuer.satz,
                },
            },
            "Price": {"PriceAmount": pos.einzelpreis_netto},
        })

    return {
        "CustomizationID": "urn:cen.eu:en16931:2017",
        "ProfileID": "urn:fdc:de.gov:xrechnung:3.0.1",
        "ID": rechnung.dokument.rechnungsnummer,
        "IssueDate": rechnung.dokument.rechnungsdatum.isoformat(),
        "InvoiceTypeCode": invoice_type_code,
        "DocumentCurrencyCode": rechnung.dokument.waehrung,
        "AccountingSupplierParty": {"Party": _party(rechnung.verkaeufer)},
        "AccountingCustomerParty": {"Party": _party(rechnung.kaeufer)},
        "TaxTotal": {
            "TaxAmount": rechnung.summen.gesamt_umsatzsteuer,
            "TaxSubtotal": subtotals,
        },
        "LegalMonetaryTotal": {
            "LineExtensionAmount": rechnung.summen.gesamt_netto,
            "TaxExclusiveAmount": rechnung.summen.gesamt_netto,
            "TaxInclusiveAmount": rechnung.summen.gesamt_brutto,
            "PayableAmount": rechnung.summen.zahlbetrag,
        },
        "InvoiceLine": lines,
    }