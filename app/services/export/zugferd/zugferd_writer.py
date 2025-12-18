from pathlib import Path
from typing import Dict, Any
from lxml import etree

NSMAP = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}


def _ram(tag: str, text: Any = None):
    el = etree.Element(etree.QName(NSMAP["ram"], tag))
    if text is not None:
        el.text = str(text)
    return el


def write_zugferd_xml(cii: Dict[str, Any], out_path: Path) -> None:
    root = etree.Element(etree.QName(NSMAP["rsm"], "CrossIndustryInvoice"), nsmap=NSMAP)

    # Context
    ctx = etree.Element(etree.QName(NSMAP["rsm"], "ExchangedDocumentContext"))
    param = etree.Element(etree.QName(NSMAP["ram"], "GuidelineSpecifiedDocumentContextParameter"))
    param.append(_ram("ID", cii["Context"]["GuidelineID"]))
    ctx.append(param)
    root.append(ctx)

    # Document
    doc = etree.Element(etree.QName(NSMAP["rsm"], "ExchangedDocument"))
    doc.append(_ram("ID", cii["Document"]["ID"]))
    doc.append(_ram("TypeCode", cii["Document"]["TypeCode"]))
    doc.append(_ram("IssueDateTime", cii["Document"]["IssueDate"]))
    root.append(doc)

    # Parties
    header_agreement = etree.Element(etree.QName(NSMAP["ram"], "ApplicableHeaderTradeAgreement"))
    seller = etree.Element(etree.QName(NSMAP["ram"], "SellerTradeParty"))
    seller.append(_ram("Name", cii["Parties"]["Seller"]["Name"]))
    seller_addr = etree.Element(etree.QName(NSMAP["ram"], "PostalTradeAddress"))
    seller_addr.append(_ram("PostcodeCode", cii["Parties"]["Seller"]["ZIP"]))
    seller_addr.append(_ram("LineOne", cii["Parties"]["Seller"]["Street"]))
    seller_addr.append(_ram("CityName", cii["Parties"]["Seller"]["City"]))
    seller_addr.append(_ram("CountryID", cii["Parties"]["Seller"]["Country"]))
    seller.append(seller_addr)
    header_agreement.append(seller)

    buyer = etree.Element(etree.QName(NSMAP["ram"], "BuyerTradeParty"))
    buyer.append(_ram("Name", cii["Parties"]["Buyer"]["Name"]))
    buyer_addr = etree.Element(etree.QName(NSMAP["ram"], "PostalTradeAddress"))
    buyer_addr.append(_ram("PostcodeCode", cii["Parties"]["Buyer"]["ZIP"]))
    buyer_addr.append(_ram("LineOne", cii["Parties"]["Buyer"]["Street"]))
    buyer_addr.append(_ram("CityName", cii["Parties"]["Buyer"]["City"]))
    buyer_addr.append(_ram("CountryID", cii["Parties"]["Buyer"]["Country"]))
    buyer.append(buyer_addr)
    header_agreement.append(buyer)

    root.append(header_agreement)

    # Settlement (totals)
    settlement = etree.Element(etree.QName(NSMAP["ram"], "ApplicableHeaderTradeSettlement"))
    currency = etree.Element(etree.QName(NSMAP["ram"], "InvoiceCurrencyCode"))
    currency.text = cii["Document"]["Currency"]
    settlement.append(currency)

    # MonetarySummation
    summ = etree.Element(etree.QName(NSMAP["ram"], "SpecifiedTradeSettlementHeaderMonetarySummation"))
    summ.append(_ram("LineTotalAmount", cii["Totals"]["LineNetTotal"]))
    summ.append(_ram("TaxTotalAmount", cii["Totals"]["TaxTotal"]))
    summ.append(_ram("GrandTotalAmount", cii["Totals"]["GrandTotal"]))
    summ.append(_ram("DuePayableAmount", cii["Totals"]["PayableAmount"]))
    settlement.append(summ)

    root.append(settlement)

    # Lines
    trx = etree.Element(etree.QName(NSMAP["ram"], "SupplyChainTradeTransaction"))
    for ln in cii["Lines"]:
        line = etree.Element(etree.QName(NSMAP["ram"], "IncludedSupplyChainTradeLineItem"))
        docline = etree.Element(etree.QName(NSMAP["ram"], "AssociatedDocumentLineDocument"))
        docline.append(_ram("LineID", ln["LineID"]))
        line.append(docline)
        prod = etree.Element(etree.QName(NSMAP["ram"], "SpecifiedTradeProduct"))
        prod.append(_ram("Name", ln["ProductName"]))
        line.append(prod)
        price = etree.Element(etree.QName(NSMAP["ram"], "GrossPriceProductTradePrice"))
        price.append(_ram("ChargeAmount", ln["NetPrice"]))
        line.append(price)
        qty = etree.Element(etree.QName(NSMAP["ram"], "SpecifiedLineTradeDelivery"))
        q = etree.Element(etree.QName(NSMAP["ram"], "BilledQuantity"), unitCode=str(ln["UnitCode"]))
        q.text = str(ln["Quantity"]) 
        qty.append(q)
        line.append(qty)

        # Line settlement / tax
        lsett = etree.Element(etree.QName(NSMAP["ram"], "SpecifiedLineTradeSettlement"))
        tax = etree.Element(etree.QName(NSMAP["ram"], "ApplicableTradeTax"))
        tax.append(_ram("TypeCode", "VAT"))
        tax.append(_ram("CategoryCode", ln["TaxCategory"]))
        tax.append(_ram("RateApplicablePercent", ln["TaxPercent"]))
        lsett.append(tax)
        mon = etree.Element(etree.QName(NSMAP["ram"], "SpecifiedTradeSettlementLineMonetarySummation"))
        mon.append(_ram("LineTotalAmount", ln["NetAmount"]))
        lsett.append(mon)
        line.append(lsett)

        trx.append(line)

    root.append(trx)

    tree = etree.ElementTree(root)
    tree.write(str(out_path), encoding="UTF-8", xml_declaration=True, pretty_print=True)