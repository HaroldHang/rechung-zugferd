from pathlib import Path
from typing import Union
from loguru import logger

from app.services.extraction.pdf_extractor import extract_pdf_text
from app.services.extraction.image_ocr import extract_image_text
from app.services.extraction.docx_extractor import extract_docx_text
from app.services.extraction.xlsx_extractor import extract_xlsx_text


SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic"}


def extract_raw_text_to_file(input_path: Union[str, Path], dest_dir: Union[str, Path]) -> Path:
    input_path = Path(input_path)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    suffix = input_path.suffix.lower()
    logger.info(f"Extrahiere Rohtext aus {input_path} ({suffix})")

    if suffix == ".pdf":
        text = extract_pdf_text(input_path)
    elif suffix in SUPPORTED_IMAGE_EXTS:
        text = extract_image_text(input_path)
    elif suffix == ".docx":
        text = extract_docx_text(input_path)
    elif suffix == ".xlsx":
        text = extract_xlsx_text(input_path)
    elif suffix in {".txt", ".csv"}:
        text = input_path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Nicht unterstütztes Format: {suffix}")

    text = sanitize_text(text)
    print(text)
    out_path = dest_dir / "raw_text.txt"
    out_path.write_text(text, encoding="utf-8")
    return out_path


def sanitize_text(text: str) -> str:
    # Normalize whitespace and ensure ASCII fallback if needed
    cleaned = "\n".join(line.strip() for line in text.splitlines())
    return cleaned.strip()