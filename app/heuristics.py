import re
from typing import List, Tuple
from .models import Block, Product

PRICE_RE = re.compile(r"(?:₹|\$|EUR|INR)?\s*([0-9][0-9,]*\.?[0-9]{0,2})")
SKU_RE = re.compile(r"\b(?:SKU|Item Code|Code|Model No\.?)\s*[:\-]?\s*([A-Za-z0-9\-\_\/]+)")

def split_blocks(raw_text: str, min_lines:int=2) -> List[Tuple[int,int]]:
    text = raw_text.replace("\r\n", "\n").strip()
    parts = text.split("\n\n")
    blocks = []
    pos = 0
    for part in parts:
        start = text.find(part, pos)
        end = start + len(part)
        pos = end
        if part.strip() and (part.count("\n") + 1) >= min_lines:
            blocks.append((start, end))
    return blocks

def parse_block_to_product(text: str) -> Product:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    name = lines[0] if lines else None

    desc_lines = []
    for ln in lines[1:]:
        if any(lbl.lower() in ln.lower() for lbl in ["price", "mrp", "sku", "item code", "code", "model"]):
            continue
        desc_lines.append(ln)
    description = " ".join(desc_lines)[:500] if desc_lines else None

    price = None
    currency = None
    m = PRICE_RE.search(text.replace(",", ""))
    if m:
        try:
            price = float(m.group(1))
        except:
            price = None
        currency = "INR" if "₹" in text or "INR" in text.upper() else None
        if not currency and "$" in text: currency = "USD"
        if not currency and "EUR" in text.upper(): currency = "EUR"

    sku = None
    m2 = SKU_RE.search(text)
    if m2:
        sku = m2.group(1)

    return Product(name=name, sku=sku, price=price, currency=currency, description=description)
