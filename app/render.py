from typing import List
from .models import Product, Template

def render_html(tpl: Template, products: List[Product]) -> str:
    items = []
    for p in products:
        items.append(f"""
        <li style="margin-bottom:12px">
          <div><strong>{p.name or 'Unnamed'}</strong></div>
          <div>SKU: {p.sku or '-'} | Price: {p.price or '-'} {p.currency or ''}</div>
          <div><em>{p.description or ''}</em></div>
        </li>
        """)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Catalog</title></head>
<body style="font-family:system-ui;max-width:800px;margin:24px auto">
<h1>{tpl.name}</h1>
<ul style="list-style:disc">
{''.join(items)}
</ul>
</body></html>"""
