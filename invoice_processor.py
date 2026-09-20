import pymupdf
import re


def extract_text_from_pdf(pdf_path):
    doc = pymupdf.open(pdf_path)

    text = ""

    for page in doc:
        text += page.get_text()

    doc.close()

    return text


def extract_invoice_details(pdf_path):
    text = extract_text_from_pdf(pdf_path)

    details = {
    "invoice_number": None,
    "invoice_date": None,
    "order_id": None,
    "seller_name": None,
    "seller_gstin": None,
    "total": None,
}

    # Invoice Number
    match = re.search(r"Invoice Number\s*#\s*([A-Z0-9]+)", text)
    if match:
        details["invoice_number"] = match.group(1)

    # Invoice Date
    match = re.search(r"(\d{2}-\d{2}-\d{4})\s*Invoice Date:", text)
    if match:
        details["invoice_date"] = match.group(1)

    # Order ID
    match = re.search(r"Order ID:\s*([A-Z0-9]+)", text)
    if match:
        details["order_id"] = match.group(1)
 # Seller
    match = re.search(
    r"Sold By:\s*\n?\s*([A-Za-z0-9 &.,]+?)(?:\s*,|\n)",
    text
)

    if match:
     details["seller_name"] = match.group(1).strip()
    # GSTIN
    match = re.search(r"GSTIN\s*-\s*([A-Z0-9]+)", text)
    if match:
        details["seller_gstin"] = match.group(1)

    # Grand Total
    match = re.search(r"Grand Total\s*₹\s*([\d,.]+)", text)
    if match:
        details["total"] = match.group(1)

    return details