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
