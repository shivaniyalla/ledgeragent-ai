import os
import json

from dotenv import load_dotenv
from google import genai


# ==========================================
# LOAD GEMINI API KEY
# ==========================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found in .env file."
    )


# ==========================================
# GEMINI CLIENT
# ==========================================

client = genai.Client(api_key=api_key)

MODEL_NAME = "gemini-3.8-flash"


# ==========================================
# AI INVOICE EXTRACTION
# ==========================================

def extract_invoice_data(invoice_text):

    prompt = f"""
You are an accounting document extraction assistant.

Extract the important information from the invoice below.

Return ONLY valid JSON.

Use exactly these fields:

invoice_number
invoice_date
seller_name
seller_gstin
customer_name
items
subtotal
cgst
sgst
total
payment_status

For each item inside "items", use:

description
quantity
unit_price
amount

Important rules:

- quantity must be a number
- unit_price must be a number
- amount must be a number
- subtotal must be a number
- cgst must be a number
- sgst must be a number
- total must be a number
- If a value is not available, use null
- Do not invent information
- Preserve the information from the invoice

Invoice:
{invoice_text}
"""

    try:

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        result = response.text

        data = json.loads(result)

        return data

    except Exception as e:

        print("❌ Gemini invoice extraction failed.")
        print("Error:", e)

        return None


# ==========================================
# DOCUMENT CLASSIFICATION
# ==========================================

def classify_document(document_text):

    prompt = f"""
You are an accounting document classification assistant.

Classify the following financial document into exactly ONE category.

Allowed categories:

Invoice
Receipt
Purchase Document
Sales Document
Bank Statement
Other

Return ONLY the category name.

Do not explain your answer.

Document:
{document_text}
"""

    try:

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        result = response.text.strip()

        allowed_categories = [
            "Invoice",
            "Receipt",
            "Purchase Document",
            "Sales Document",
            "Bank Statement",
            "Other"
        ]

        if result in allowed_categories:
            return result

        return "Other"

    except Exception as e:

        print("❌ Gemini document classification failed.")
        print("Error:", e)

        return "Other"


# ==========================================
# TEST USING SAMPLE INVOICE
# ==========================================

if __name__ == "__main__":

    from read_invoice import extract_text_from_pdf

    invoice_text = extract_text_from_pdf(
        "sample_invoice.pdf"
    )

    print("\n===== GEMINI AI EXTRACTION =====\n")

    data = extract_invoice_data(invoice_text)

    if data:

        print(
            json.dumps(
                data,
                indent=4,
                ensure_ascii=False
            )
        )

    else:

        print("❌ AI extraction failed.")
