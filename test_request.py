import requests

samples = [
    "INVOICE\nInvoice No: INV-2026-0041\nDate: 15 March 2026\nVendor: TechParts Pvt Ltd\nBill To: IITM Procurement Dept\n\nItems:\n  USB-C Hub (x2) ............. Rs. 1,299.00\n  HDMI Cable (x3) ............. Rs.   450.00\n                                ----------\n  Subtotal ...................  Rs. 2,199.00\n  GST (18%) ..................  Rs.   395.82\n                                ----------\n  TOTAL ......................  Rs. 2,594.82\nCurrency: INR",
    "NovaSoft Solutions — Tax Invoice\nRef: NS/2026/778\nIssued: 2026-01-22\nClient: DataFlow Analytics\n\nService: API Integration & Consulting — 40 hrs @ Rs. 3,500/hr\nSubtotal: Rs. 1,40,000.00\nIGST (18%): Rs. 25,200.00\nTotal Due: Rs. 1,65,200.00\nCurrency: INR"
]

for i, text in enumerate(samples):
    response = requests.post(
        "http://127.0.0.1:8000/extract",
        json={"invoice_text": text}
    )
    print(f"--- Sample {i+1} ---")
    print(response.status_code)
    print(response.json())
    print()