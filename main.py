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

    # Vendor: try multiple common labels first
    m = re.search(
        r"(?:Vendor|From|Sold By|Billed By|Bill From|Supplier|Company|Company Name|Seller|Issued By)"
        r"[:\s]+([^\n]+)",
        text, re.IGNORECASE
    )
    if m:
        result["vendor"] = m.group(1).strip()
    else:
        # Try "Name — Tax Invoice" style first line
        m = re.search(r"^([A-Za-z0-9 &.]+?)\s+—", text)
        if m:
            result["vendor"] = m.group(1).strip()
        else:
            # Last resort: use the first non-empty line that isn't a generic header like "INVOICE"
            for line in text.strip().splitlines():
                line = line.strip()
                if line and line.upper() not in ("INVOICE", "TAX INVOICE", "RECEIPT"):
                    result["vendor"] = line
                    break

    # Amount (subtotal): search only within the same line as the label
    m = re.search(r"(?:Subtotal|Amount)[^\n]*?([\d][\d,]*(?:\.\d{1,2})?)", text, re.IGNORECASE)
    if m:
        result["amount"] = parse_amount(m.group(1))

    # Tax: skip past any percentage (with or without parentheses), avoid "Tax Invoice" title
    m = re.search(
        r"(?:GST|IGST|CGST|SGST|VAT|Tax(?!\s*Invoice))"
        r"(?:\s*\(?\s*\d+(?:\.\d+)?\s*%\s*\)?)?"   # optional percentage, e.g. "(18%)" or "18%"
        r"[^\n\d]*"                                  # skip any non-digit chars (labels, colons, currency)
        r"([\d][\d,]*(?:\.\d{1,2})?)",               # the actual amount
        text, re.IGNORECASE
    )
    if m:
        result["tax"] = parse_amount(m.group(1))

    # Currency: explicit label first, then fall back to detecting symbols
    m = re.search(r"Currency[:\s]+([A-Za-z]+)", text, re.IGNORECASE)
    if m:
        result["currency"] = m.group(1).strip().upper()
    else:
        symbol_map = {
            "₹": "INR", "Rs.": "INR", "Rs": "INR",
            "$": "USD",
            "£": "GBP",
            "€": "EUR",
            "¥": "JPY",
        }
        for symbol, code in symbol_map.items():
            if symbol in text:
                result["currency"] = code
                break
        else:
            # last resort: look for a bare 3-letter currency code like USD, GBP, EUR
            m = re.search(r"\b(INR|USD|GBP|EUR|JPY|AUD|CAD)\b", text)
            if m:
                result["currency"] = m.group(1)

    return result