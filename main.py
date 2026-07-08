import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceRequest(BaseModel):
    invoice_text: str

def parse_amount(raw: str) -> float:
    # Remove currency symbols, "Rs.", commas, spaces -> keep only digits and dot
    cleaned = re.sub(r"[^\d.]", "", raw)
    return float(cleaned)

def parse_date(raw: str) -> str:
    raw = raw.strip()
    formats = ["%d %B %Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

@app.post("/extract")
def extract(body: InvoiceRequest):
    text = body.invoice_text

    result = {
        "invoice_no": None,
        "date": None,
        "vendor": None,
        "amount": None,
        "tax": None,
        "currency": None,
    }

    # Invoice number: "Invoice No: XXX" or "Ref: XXX"
    m = re.search(r"(?:Invoice No|Ref)[:\s]+([A-Za-z0-9/\-]+)", text)
    if m:
        result["invoice_no"] = m.group(1).strip()

    # Date: "Date: 15 March 2026" or "Issued: 2026-01-22"
    m = re.search(r"(?:Date|Issued)[:\s]+([A-Za-z0-9 \-/]+)", text)
    if m:
        result["date"] = parse_date(m.group(1))

    # Vendor: try multiple common labels, then fall back to first line pattern
    m = re.search(r"(?:Vendor|From|Sold By|Billed By|Company|Seller)[:\s]+([^\n]+)", text, re.IGNORECASE)
    if m:
        result["vendor"] = m.group(1).strip()
    else:
        m = re.search(r"^([A-Za-z0-9 &]+)\s+—", text)
        if m:
            result["vendor"] = m.group(1).strip()

    # Amount (subtotal): "Subtotal ... Rs. 2,199.00"
    m = re.search(r"Subtotal[.\s:]*Rs\.?\s*([\d,]+\.\d{2})", text)
    if m:
        result["amount"] = parse_amount(m.group(1))

    # Tax: "GST (18%) ... Rs. 395.82" or "IGST (18%): Rs. 25,200.00"
    m = re.search(r"(?:GST|IGST)[^R]*Rs\.?\s*([\d,]+\.\d{2})", text)
    if m:
        result["tax"] = parse_amount(m.group(1))

    # Currency: "Currency: INR"
    m = re.search(r"Currency[:\s]+([A-Za-z]+)", text)
    if m:
        result["currency"] = m.group(1).strip()

    return result