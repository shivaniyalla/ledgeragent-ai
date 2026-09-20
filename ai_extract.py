import os
import json

from dotenv import load_dotenv
from openai import OpenAI


# ----------------------------------
# Load API key
# ----------------------------------
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file.")


# ----------------------------------
# OpenAI client
# ----------------------------------
client = OpenAI(api_key=api_key)


# ----------------------------------
# AI Invoice Extraction Function
# ----------------------------------
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

Invoice:
{invoice_text}
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt
    )

    result = response.output_text

    try:
        data = json.loads(result)
        return data

    except json.JSONDecodeError:
        print("AI response was not valid JSON.")
        print(result)
        return None
# ----------------------------------
# Document Classification
# ----------------------------------
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

Document:
{document_text}
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt
    )

    result = response.output_text.strip()

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

# ----------------------------------
# Test using sample invoice
# ----------------------------------
if __name__ == "__main__":

    from read_invoice import extract_text_from_pdf

    invoice_text = extract_text_from_pdf("sample_invoice.pdf")

    data = extract_invoice_data(invoice_text)

    print("\n===== AI EXTRACTED DATA =====\n")

    if data:
        print(json.dumps(data, indent=4))
    else:
        print("❌ AI extraction failed.")