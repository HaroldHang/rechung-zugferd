from pathlib import Path
from typing import Dict, Any
from lxml import etree

NSMAP = {
    None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}


def _el(tag: str, text: Any = None, ns: str = "cbc"):
    qname = etree.QName(NSMAP[ns], tag)
    el = etree.Element(qname)
    if text is not None:
        el.text = str(text)
    return el


def write_xrechnung_xml(ubl_invoice: Dict[str, Any], out_path: Path) -> None:
    inv = etree.Element(etree.QName(NSMAP[None], "Invoice"), nsmap=NSMAP)

    inv.append(_el("CustomizationID", ubl_invoice["CustomizationID"]))
    inv.append(_el("ProfileID", ubl_invoice["ProfileID"]))
    inv.append(_el("ID", ubl_invoice["ID"]))
    inv.append(_el("IssueDate", ubl_invoice["IssueDate"]))
    inv.append(_el("InvoiceTypeCode", ubl_invoice["InvoiceTypeCode"]))
    inv.append(_el("DocumentCurrencyCode", ubl_invoice["DocumentCurrencyCode"]))

    # Parties
    def party_el(role_key: str):
        role = etree.Element(etree.QName(NSMAP["cac"], role_key))
        party = etree.Element(etree.QName(NSMAP["cac"], "Party"))

        pname = etree.Element(etree.QName(NSMAP["cac"], "PartyName"))
        pname.append(_el("Name", ubl_invoice[role_key]["Party"]["PartyName"]))
        party.append(pname)

        addr = etree.Element(etree.QName(NSMAP["cac"], "PostalAddress"))
        a = ubl_invoice[role_key]["Party"]["PostalAddress"]
        addr.append(_el("StreetName", a["StreetName"]))
        addr.append(_el("CityName", a["CityName"]))
        addr.append(_el("PostalZone", a["PostalZone"]))
        country = etree.Element(etree.QName(NSMAP["cac"], "Country"))
        country.append(_el("IdentificationCode", a["Country"]["IdentificationCode"]))
        addr.append(country)
        party.append(addr)

        role.append(party)
        inv.append(role)

    party_el("AccountingSupplierParty")
    party_el("AccountingCustomerParty")

    # TaxTotal
    tax_total = etree.Element(etree.QName(NSMAP["cac"], "TaxTotal"))
    tax_total.append(_el("TaxAmount", ubl_invoice["TaxTotal"]["TaxAmount"]))
    for st in ubl_invoice["TaxTotal"].get("TaxSubtotal", []):
        tax_sub = etree.Element(etree.QName(NSMAP["cac"], "TaxSubtotal"))
        tax_sub.append(_el("TaxableAmount", st["TaxableAmount"]))
        tax_sub.append(_el("TaxAmount", st["TaxAmount"]))
        tax_cat = etree.Element(etree.QName(NSMAP["cac"], "TaxCategory"))
        tax_cat.append(_el("ID", st["TaxCategory"]["ID"]))
        tax_cat.append(_el("Percent", st["TaxCategory"]["Percent"]))
        tax_sub.append(tax_cat)
        tax_total.append(tax_sub)
    inv.append(tax_total)

    # MonetaryTotal
    mtotal = etree.Element(etree.QName(NSMAP["cac"], "LegalMonetaryTotal"))
    mt = ubl_invoice["LegalMonetaryTotal"]
    mtotal.append(_el("LineExtensionAmount", mt["LineExtensionAmount"]))
    mtotal.append(_el("TaxExclusiveAmount", mt["TaxExclusiveAmount"]))
    mtotal.append(_el("TaxInclusiveAmount", mt["TaxInclusiveAmount"]))
    mtotal.append(_el("PayableAmount", mt["PayableAmount"]))
    inv.append(mtotal)

    # Lines
    for ln in ubl_invoice["InvoiceLine"]:
        line = etree.Element(etree.QName(NSMAP["cac"], "InvoiceLine"))
        line.append(_el("ID", ln["ID"]))
        qty = etree.Element(etree.QName(NSMAP["cbc"], "InvoicedQuantity"), unitCode=str(ln["InvoicedQuantity"]["unitCode"]))
        qty.text = str(ln["InvoicedQuantity"]["value"])
        line.append(qty)
        line.append(_el("LineExtensionAmount", ln["LineExtensionAmount"]))
        item = etree.Element(etree.QName(NSMAP["cac"], "Item"))
        item.append(_el("Description", ln["Item"]["Description"]))
        taxc = etree.Element(etree.QName(NSMAP["cac"], "ClassifiedTaxCategory"))
        taxc.append(_el("ID", ln["Item"]["ClassifiedTaxCategory"]["ID"]))
        taxc.append(_el("Percent", ln["Item"]["ClassifiedTaxCategory"]["Percent"]))
        item.append(taxc)
        line.append(item)
        price = etree.Element(etree.QName(NSMAP["cac"], "Price"))
        price.append(_el("PriceAmount", ln["Price"]["PriceAmount"]))
        line.append(price)
        inv.append(line)

    tree = etree.ElementTree(inv)
    tree.write(str(out_path), encoding="UTF-8", xml_declaration=True, pretty_print=True)