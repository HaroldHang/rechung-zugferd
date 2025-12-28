from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import date
from datetime import datetime

class Anschrift(BaseModel):
    strasse: str
    plz: str
    ort: str
    land: str = Field("DE", min_length=2, max_length=2)


class Dokument(BaseModel):
    rechnungsnummer: str
    rechnungsart: str
    rechnungsdatum: date
    faelligkeitsdatum: Optional[date] = None
    waehrung: Optional[str] = "EUR"

    @validator('rechnungsdatum', pre=True)
    def parse_german_date(cls, v):
        if not v:
            return None
        # Accept DD.MM.YYYY format
        try:
            return datetime.strptime(v, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError(f"Ungültiges Datum: {v}") 


class Partei(BaseModel):
    name: str
    umsatzsteuer_id: Optional[str] = None
    steuernummer: Optional[str] = None
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
    umsatzsteuer: Optional[UmsatzsteuerPosition] = {"kategorie": "", "satz": 0.0}


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
    iban: Optional[str] = None
    bic: Optional[str] = None


class Bemerkung(BaseModel):
    text: str


class Rechnung(BaseModel):
    dokument: Dokument
    verkaeufer: Partei
    kaeufer: Partei
    positionen: List[Rechnungsposition]
    umsatzsteuer_aufschluesselung: Optional[List[UmsatzsteuerAufschluesselung]] = None
    summen: Summen
    zahlung: Zahlung
    bemerkungen: Optional[List[Bemerkung]] = None
