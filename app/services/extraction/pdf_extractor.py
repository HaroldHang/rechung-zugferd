from pathlib import Path
import tempfile
import pdfplumber
from loguru import logger
import subprocess
import shutil


def _pdf_text(input_pdf: Path) -> str:
    text_parts = []
    with pdfplumber.open(str(input_pdf)) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def _needs_ocr(text: str) -> bool:
    # Heuristic: if very few alphanumeric chars, likely scanned
    alnum = sum(c.isalnum() for c in text)
    return alnum < 50


def _run_ocrmypdf(src: Path, dst: Path) -> None:
    cmd = [
        "ocrmypdf",
        "--force-ocr",
        "--rotate-pages",
        "--skip-text",
        str(src),
        str(dst),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        logger.warning(f"OCRmyPDF fehlgeschlagen: {e}")
        raise


def extract_pdf_text(input_path: Path) -> str:
    logger.info(f"Lese PDF: {input_path}")
    text = _pdf_text(input_path)
    if _needs_ocr(text):
        logger.info("Wenig Text erkannt, starte OCR...")
        with tempfile.TemporaryDirectory() as tmpdir:
            ocr_pdf = Path(tmpdir) / "ocr.pdf"
            try:
                _run_ocrmypdf(input_path, ocr_pdf)
                text = _pdf_text(ocr_pdf)
            except Exception:
                logger.warning("OCR fehlgeschlagen, verwende ursprünglichen Text")
    return text