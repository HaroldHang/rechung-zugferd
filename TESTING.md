# Testprotokoll

Dieses Protokoll beschreibt manuelle Tests zur Sicherstellung der End-to-End-Funktionalität.

## Vorbereitung
- Stellen Sie sicher, dass Python-Abhängigkeiten installiert sind (Python 3.11 empfohlen).
- Optional: Installieren Sie Tesseract und Ghostscript für OCR / PDF/A-3.
- Legen Sie eine Beispielrechnung (PDF mit maschinellem Text, sowie eine gescannte Variante) bereit.

## Schritte
1. Starten Sie den Server: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
2. Öffnen Sie `http://localhost:8000/`.
3. Einstellungen setzen:
   - `llm_model_path` auf lokalen GGUF-Pfad.
   - Optional `logo_path` setzen.
4. Firmendaten eingeben und speichern.
5. Datei hochladen und „Verarbeiten“ klicken.
6. Ergebnisse prüfen:
   - `raw_text.txt` enthält sinnvollen Text.
   - `canonical.json` ist vollständig und konsistent (Summen, VAT-Aufschlüsselung).
   - `xrechnung.xml` und `zugferd.xml` existieren und sind strukturell valide.
   - `zugferd.pdf` existiert und öffnet sich in einem PDF-Viewer.

## Validierung (extern)
- XRechnung: Prüfen mit offiziellem Validator (z. B. Bundesportal) – EN 16931 Profil.
- ZUGFeRD: Prüfen mit offiziellem ZUGFeRD Validator 
  - Prüfen, ob XML eingebettet ist (PDF-Anhang sichtbar) und Profil EN16931 erkannt wird.

## Fehlerfälle
- Fehlendes LLM-Modell: Erwartet `FileNotFoundError`.
- OCRmyPDF nicht installiert: Bei gescannten PDFs Warnung, ggf. wenig Text.
- Ungültige Daten (EN 16931 Regeln): Erwartet 400/500 Fehlermeldungen mit Ursache.

## Protokollierung
- Sammeln Sie Log-Ausgaben und ggf. Screenshots.
- Notieren Sie Validationsergebnisse mit Datum und Version.