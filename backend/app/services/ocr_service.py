"""
OCR service — uses Claude Vision for document parsing.
"""
import re

GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b")
AMOUNT_RE = re.compile(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{2})?)")
DATE_RE = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b")


async def parse_bank_statement(file_bytes: bytes, filename: str, bank: str = "unknown") -> list[dict]:
    """Returns mock transactions — real parsing not yet implemented."""
    return [
        {"date": "2025-01-10", "description": "SALARY CREDIT ACME CORP", "credit": 150000, "debit": 0, "balance": 250000},
        {"date": "2025-01-15", "description": "CASH DEPOSIT", "credit": 50000, "debit": 0, "balance": 300000},
        {"date": "2025-01-20", "description": "UPI/AMAZON/PURCHASE", "credit": 0, "debit": 25000, "balance": 275000},
    ]
