# 📘 Catalog Automation POC (LLM-free + OCR)

A **FastAPI** proof-of-concept to:
- extract text from **PDF / DOCX / HTML / Images** (OCR for scanned docs),
- **segment** product blocks,
- **map** blocks to structured **Product JSON**,
- **generate** new catalogs (HTML/PDF) from templates + JSON.

No LLMs. Deterministic parsing + optional OCR (Tesseract).

---

## 🚀 Features
- 📄 Multi-format ingestion (PDF, DOCX, HTML, JPG/PNG/TIFF).
- 🔎 Heuristic segmentation (blank-line & label hints).
- 🧩 Regex mapping (price/SKU/currency) → `Product` JSON.
- 🧱 Template create/persist/list.
- 📝 HTML/PDF generation (Jinja-style renderer; WeasyPrint optional).
- 🖼 OCR for scanned PDFs & images (Tesseract via `pytesseract`).

---
Collection: CatalogPOC.postman_collection.json

Environment: CatalogPOC.postman_environment.json

## How to use in Postman

Open Postman → Import → upload both files.

Select the environment “Catalog POC – Local” at the top-right.

Click the eye icon by the environment → click Edit and set:

baseUrl: http://127.0.0.1:8000

sampleFile: absolute path to a real file on your machine (e.g. C:\Users\you\Downloads\catalog.pdf or /Users/you/Desktop/catalog.pdf)

ocr: false for digital PDFs/Docx/HTML; set true for images/scanned PDFs

ocr_lang: e.g. eng or eng+hin

Run the flow (left panel → “Catalog POC (FastAPI, OCR, No-LLM)”)

01 - Health (GET /health)

Confirms server is up.

02 - Extract (file upload) (POST /extract)

Form-data: picks your {{sampleFile}} path.

Test script auto-saves raw_text and file_id to environment.

03 - Segment (POST /segment)

Uses {{raw_text}} from step 2.

Test script saves blocks and builds block_texts (first two blocks).

04 - Map (POST /map)

Body uses {{block_texts}}.

Test script saves products array.

05 - Template Generate (POST /template/generate)

Uses {{products}}.

Test script saves template_object and template_id.

06 - Template Persist (POST /template/persist)

Saves the template_object returned earlier.

Test script ensures template_id is set.

07 - Templates (GET /templates)

Lists templates; picks the first one if template_id missing.

08 - Generate Catalog (HTML) (POST /generate)

Uses {{template_id}} + {{products}}.

Test script saves doc_id + preview_url.

09 - Get Generated HTML (GET /generated/{{doc_id}})

Opens the rendered HTML catalog.

## Tips

For images/scanned PDFs, set ocr=true in the environment before running step 2.

If step 3 finds zero blocks, open your extracted text and make sure it has blank lines between products (the heuristic splitter uses \n\n).

You can tweak the regex/heuristics in app/heuristics.py to match your catalogs better.

## 🖼 Architecture (Mermaid)

### System Flow (with OCR branch)
```mermaid
flowchart LR
    U[User (Web UI)] -->|Upload| API[FastAPI Backend]

    %% Extraction layer
    subgraph EX [Extraction & Parsing]
      Tika[Apache Tika (type sniff)]
      PDF[pdfplumber (PDF text)]
      DOCX[python-docx (DOCX)]
      HTML[BeautifulSoup (HTML)]
      TAB[Camelot/Tabula (tables)]
      OCR[pytesseract (OCR)]
      P2I[pdf2image (PDF→images)]

      Tika --> Orch
      PDF --> Orch
      DOCX --> Orch
      HTML --> Orch
      TAB --> Orch
      P2I --> OCR --> Orch
    end

    API --> EX
    Orch[Orchestrator] --> Norm[Normalize (price/SKU/currency)]
    Norm --> TD[Template Detector (rules)]
    TD --> MAP[JSON Mapper (schema/jsonschema)]
    MAP --> DB[(SQLite / Postgres)]
    DB --> API

    %% Generation
    subgraph GEN [Catalog Generation]
      DB --> Jinja[Jinja2 → HTML]
      Jinja --> Weasy[WeasyPrint → PDF]
      Jinja --> HOut[HTML Output]
      Weasy --> POut[PDF Output]
    end

    GEN --> API
    API -->|Download JSON/HTML/PDF| U

sequenceDiagram
    participant U as User
    participant A as FastAPI
    participant X as Extractors
    participant H as Heuristics
    participant D as DB

    U->>A: POST /extract (file)
    A->>X: detect type → parse (pdfplumber/docx/bs4) or OCR (pdf2image+tesseract)
    X-->>A: raw text
    U->>A: POST /segment (raw_text)
    A->>H: split on blank lines / label hints
    H-->>A: blocks[]
    U->>A: POST /map (block_texts[])
    A->>H: regex map → Product JSON
    H-->>A: products[]
    U->>A: POST /template/generate (name, products)
    A->>D: save template (/template/persist)
    D-->>A: template_id
    U->>A: POST /generate (template_id, products)
    A->>D: fetch template
    A-->>U: preview_url (HTML) or PDF bytes
