from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class Anschrift(BaseModel):
    strasse: str
    plz: str
    ort: str
    land: str = Field(..., min_length=2, max_length=2)


class Dokument(BaseModel):
    rechnungsnummer: str
    rechnungsart: str
    rechnungsdatum: date
    faelligkeitsdatum: Optional[date]
    waehrung: str = "EUR"


class Partei(BaseModel):
    name: str
    umsatzsteuer_id: Optional[str]
    steuernummer: Optional[str]
    anschrift: Anschrift


class UmsatzsteuerPosition(BaseModel):
    kategorie: str
    satz: float


class Rechnungsposition(BaseModel):
    positionsnummer: int
    beschreibung: str
    menge: float
    einheit: str
    einzelpreis_netto: float
    positionsbetrag_netto: float
    umsatzsteuer: UmsatzsteuerPosition


class UmsatzsteuerAufschluesselung(BaseModel):
    kategorie: str
    satz: float
    steuerbasisbetrag: float
    steuerbetrag: float


class Summen(BaseModel):
    gesamt_netto: float
    gesamt_umsatzsteuer: float
    gesamt_brutto: float
    zahlbetrag: float


class Zahlung(BaseModel):
    zahlungsart: str
    iban: Optional[str]
    bic: Optional[str]


class Bemerkung(BaseModel):
    text: str


class Rechnung(BaseModel):
    dokument: Dokument
    verkaeufer: Partei
    kaeufer: Partei
    positionen: List[Rechnungsposition]
    umsatzsteuer_aufschluesselung: Optional[List[UmsatzsteuerAufschluesselung]]
    summen: Summen
    zahlung: Zahlung
    bemerkungen: Optional[List[Bemerkung]]
