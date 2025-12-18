from pathlib import Path
from typing import Dict, Any
import json
from loguru import logger

from app.services.extraction.raw_text import extract_raw_text_to_file
from app.services.llm.extractor import llm_extract_draft_json
from app.services.llm.normalizer import validate_and_normalize
from app.services.export.xrechnung.ubl_mapper import map_to_ubl
from app.services.export.xrechnung.xrechnung_writer import write_xrechnung_xml
from app.services.export.zugferd.cii_mapper import map_to_cii
from app.services.export.zugferd.zugferd_writer import write_zugferd_xml
from app.services.export.pdf.pdfa3 import generate_pdf_a3_with_xml

from app.domain.rechnung_model import Rechnung


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def process_input_file(input_path: Path, output_root: Path, settings: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Verarbeite Datei: {input_path}")

    # 1) Extract raw text
    work_dir = output_root / "_working"
    ensure_dir(work_dir)
    raw_text_path = extract_raw_text_to_file(input_path=input_path, dest_dir=work_dir)

    # 2) LLM → draft JSON
    llm_model_path = Path(settings.get("llm_model_path", "./models/model.gguf"))
    print(llm_model_path)
    draft_json = llm_extract_draft_json(raw_text_path=raw_text_path, model_path=llm_model_path)

    # 3) Validation & Normalization → canonical Rechnung
    canonical: Rechnung = validate_and_normalize(draft_json)

    rechnungsnummer = canonical.dokument.rechnungsnummer
    out_dir = output_root / rechnungsnummer
    ensure_dir(out_dir)

    canonical_json_path = out_dir / "canonical.json"
    canonical_json_path.write_text(canonical.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")

    # 4) Exports
    # XRechnung
    ubl_invoice = map_to_ubl(canonical)
    xrechnung_path = out_dir / "xrechnung.xml"
    write_xrechnung_xml(ubl_invoice, xrechnung_path)

    # ZUGFeRD
    cii_invoice = map_to_cii(canonical)
    zugferd_xml_path = out_dir / "zugferd.xml"
    write_zugferd_xml(cii_invoice, zugferd_xml_path)

    # PDF/A-3 with embedded ZUGFeRD XML
    logo_path = settings.get("logo_path") or ""
    pdf_path = out_dir / "zugferd.pdf"
    generate_pdf_a3_with_xml(canonical, zugferd_xml_path, pdf_path, logo_path=logo_path)

    return {
        "status": "success",
        "rechnungsnummer": rechnungsnummer,
        "output_directory": str(out_dir.resolve()),
        "files": {
            "raw_text": str(raw_text_path.resolve()),
            "canonical_json": str(canonical_json_path.resolve()),
            "xrechnung_xml": str(xrechnung_path.resolve()),
            "zugferd_xml": str(zugferd_xml_path.resolve()),
            "zugferd_pdf": str(pdf_path.resolve()),
        },
    }