from pathlib import Path
from typing import Optional
from PIL import Image
import pytesseract
from loguru import logger

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_image_text(input_path: Path) -> str:
    logger.info(f"OCR für Bild: {input_path}")
    with Image.open(str(input_path)) as img:
        img = img.convert("L")  # grayscale
        text = pytesseract.image_to_string(img, lang="deu")
        #print(text)
    return text