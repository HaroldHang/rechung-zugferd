from typing import Dict, Any
from app.domain.rechnung_model import Rechnung


def map_to_cii(rechnung: Rechnung) -> Dict[str, Any]:
    inv_type = "380" if rechnung.dokument.rechnungsart == "RECHNUNG" else "381"

    parties = {
        "Seller": {
            "Name": rechnung.verkaeufer.name,
            "Street": rechnung.verkaeufer.anschrift.strasse,
            "City": rechnung.verkaeufer.anschrift.ort,
            "ZIP": rechnung.verkaeufer.anschrift.plz,
            "Country": rechnung.verkaeufer.anschrift.land,
            "TaxID": rechnung.verkaeufer.steuernummer or rechnung.verkaeufer.umsatzsteuer_id or "",
        },
        "Buyer": {
            "Name": rechnung.kaeufer.name,
            "Street": rechnung.kaeufer.anschrift.strasse,
            "City": rechnung.kaeufer.anschrift.ort,
            "ZIP": rechnung.kaeufer.anschrift.plz,
            "Country": rechnung.kaeufer.anschrift.land,
        },
    }

    lines = []
    for pos in rechnung.positionen:
        lines.append({
            "LineID": str(pos.positionsnummer),
            "ProductName": pos.beschreibung,
            "Quantity": pos.menge,
            "UnitCode": pos.einheit,
            "NetAmount": pos.positionsbetrag_netto,
            "NetPrice": pos.einzelpreis_netto,
            "TaxCategory": pos.umsatzsteuer.kategorie,
            "TaxPercent": pos.umsatzsteuer.satz,
        })

    breakdown = []
    for b in (rechnung.umsatzsteuer_aufschluesselung or []):
        breakdown.append({
            "Category": b.kategorie,
            "Percent": b.satz,
            "Basis": b.steuerbasisbetrag,
            "Amount": b.steuerbetrag,
        })

    return {
        "Context": {
            "GuidelineID": "urn:cen.eu:en16931:2017",
            "Profile": "EN16931",
        },
        "Document": {
            "ID": rechnung.dokument.rechnungsnummer,
            "TypeCode": inv_type,
            "IssueDate": rechnung.dokument.rechnungsdatum.isoformat(),
            "Currency": rechnung.dokument.waehrung,
        },
        "Parties": parties,
        "Lines": lines,
        "Totals": {
            "TaxSubtotals": breakdown,
            "TaxTotal": rechnung.summen.gesamt_umsatzsteuer,
            "LineNetTotal": rechnung.summen.gesamt_netto,
            "GrandTotal": rechnung.summen.gesamt_brutto,
            "PayableAmount": rechnung.summen.zahlbetrag,
        },
        "Payment": {
            "Type": rechnung.zahlung.zahlungsart,
            "IBAN": rechnung.zahlung.iban or "",
            "BIC": rechnung.zahlung.bic or "",
        },
    }