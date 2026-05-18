"""
OCR service — wraps AWS Textract in production, mocks in dev.
"""
import re
from pathlib import Path
from app.core.config import settings


GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b")
AMOUNT_RE = re.compile(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{2})?)")
DATE_RE = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b")


def _mock_parse(filename: str) -> dict:
    return {
        "vendor_name": "Mock Vendor Pvt Ltd",
        "vendor_gstin": "27AABCS1429B1ZB",
        "invoice_number": "INV-2025-001",
        "invoice_date": "2025-01-15",
        "taxable_value": 100000.00,
        "igst": 0.0,
        "cgst": 9000.0,
        "sgst": 9000.0,
        "total": 118000.0,
        "raw_text": f"[MOCK OCR for {filename}]",
    }


async def parse_invoice_pdf(file_bytes: bytes, filename: str) -> dict:
    if settings.AWS_ACCESS_KEY_ID == "mock":
        return _mock_parse(filename)

    import boto3
    client = boto3.client(
        "textract",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    response = client.analyze_document(
        Document={"Bytes": file_bytes},
        FeatureTypes=["FORMS", "TABLES"],
    )
    raw_text = " ".join(
        block["Text"]
        for block in response["Blocks"]
        if block["BlockType"] == "LINE" and "Text" in block
    )
    gstins = GSTIN_RE.findall(raw_text)
    amounts = AMOUNT_RE.findall(raw_text)
    dates = DATE_RE.findall(raw_text)

    return {
        "vendor_gstin": gstins[0] if gstins else None,
        "invoice_date": dates[0] if dates else None,
        "amounts_found": [float(a.replace(",", "")) for a in amounts],
        "raw_text": raw_text[:2000],
    }


async def parse_bank_statement(file_bytes: bytes, filename: str, bank: str = "unknown") -> list[dict]:
    """Returns list of transactions parsed from bank PDF/CSV."""
    if settings.AWS_ACCESS_KEY_ID == "mock":
        return [
            {"date": "2025-01-10", "description": "SALARY CREDIT ACME CORP", "credit": 150000, "debit": 0, "balance": 250000},
            {"date": "2025-01-15", "description": "CASH DEPOSIT", "credit": 50000, "debit": 0, "balance": 300000},
            {"date": "2025-01-20", "description": "UPI/AMAZON/PURCHASE", "credit": 0, "debit": 25000, "balance": 275000},
        ]
    # Production: use Textract for PDFs, pandas for CSVs
    raise NotImplementedError("Production bank statement parsing not yet implemented")
