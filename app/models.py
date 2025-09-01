from __future__ import annotations
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class Block(BaseModel):
    start: int
    end: int
    preview: str

class SegmentResult(BaseModel):
    blocks: List[Block]

class Product(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None

class MapResult(BaseModel):
    products: List[Product]

class Template(BaseModel):
    id: Optional[str] = None
    name: str
    required: List[str] = ["name"]
    optional: List[str] = ["sku","price","currency","description"]
    label_aliases: Dict[str, List[str]] = {
        "sku": ["SKU","Item Code","Code","Model No."],
        "price": ["Price","MRP","List Price"]
    }
    field_hints: Dict[str, Any] = {
        "price_regex": r"[0-9]+(?:\.[0-9]{1,2})?",
        "currency_whitelist": ["INR","₹","USD","$","EUR","€"]
    }

class ExtractResult(BaseModel):
    file_id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GenerateCatalogRequest(BaseModel):
    template_id: str
    products: List[Product]
    format: str = "html"
