from database import save_invoice


# ----------------------------------
# Validate Invoice
# ----------------------------------
def validate_invoice(invoice):

    issues = []

    # ----------------------------------
    # 1. Required fields
    # ----------------------------------
    required_fields = [
        "invoice_number",
        "invoice_date",
        "seller_name",
        "customer_name",
        "subtotal",
        "total"
    ]

    for field in required_fields:

        if not invoice.get(field):
            issues.append(f"Missing field: {field}")

    # ----------------------------------
    # 2. Calculate and validate item amounts
    # ----------------------------------
    items_total = 0

    for item in invoice.get("items", []):

        quantity = item.get("quantity", 0)
        unit_price = item.get("unit_price", 0)
        invoice_amount = item.get("amount", 0)

        calculated_amount = quantity * unit_price

        # Check individual item amount
        if calculated_amount != invoice_amount:

            issues.append(
                f"Item amount mismatch: "
                f"{item.get('description', item.get('name', 'Unknown item'))} "
                f"calculated = ₹{calculated_amount}, "
                f"invoice amount = ₹{invoice_amount}"
            )

        items_total += calculated_amount

    # ----------------------------------
    # 3. Compare subtotal
    # ----------------------------------
    subtotal = invoice.get("subtotal", 0)

    if items_total != subtotal:

        issues.append(
            f"Subtotal mismatch: Items total = ₹{items_total}, "
            f"Invoice subtotal = ₹{subtotal}"
        )

    # ----------------------------------
    # 4. Check final total
    # ----------------------------------
    cgst = invoice.get("cgst", 0)
    sgst = invoice.get("sgst", 0)
    total = invoice.get("total", 0)

    calculated_total = subtotal + cgst + sgst

    if calculated_total != total:

        issues.append(
            f"Total mismatch: Calculated total = ₹{calculated_total}, "
            f"Invoice total = ₹{total}"
        )

    # ----------------------------------
    # 5. Final status
    # ----------------------------------
    if issues:

        status = "REVIEW REQUIRED"

    else:

        status = "VALID"

    return status, issues


# ----------------------------------
# Test validation with sample invoice
# ----------------------------------
if __name__ == "__main__":

    from ai_extract import extract_invoice_data
    from read_invoice import extract_text_from_pdf

    # Read sample invoice
    invoice_text = extract_text_from_pdf("sample_invoice.pdf")

    # AI extraction
    data = extract_invoice_data(invoice_text)

    if data is None:

        print("❌ AI extraction failed.")

    else:

        # Validate
        status, issues = validate_invoice(data)

        print("\n===== LEDGERAGENT VALIDATION =====\n")

        if issues:

            print("⚠️ ISSUES FOUND:\n")

            for issue in issues:

                print("•", issue)

        else:

            print("✅ No issues found.")

        print(f"\nStatus: {status}")

        # Save to database
        save_invoice(data, status)

        print("✅ Invoice saved to database.")
