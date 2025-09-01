from __future__ import annotations
from typing import List, Dict, Any
import uuid, mimetypes, io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from bs4 import BeautifulSoup
import pdfplumber
from docx import Document
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes

from .models import (
    Block, SegmentResult, Product, MapResult,
    Template, ExtractResult, GenerateCatalogRequest
)
from .heuristics import split_blocks, parse_block_to_product
from .render import render_html

app = FastAPI(title="Catalog POC", version="0.1.0")

# In-memory stores (for POC only)
FILES: Dict[str, bytes] = {}
EXTRACTS: Dict[str, ExtractResult] = {}
TEMPLATES: Dict[str, Template] = {}
GENERATED: Dict[str, str] = {}

@app.get("/health")
def health():
    return {"ok": True}

# ---------- Extraction ----------
def extract_text(file_bytes: bytes, filename: str, ocr: bool=False, ocr_lang: str="eng") -> str:
    name = (filename or "").lower()
    mime, _ = mimetypes.guess_type(name)

    # DOCX
    if name.endswith(".docx"):
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])

    # HTML
    if name.endswith(".html") or (mime and mime=="text/html"):
        soup = BeautifulSoup(file_bytes, "html.parser")
        return soup.get_text("\n", strip=True)

    # PDF
    if name.endswith(".pdf") or (mime and mime=="application/pdf"):
        if not ocr:
            # Try text extraction
            txt_parts = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    txt_parts.append(page.extract_text() or "")
            txt = "\n".join(txt_parts)
            if txt.strip():
                return txt
        # Fallback: OCR scanned PDFs
        pages = convert_from_bytes(file_bytes, dpi=300)
        txt = []
        for img in pages:
            txt.append(pytesseract.image_to_string(img.convert("RGB"), lang=ocr_lang))
        return "\n".join(txt)

    # Images (OCR)
    if (mime and mime.startswith("image")) or name.endswith((".png",".jpg",".jpeg",".tif",".tiff",".bmp")):
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        return pytesseract.image_to_string(img, lang=ocr_lang)

    # Fallback: treat as plain text
    return file_bytes.decode("utf-8", errors="ignore")

@app.post("/extract", response_model=ExtractResult)
async def extract(file: UploadFile = File(...), ocr: bool=False, ocr_lang: str="eng"):
    data = await file.read()
    fid = str(uuid.uuid4())
    FILES[fid] = data
    text = extract_text(data, file.filename, ocr=ocr, ocr_lang=ocr_lang)
    if not text.strip():
        raise HTTPException(400, "No extractable text found.")
    result = ExtractResult(file_id=fid, text=text, metadata={"filename": file.filename, "ocr": ocr})
    EXTRACTS[fid] = result
    return result

# ---------- Segment ----------
@app.post("/segment", response_model=SegmentResult)
def segment(raw_text: str):
    idxs = split_blocks(raw_text)
    blocks = [Block(start=s, end=e, preview=raw_text[s:e][:60]) for s, e in idxs]
    return SegmentResult(blocks=blocks)

# ---------- Map ----------
class MapRequest(BaseModel):
    block_texts: List[str]

@app.post("/map", response_model=MapResult)
def map_blocks(req: MapRequest):
    products = [parse_block_to_product(t) for t in req.block_texts]
    return MapResult(products=products)

# ---------- Templates ----------
@app.post("/template/generate", response_model=Template)
def generate_template(name: str, products: List[Product]):
    required = ["name"]
    optional = ["sku","price","currency","description"]
    tpl = Template(id=str(uuid.uuid4()), name=name, required=required, optional=optional)
    return tpl

@app.post("/template/persist", response_model=Template)
def persist_template(tpl: Template):
    if not tpl.id:
        tpl.id = str(uuid.uuid4())
    TEMPLATES[tpl.id] = tpl
    return tpl

@app.get("/templates", response_model=List[Template])
def list_templates():
    return list(TEMPLATES.values())

# ---------- Catalog Generation ----------
@app.post("/generate")
def generate(req: GenerateCatalogRequest):
    tpl = TEMPLATES.get(req.template_id)
    if not tpl:
        raise HTTPException(404, "Template not found")

    # Validate minimal fields
    missing = []
    for i, p in enumerate(req.products):
        if "name" in tpl.required and not (p.name and p.name.strip()):
            missing.append({"row": i, "field": "name"})
    if missing:
        return JSONResponse(status_code=400, content={"error": "validation_failed", "missing": missing})

    html = render_html(tpl, req.products)
    gid = str(uuid.uuid4())
    GENERATED[gid] = html

    if req.format == "html":
        return {"doc_id": gid, "preview_url": f"/generated/{gid}"}
    elif req.format == "pdf":
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html).write_pdf()
            # In production, save to a file or object storage
            return {"doc_id": gid, "format": "pdf", "note": "PDF bytes generated"}
        except Exception as e:
            raise HTTPException(500, f"PDF generation failed: {e}")
    else:
        raise HTTPException(400, "Unsupported format")

@app.get("/generated/{doc_id}")
def get_generated_html(doc_id: str):
    html = GENERATED.get(doc_id)
    if not html:
        raise HTTPException(404, "Not found")
    return HTMLResponse(html)
