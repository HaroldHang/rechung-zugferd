# Rechnung Konverter (Offline)

Ein lokales Tool zum Extrahieren, Validieren und Exportieren von Rechnungen in XRechnung und ZUGFeRD (PDF/A-3 mit eingebettetem XML). Keine Cloud, keine Datenübertragung nach außen.

## Features
- FastAPI Backend mit UI (Drag & Drop)
- Rohtext-Extraktion (PDF, Bilder, DOCX, XLSX, TXT)
- LLM-gestützte Datenextraktion (lokales `llama-cpp`)
- Validierung & Normalisierung (EN 16931 Grundregeln)
- Export: XRechnung (UBL) und ZUGFeRD (CII)
- PDF/A-3 Erstellung und XML-Einbettung (ReportLab + Ghostscript + PyMuPDF)

## Voraussetzungen
- Python 3.11 empfohlen (für stabile Wheels von pydantic / pydantic-core)
  - Bei Python 3.14 kann `pydantic-core` aus Quelltext bauen und Rust benötigen.
- Optional: Tesseract + Ghostscript (für OCRmyPDF und PDF/A-3)
- Optional: `pymupdf` (PyMuPDF) für das Einbetten von XML in PDF

## Installation
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Falls `pydantic-core` nicht als Wheel verfügbar ist (z. B. auf Python 3.14), verwenden Sie Python 3.11 oder installieren Sie Rust / Maturin.

## Start
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Gehen Sie zu `http://localhost:8000/`.

## Nutzung
1. Einstellungen prüfen: Modellpfad (`.gguf`) und optional Logo-Pfad.
2. Firmendaten erfassen (Anschrift, USt-IdNr., Zahlung).
3. Rechnung hochladen (PDF, Bild, DOCX, XLSX, TXT/CSV).
4. Ergebnisse: Rohtext, `canonical.json`, `xrechnung.xml`, `zugferd.xml`, `zugferd.pdf`.

## Hinweise
- OCR für gescannte PDFs: `ocrmypdf` ruft Tesseract auf. Installieren Sie Tesseract / Ghostscript lokal.
- PDF/A-3: Wir konvertieren über Ghostscript (`-dPDFA=3`). Das Einbetten von XML erfolgt via PyMuPDF.
- Validierungsregeln: Basis gemäß EN 16931, erweiterbar unter `app/domain/rechnung/regeln`.

## Lizenz
Proprietär / Intern. Keine externe Übermittlung der Daten.