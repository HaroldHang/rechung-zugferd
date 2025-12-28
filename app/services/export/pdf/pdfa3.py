import os
import subprocess
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle
from loguru import logger
import pathlib
from pathlib import Path
import pikepdf
from pikepdf import Name, Dictionary, Array
import shutil
from weasyprint import HTML
from jinja2 import FileSystemLoader, Environment
import fitz  # PyMuPDF

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
#from ironpdf import PdfDocument, PdfAVersions
jinja_env = Environment(loader=FileSystemLoader(BASE_DIR / "resources" / "invoice"))
gs_base = os.getenv("GHOSTSCRIPT_PATH", "C:/Program Files/gs/gs10.06.0")
env = os.environ.copy()
env["GS_LIB"] = f"{gs_base}/lib;{gs_base}/Resource/Init;{gs_base}/Resource/Font"
try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional dependency
    fitz = None


def _render_basic_invoice_pdf(rechnung: dict, pdf_path: str, logo_path: Optional[str] = None) -> None:
    """Render a simple invoice layout to a PDF using ReportLab.

    This focuses on clarity and correctness of values; it is not intended to be a
    production design. The goal is to produce a base PDF that we will convert to
    PDF/A-3 and attach the ZUGFeRD XML to.
    """
    c = canvas.Canvas(pdf_path,pagesize=A4,invariant=1)
    width, height = A4

    # Header with seller info and optional logo
    y = height - 25 * mm
    if logo_path and os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, 20 * mm, y - 20 * mm, width=40 * mm, height=20 * mm, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            logger.warning(f"Logo rendering failed: {e}")

    seller = rechnung.get("verkaeufer", {})
    buyer = rechnung.get("kaeufer", {})

    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, seller.get("name", "Verkäufer"))
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y - 6 * mm, seller.get("adresse", ""))
    c.drawString(20 * mm, y - 12 * mm, f"USt-IdNr: {seller.get('ust_id', '')}")

    # Buyer block
    c.setFont("Helvetica-Bold", 12)
    c.drawString(120 * mm, y, buyer.get("name", "Käufer"))
    c.setFont("Helvetica", 10)
    c.drawString(120 * mm, y - 6 * mm, buyer.get("adresse", ""))

    # Invoice info
    y_info = y - 30 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y_info, "Rechnung")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y_info - 6 * mm, f"Rechnungsnummer: {rechnung.get('rechnungsnummer', '')}")
    c.drawString(20 * mm, y_info - 12 * mm, f"Datum: {rechnung.get('datum', datetime.now().date())}")
    c.drawString(20 * mm, y_info - 18 * mm, f"Zahlungsziel: {rechnung.get('zahlungsziel', '')}")

    # Positions table
    data = [["Pos", "Beschreibung", "Menge", "Preis", "MwSt%", "Summe"]]
    for i, pos in enumerate(rechnung.get("positionen", []), start=1):
        data.append([
            str(i),
            pos.get("beschreibung", ""),
            f"{pos.get('menge', 0):.2f}",
            f"{pos.get('preis', 0):.2f}",
            f"{pos.get('mwst', 0):.2f}",
            f"{pos.get('summe', 0):.2f}",
        ])

    table = Table(data, colWidths=[12 * mm, 80 * mm, 18 * mm, 22 * mm, 18 * mm, 22 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    w, h = table.wrapOn(c, width - 40 * mm, height)
    table.drawOn(c, 20 * mm, y_info - 40 * mm - h)

    # Totals
    y_tot = y_info - 50 * mm - h
    summen = rechnung.get("summen", {})
    c.setFont("Helvetica-Bold", 12)
    c.drawString(120 * mm, y_tot, "Summen")
    c.setFont("Helvetica", 10)
    c.drawRightString(200 * mm, y_tot - 6 * mm, f"Zwischensumme: {summen.get('zwischensumme', 0):.2f} {rechnung.get('waehrung', 'EUR')}")
    c.drawRightString(200 * mm, y_tot - 12 * mm, f"MwSt: {summen.get('mwst_summe', 0):.2f} {rechnung.get('waehrung', 'EUR')}")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(200 * mm, y_tot - 20 * mm, f"Gesamt: {summen.get('gesamt', 0):.2f} {rechnung.get('waehrung', 'EUR')}")

    c.showPage()
    c.save()

def _render_basic_with_weasprint(rechnung: dict, output_pdf: str, logo_path: Optional[str] = None):
    """Render a simple invoice layout to a PDF using WeasyPrint.

    This focuses on clarity and correctness of values; it is not intended to be a
    production design. The goal is to produce a base PDF that we will convert to
    PDF/A-3 and attach the ZUGFeRD XML to.
    """

    #html = HTML(string=jinja_env.get_template("invoice.html").render(data))
    #html.write_pdf(output_pdf)
    template = jinja_env.get_template("invoice.html")
    html = template.render(**rechnung)
    HTML(string=html, base_url=".").write_pdf(output_pdf)

def _convert_to_pdfa3_ghostscript(input_pdf: str, output_pdf: str) -> bool:
    """Convert a PDF to PDF/A-3 using Ghostscript if available.

    Returns True on success, False otherwise.
    """
    """
    gs_exe_candidates = [
        "gswin64c",  # Windows 64-bit CLI
        "gswin32c",  # Windows 32-bit CLI
        "gs",        # Unix-like
    ]

    gs_exe = None
    for exe in gs_exe_candidates:
        try:
            subprocess.run([exe, "-v"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            gs_exe = exe
            break
        except Exception:
            continue

    if not gs_exe:
        logger.warning("Ghostscript not found. Skipping PDF/A-3 conversion.")
        return False
    """
    # 1. Absolute paths are safer; ensure they use forward slashes for GS
    input_pdf = os.path.abspath(input_pdf).replace("\\", "/")
    output_pdf = os.path.abspath(output_pdf).replace("\\", "/")
    gs_exe = "gswin64c.exe"
    icc_profile = str(Path(__file__).parent.parent.parent.parent.parent / "resources" / "srgb.icc")
    print(icc_profile)
    if not os.path.exists(icc_profile):
        logger.error(f"ICC profile not found: {icc_profile}") 
        return False
    cmd = [
        gs_exe,
        #"-dNOSAFER",
        "-dPDFA=3",
        "-dBATCH",
        "-dNOPAUSE",
        #f"--permit-file-read={icc_profile}",
        "-sDEVICE=pdfwrite",
        "-dPDFACompatibilityPolicy=1 ",
        "-sProcessColorModel=DeviceRGB",
        "-sColorConversionStrategy=RGB",
        f"-sOutputICCProfile={icc_profile}",
        #"-sColorConversionStrategy=UseDeviceIndependentColor",
        f"-sOutputFile={output_pdf}", 
        "PDFA_def.ps",
        input_pdf,
    ]

    try:
        res = subprocess.run(cmd, check=True)
        #print(res.__dict__)
        """
        if res.returncode != 0:
            logger.error(f"Ghostscript PDF/A-3 conversion failed: {res.stderr.decode(errors='ignore')[:2000]}")
            return False
        print(f"convert {input_pdf} to {output_pdf}")
        return True
        """
        if os.path.exists(output_pdf) and os.path.getsize(output_pdf) > 0:
            print(f"Successfully created: {output_pdf}")
            return True
        else:
            print("Process finished but output file is missing or empty.")
            return False
    except subprocess.CalledProcessError as e:
        print(f"Ghostscript Error: {e.stderr}") # e.stderr contains the log
        
        return False
    except Exception as e:
        logger.error(f"Ghostscript invocation error: {e}")
        return False

"""
def _convert_to_pdfa3_ironpdf(input_pdf: str, output_pdf: str) -> bool:
    Convert a PDF to PDF/A-3 using IronPDF if available.

    Returns True on success, False otherwise.
    
    try:
        doc = PdfDocument.fromFile(input_pdf)
        #doc.ConvertToPdfA(PdfAVersions.PdfA3)
        doc.SaveAsPdfA(output_pdf, PdfAVersions.PdfA3)
        return True
    except Exception as e:
        logger.error(f"IronPDF PDF/A-3 conversion failed: {e}")
        return False
"""

def _embed_xml_with_pymupdf(pdf_path: str, xml_path: str, output_pdf: str) -> bool:
    """Embed XML into a PDF using PyMuPDF.

    Note: This will attach the XML. Creating full PDF/A-3 AF catalog entries is
    implementation-dependent; we rely on PDF/A-3 conversion to preserve /EmbeddedFiles.
    """
    if fitz is None:
        logger.warning("PyMuPDF (pymupdf) not installed; cannot embed XML.")
        return False

    try:
        doc = fitz.open(pdf_path)
        with open(xml_path, "rb") as f:
            xml_bytes = f.read()
        # Name visible in attachment panel
        name = os.path.basename(xml_path)
        doc.embfile_add(name, xml_bytes, desc="ZUGFeRD XML")

        # Best-effort XMP metadata for PDF/A-3
        meta = doc.metadata or {}
        #meta["pdfaid:part"] = "3"
        #meta["pdfaid:conformance"] = "B"
        doc.set_metadata(meta)

        doc.save(output_pdf)
        return True
    except Exception as e:
        logger.error(f"Embedding XML failed: {e}")
        return False

def embed_xml_zugferd(pdf_path: str, xml_path: str, output_pdf: str) -> None:
    #check if pdf_path exist first
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return
    
    try:
        """
        with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
            # Read XML
            with open(xml_path, "rb") as f:
                xml_bytes = f.read()

            # 1. Create EmbeddedFile stream
            embedded_file = pdf.make_stream(
                xml_bytes,
                Type=Name("/EmbeddedFile"),
                Subtype=Name("/application#2Fxml")
            )

            # 2. Create Filespec
            filespec = Dictionary(
                Type=Name("/Filespec"),
                F="zugferd.xml",
                UF="zugferd.xml",
                AFRelationship=Name("/Data"),
                EF=Dictionary(F=embedded_file)
            )

            filespec_ref = pdf.make_indirect(filespec)

            # 3. Add to EmbeddedFiles name tree
            if "/Names" not in pdf.Root:
                pdf.Root.Names = Dictionary()

            if "/EmbeddedFiles" not in pdf.Root.Names:
                pdf.Root.Names.EmbeddedFiles = Dictionary(
                    Names=Array()
                )

            pdf.Root.Names.EmbeddedFiles.Names.extend([
                "zugferd.xml",
                filespec_ref
            ])

            # 4. Associate file with document (PDF/A-3 requirement)
            pdf.Root.AF = Array([filespec_ref])

            pdf.save(output_pdf)
        """
        doc = fitz.open(pdf_path) # open main document
        count = doc.embfile_count()
        print("number of embedded file:", count)     # shows number of embedded files
        
        pathnamedata = xml_path
        print(pathnamedata)

        embedded_doc = fitz.open(pathnamedata) # open document you want to embed
        embedded_data = pathlib.Path(pathnamedata).read_bytes() # get the document byte data as a buffer
        doc.embfile_add(os.path.basename(pathnamedata), embedded_data)
        doc.saveIncr()
        return True
    except Exception as e:
        logger.error(f"Embedding XML with pikepdf failed: {e}")
        return False

def generate_pdf_a3_with_xml(rechnung: dict, zugferd_xml_path: str, pdf_output_path: str, logo_path: Optional[str] = None) -> str:
    """Generate a PDF/A-3 invoice and embed the ZUGFeRD XML.

    Returns the final PDF path.
    """
    os.makedirs(os.path.dirname(pdf_output_path), exist_ok=True)

    base_pdf_path = os.path.join(os.path.dirname(pdf_output_path), "zugferd.pdf")
    pdfa3_tmp_path = os.path.join(os.path.dirname(pdf_output_path), "zugferd_pdfa3.pdf")

    #_render_basic_invoice_pdf(rechnung, base_pdf_path, logo_path)
    _render_basic_with_weasprint(rechnung, base_pdf_path, logo_path)
    print(base_pdf_path, pdfa3_tmp_path)
    # copy file (base_pdf_path) to temporary directory under data/tmp
    tmp_dir = os.path.join(DATA_DIR, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_pdf_path = os.path.join(tmp_dir, os.path.basename(base_pdf_path))
    try:
        shutil.copyfile(base_pdf_path, tmp_pdf_path)
    except Exception as e:
        logger.error(f"Failed to copy PDF to temporary directory: {e}")
        raise
    
    # Convert to PDF/A-3 (best effort)
    converted = _convert_to_pdfa3_ghostscript(tmp_pdf_path, pdfa3_tmp_path)
    
    #pdf_for_embed = pdfa3_tmp_path if converted else base_pdf_path
    pdf_for_embed = pdfa3_tmp_path
    print(pdf_for_embed)
    # Embed XML
    #embedded = _embed_xml_with_pymupdf(pdf_for_embed, zugferd_xml_path, pdf_output_path)
    embedded = embed_xml_zugferd(pdf_for_embed, zugferd_xml_path, pdf_output_path)
    """
    if not embedded:
        # Fallback: copy the PDF (without embedding) to output
        try:
            shutil.copyfile(pdf_for_embed, pdf_output_path)
            logger.warning("Produced PDF without embedded XML. Install PyMuPDF to enable embedding.")
        except Exception as e:
            logger.error(f"Failed to copy PDF fallback: {e}")
            raise

    # Cleanup temp files
    for p in [base_pdf_path, pdfa3_tmp_path]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass
    """

    return pdf_output_path