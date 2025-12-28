from typing import Dict, Any, List, Tuple
from decimal import Decimal, ROUND_HALF_UP
from loguru import logger

from app.domain.rechnung_model import Rechnung
from app.domain.rechnung.regeln.en_16931 import check_basic


TWOPLACES = Decimal("0.01")


def _round(v: float) -> float:
    return float(Decimal(str(v)).quantize(TWOPLACES, rounding=ROUND_HALF_UP))


def _recalc_positions(draft: Dict[str, Any]) -> None:
    for pos in draft.get("positionen", []):
        menge = float(pos.get("menge", 0))
        einzel = float(pos.get("einzelpreis_netto", 0))
        pos_betrag = _round(menge * einzel)
        pos["positionsbetrag_netto"] = pos_betrag


def _vat_breakdown(draft: Dict[str, Any]) -> List[Dict[str, Any]]:
    buckets: Dict[Tuple[str, float], Dict[str, Any]] = {}
    for pos in draft.get("positionen", []):
        ust = pos.get("umsatzsteuer", {})
        kat = ust.get("kategorie", "S")
        satz = float(ust.get("satz", 0))
        key = (kat, satz)
        bucket = buckets.setdefault(key, {"kategorie": kat, "satz": satz, "steuerbasisbetrag": 0.0, "steuerbetrag": 0.0})
        basis = float(pos.get("positionsbetrag_netto", 0))
        steuer = basis * (satz / 100.0)
        bucket["steuerbasisbetrag"] = _round(bucket["steuerbasisbetrag"] + basis)
        bucket["steuerbetrag"] = _round(bucket["steuerbetrag"] + steuer)
    return list(buckets.values())


def _recalc_summen(draft: Dict[str, Any]) -> Dict[str, Any]:
    gesamt_netto = _round(sum(float(p.get("positionsbetrag_netto", 0)) for p in draft.get("positionen", [])))
    breakdown = _vat_breakdown(draft)
    gesamt_ust = _round(sum(float(b.get("steuerbetrag", 0)) for b in breakdown))
    gesamt_brutto = _round(gesamt_netto + gesamt_ust)
    zahlbetrag = gesamt_brutto
    return {
        "summen": {
            "gesamt_netto": gesamt_netto,
            "gesamt_umsatzsteuer": gesamt_ust,
            "gesamt_brutto": gesamt_brutto,
            "zahlbetrag": zahlbetrag,
        },
        "umsatzsteuer_aufschluesselung": breakdown if breakdown else None,
    }


def validate_and_normalize(draft: Dict[str, Any]) -> Rechnung:
    if not isinstance(draft, dict):
        raise ValueError("Draft JSON muss ein Objekt sein")

    # Recalculate positions and totals deterministically
    _recalc_positions(draft)
    recalced = _recalc_summen(draft)

    # Merge recalculated values back into draft
    draft["summen"] = recalced["summen"]
    if recalced["umsatzsteuer_aufschluesselung"]:
        draft["umsatzsteuer_aufschluesselung"] = recalced["umsatzsteuer_aufschluesselung"]

    # Business rules validation (EN 16931)
    check_basic(draft)

    # Pydantic schema validation to canonical model
    try:
        canonical = Rechnung.model_validate(draft)
    except Exception as e:
        logger.error(f"Validierung fehlgeschlagen: {e}")
        raise
    return canonical