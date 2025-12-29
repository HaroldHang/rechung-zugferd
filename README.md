# Rechnung Konverter (Offline)

Ein lokales Tool zum Extrahieren, Validieren und Exportieren von Rechnungen in XRechnung und ZUGFeRD (PDF/A-3 mit eingebettetem XML). Keine Cloud, keine Datenübertragung nach außen.

## Features

- FastAPI Backend mit UI (Drag & Drop)
- Rohtext-Extraktion (PDF, Bilder, DOCX, XLSX, TXT)
- LLM-gestützte Datenextraktion (lokales `llama-cpp`)
- Validierung & Normalisierung (EN 16931 Grundregeln)
- Export: XRechnung (UBL) und ZUGFeRD (CII)
- PDF/A-3 Erstellung und XML-Einbettung (ReportLab + Ghostscript)

## Voraussetzungen

- Python 3.11 empfohlen (für stabile Wheels von pydantic / pydantic-core)
  - Bei Python 3.14 kann `pydantic-core` aus Quelltext bauen.
- Ghostscript
  - Erforderlich für die Erstellung von PDF/A-3
  - Installieren Sie Ghostscript lokal. [Download](https://www.ghostscript.com/releases/gsdnld.html)
- Tesseract
  - Erforderlich für die Erstellung von PDF/A-3
  - Installieren Sie Tesseract lokal. [Download](https://tesseract-ocr.github.io/tessdoc/Compiling.html#windows)
- **PATH-Konfiguration**
  - Fügen Sie die Installationspfade von Ghostscript und Tesseract zur Systemumgebungsvariable `PATH` hinzu.


## Installation

```bash
install.exe
```

oder

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Konfiguration

Erstellen Sie eine `.env`-Datei basierend auf der `.env.example` und passen Sie die Werte (z. B. `MODEL_PATH`, `LOGO_PATH`) an:

```bash
cp .env.example .env
GHOSTSCRIPT_PATH="C:/Program Files/gs/gs10.06.0"
TESSERACT_PATH="C:/Program Files/Tesseract-OCR/tesseract.exe"
```



## Start

```bash
start.exe
```

oder

```bash
fastapi dev app/main.py
```

Gehen Sie zu [`http://localhost:8000/`](http://localhost:8000/).

## Nutzung

1. Einstellungen prüfen: Modellpfad (`.gguf`) (z. B. [Qwen2.5-VL-7B-Instruct-Q5_K_M.gguf](https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/Qwen2.5-VL-7B-Instruct-Q5_K_M.gguf?download=true)) und optional Logo-Pfad.
2. Firmendaten erfassen (Anschrift, USt-IdNr., Zahlung).
3. Rechnung hochladen (PDF, Bild, DOCX, XLSX, TXT/CSV).
4. Ergebnisse: Rohtext, `canonical.json`, `xrechnung.xml`, `zugferd.xml`, `zugferd.pdf`.

## Hinweise

- OCR für gescannte PDFs: `ocrmypdf` ruft Tesseract auf. Installieren Sie Tesseract / Ghostscript lokal.
- PDF/A-3: Wir konvertieren über Ghostscript (`-dPDFA=3`). Das Einbetten von XML erfolgt via PyMuPDF.
- Validierungsregeln: Basis gemäß EN 16931, erweiterbar unter `app/domain/rechnung/regeln`.

## Lizenz

Proprietär / Intern. Keine externe Übermittlung der Daten.