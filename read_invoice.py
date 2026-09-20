import pymupdf


def extract_text_from_pdf(pdf_path):
    doc = pymupdf.open(pdf_path)

    text = ""

    for page in doc:
        text += page.get_text()

    doc.close()

    return text


if __name__ == "__main__":
    pdf_filename = "sample_invoice.pdf"

    extracted_text = extract_text_from_pdf(pdf_filename)

    print("\n===== EXTRACTED INVOICE TEXT =====\n")
    print(extracted_text)