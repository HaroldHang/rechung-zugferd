from typing import Dict, Any


def check_basic(data: Dict[str, Any]) -> None:
    # Minimal business rules per EN 16931 context
    dokument = data.get("dokument", {})
    """
    if dokument.get("waehrung") != "EUR":
        raise ValueError("Nur Währung EUR wird unterstützt")
    """

    rechnungsart = dokument.get("rechnungsart")
    if rechnungsart not in {"RECHNUNG", "GUTSCHRIFT"}:
        raise ValueError("Ungültige Rechnungsart")

    positionen = data.get("positionen")
    if not positionen or len(positionen) == 0:
        raise ValueError("Mindestens eine Rechnungsposition erforderlich")

    for pos in positionen:
        if float(pos.get("menge", 0)) < 0:
            raise ValueError("Negative Mengen sind unzulässig")
        if float(pos.get("einzelpreis_netto", 0)) < 0:
            raise ValueError("Negative Preise sind unzulässig")
        if float(pos.get("positionsbetrag_netto", 0)) < 0:
            raise ValueError("Negative Positionsbeträge sind unzulässig")