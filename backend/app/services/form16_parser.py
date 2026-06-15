"""
Form 16 parser — extracts structured salary/TDS data from employer-issued PDF.

Strategy:
  1. Extract text via pypdf (works for digitally-generated PDFs, ~95% of cases).
  2. If text < 200 chars (scanned/image PDF), fall back to Claude Vision
     on page 1 + page 2 rendered as base64 PNG via pypdf's page-to-image.
  3. Pass extracted text (or images) to Claude with a strict JSON extraction prompt.
  4. Validate and coerce into Form16Data schema.

Form 16 structure:
  Part A  — employer/employee identity, TAN, quarterly TDS deducted & deposited.
  Part B  — salary breakup, exemptions (Sec 10), deductions (Sec 16 + Ch. VI-A),
            taxable income, tax computation, TDS summary.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

import anthropic

from app.core.config import settings
from app.schemas.itr import (
    Form16Data,
    Form16Deductions,
    Form16PartA,
    Form16PartB,
)

_MOCK_FORM16 = Form16Data(
    part_a=Form16PartA(
        employer_name="ACME Technologies Pvt Ltd",
        employer_tan="BLRA12345B",
        employer_pan="AABCA1234A",
        employee_name="RAHUL SHARMA",
        employee_pan="ABCPS1234D",
        employee_designation="Software Engineer",
        financial_year="2024-25",
        assessment_year="2025-26",
        period_from="01/04/2024",
        period_to="31/03/2025",
        tds_q1=Decimal("18750"),
        tds_q2=Decimal("18750"),
        tds_q3=Decimal("18750"),
        tds_q4=Decimal("18750"),
        total_tds_deducted=Decimal("75000"),
        total_tds_deposited=Decimal("75000"),
    ),
    part_b=Form16PartB(
        salary_17_1=Decimal("1200000"),
        perquisites_17_2=Decimal("0"),
        profits_lieu_salary_17_3=Decimal("0"),
        gross_salary=Decimal("1200000"),
        hra_received=Decimal("240000"),
        hra_exempt_10_13a=Decimal("120000"),
        lta_exempt_10_5=Decimal("20000"),
        other_exempt_10=Decimal("0"),
        total_exemptions=Decimal("140000"),
        net_salary=Decimal("1060000"),
        standard_deduction_16=Decimal("75000"),
        professional_tax_16_iii=Decimal("2400"),
        total_deductions_16=Decimal("77400"),
        income_from_salary=Decimal("982600"),
        deductions=Form16Deductions(
            sec_80c=Decimal("150000"),
            sec_80d=Decimal("25000"),
            total=Decimal("175000"),
        ),
        total_taxable_income=Decimal("807600"),
        tax_on_total_income=Decimal("77520"),
        rebate_87a=Decimal("0"),
        tax_after_rebate=Decimal("77520"),
        surcharge=Decimal("0"),
        health_education_cess=Decimal("3101"),
        total_tax_payable=Decimal("80621"),
        net_tax_payable=Decimal("80621"),
        tds_by_this_employer=Decimal("75000"),
        total_tds=Decimal("75000"),
        balance_tax_payable=Decimal("5621"),
    ),
    parse_confidence=1.0,
    raw_text_length=0,
    warnings=["MOCK DATA — real Form 16 PDF required"],
)

_EXTRACTION_PROMPT = """\
You are an Indian tax document parser. Extract all data from this Form 16 (TDS Certificate) issued by an employer.

Return ONLY valid JSON — no markdown, no explanation, no trailing text.

JSON schema:
{
  "part_a": {
    "employer_name": "string or null",
    "employer_tan": "string or null",
    "employer_pan": "string or null",
    "employee_name": "string or null",
    "employee_pan": "string or null",
    "employee_designation": "string or null",
    "financial_year": "YYYY-YY format e.g. 2024-25 or null",
    "assessment_year": "YYYY-YY format e.g. 2025-26 or null",
    "period_from": "DD/MM/YYYY or null",
    "period_to": "DD/MM/YYYY or null",
    "tds_q1": 0,
    "tds_q2": 0,
    "tds_q3": 0,
    "tds_q4": 0,
    "total_tds_deducted": 0,
    "total_tds_deposited": 0
  },
  "part_b": {
    "salary_17_1": 0,
    "perquisites_17_2": 0,
    "profits_lieu_salary_17_3": 0,
    "gross_salary": 0,
    "hra_received": 0,
    "hra_exempt_10_13a": 0,
    "lta_exempt_10_5": 0,
    "other_exempt_10": 0,
    "total_exemptions": 0,
    "net_salary": 0,
    "standard_deduction_16": 0,
    "entertainment_allowance_16_ii": 0,
    "professional_tax_16_iii": 0,
    "total_deductions_16": 0,
    "income_from_salary": 0,
    "deductions": {
      "sec_80c": 0,
      "sec_80ccc": 0,
      "sec_80ccd_1": 0,
      "sec_80ccd_1b": 0,
      "sec_80ccd_2": 0,
      "sec_80d": 0,
      "sec_80dd": 0,
      "sec_80ddb": 0,
      "sec_80e": 0,
      "sec_80g": 0,
      "sec_80gg": 0,
      "sec_80tta": 0,
      "sec_80ttb": 0,
      "sec_80u": 0,
      "total": 0
    },
    "total_taxable_income": 0,
    "tax_on_total_income": 0,
    "rebate_87a": 0,
    "tax_after_rebate": 0,
    "surcharge": 0,
    "health_education_cess": 0,
    "total_tax_payable": 0,
    "relief_89": 0,
    "net_tax_payable": 0,
    "tds_by_this_employer": 0,
    "tds_by_other_employers": 0,
    "total_tds": 0,
    "balance_tax_payable": 0
  },
  "confidence": 0.0
}

Rules:
- All monetary amounts in INR as plain numbers (no commas, no ₹ symbol).
- If a field is absent in the document, use 0 for numbers and null for strings.
- confidence: float 0.0-1.0 reflecting how complete/readable the document was.
- balance_tax_payable: negative means refund due, positive means tax still owed.
- Do not infer or compute values not explicitly stated in the document.
"""


def _extract_text_pypdf(pdf_bytes: bytes) -> str:
    """Extract text from all pages. Returns empty string if pypdf unavailable."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception:
        return ""
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n\n--- PAGE BREAK ---\n\n".join(pages)


def _pdf_pages_to_base64(pdf_bytes: bytes, max_pages: int = 3) -> list[str]:
    """Convert first N pages to base64 PNG for Vision fallback."""
    try:
        from pypdf import PdfReader
        from pypdf.generic import RectangleObject
        import base64

        reader = PdfReader(BytesIO(pdf_bytes))
        images: list[str] = []
        for i, page in enumerate(reader.pages[:max_pages]):
            # Try to extract embedded images from the page
            for img_obj in page.images:
                raw = img_obj.data
                images.append(base64.standard_b64encode(raw).decode())
                break  # one image per page is enough
            if len(images) <= i:
                # No embedded image — page is text-based, shouldn't reach here
                images.append("")
        return images
    except Exception:
        return []


def _d(val: Any) -> Decimal:
    if val is None:
        return Decimal("0")
    try:
        # Remove commas e.g. "1,20,000"
        cleaned = re.sub(r"[,\s₹Rs.]", "", str(val))
        return Decimal(cleaned) if cleaned else Decimal("0")
    except InvalidOperation:
        return Decimal("0")


def _build_form16(raw: dict[str, Any], text_length: int) -> Form16Data:
    """Coerce raw Claude JSON → validated Form16Data."""
    pa = raw.get("part_a", {})
    pb = raw.get("part_b", {})
    ded = pb.get("deductions", {})
    confidence = float(raw.get("confidence", 0.5))

    warnings: list[str] = []

    part_a = Form16PartA(
        employer_name=pa.get("employer_name"),
        employer_tan=pa.get("employer_tan"),
        employer_pan=pa.get("employer_pan"),
        employee_name=pa.get("employee_name"),
        employee_pan=pa.get("employee_pan"),
        employee_designation=pa.get("employee_designation"),
        financial_year=pa.get("financial_year"),
        assessment_year=pa.get("assessment_year"),
        period_from=pa.get("period_from"),
        period_to=pa.get("period_to"),
        tds_q1=_d(pa.get("tds_q1")),
        tds_q2=_d(pa.get("tds_q2")),
        tds_q3=_d(pa.get("tds_q3")),
        tds_q4=_d(pa.get("tds_q4")),
        total_tds_deducted=_d(pa.get("total_tds_deducted")),
        total_tds_deposited=_d(pa.get("total_tds_deposited")),
    )

    deductions = Form16Deductions(
        sec_80c=_d(ded.get("sec_80c")),
        sec_80ccc=_d(ded.get("sec_80ccc")),
        sec_80ccd_1=_d(ded.get("sec_80ccd_1")),
        sec_80ccd_1b=_d(ded.get("sec_80ccd_1b")),
        sec_80ccd_2=_d(ded.get("sec_80ccd_2")),
        sec_80d=_d(ded.get("sec_80d")),
        sec_80dd=_d(ded.get("sec_80dd")),
        sec_80ddb=_d(ded.get("sec_80ddb")),
        sec_80e=_d(ded.get("sec_80e")),
        sec_80g=_d(ded.get("sec_80g")),
        sec_80gg=_d(ded.get("sec_80gg")),
        sec_80tta=_d(ded.get("sec_80tta")),
        sec_80ttb=_d(ded.get("sec_80ttb")),
        sec_80u=_d(ded.get("sec_80u")),
        total=_d(ded.get("total")),
    )

    part_b = Form16PartB(
        salary_17_1=_d(pb.get("salary_17_1")),
        perquisites_17_2=_d(pb.get("perquisites_17_2")),
        profits_lieu_salary_17_3=_d(pb.get("profits_lieu_salary_17_3")),
        gross_salary=_d(pb.get("gross_salary")),
        hra_received=_d(pb.get("hra_received")),
        hra_exempt_10_13a=_d(pb.get("hra_exempt_10_13a")),
        lta_exempt_10_5=_d(pb.get("lta_exempt_10_5")),
        other_exempt_10=_d(pb.get("other_exempt_10")),
        total_exemptions=_d(pb.get("total_exemptions")),
        net_salary=_d(pb.get("net_salary")),
        standard_deduction_16=_d(pb.get("standard_deduction_16")),
        entertainment_allowance_16_ii=_d(pb.get("entertainment_allowance_16_ii")),
        professional_tax_16_iii=_d(pb.get("professional_tax_16_iii")),
        total_deductions_16=_d(pb.get("total_deductions_16")),
        income_from_salary=_d(pb.get("income_from_salary")),
        deductions=deductions,
        total_taxable_income=_d(pb.get("total_taxable_income")),
        tax_on_total_income=_d(pb.get("tax_on_total_income")),
        rebate_87a=_d(pb.get("rebate_87a")),
        tax_after_rebate=_d(pb.get("tax_after_rebate")),
        surcharge=_d(pb.get("surcharge")),
        health_education_cess=_d(pb.get("health_education_cess")),
        total_tax_payable=_d(pb.get("total_tax_payable")),
        relief_89=_d(pb.get("relief_89")),
        net_tax_payable=_d(pb.get("net_tax_payable")),
        tds_by_this_employer=_d(pb.get("tds_by_this_employer")),
        tds_by_other_employers=_d(pb.get("tds_by_other_employers")),
        total_tds=_d(pb.get("total_tds")),
        balance_tax_payable=_d(pb.get("balance_tax_payable")),
    )

    # Sanity checks → warnings
    if not part_a.employee_pan:
        warnings.append("Employee PAN not found — verify manually.")
    if not part_a.employer_tan:
        warnings.append("Employer TAN not found — may be Part A missing.")
    if part_b.gross_salary == 0:
        warnings.append("Gross salary is zero — Part B may not have parsed correctly.")
    q_sum = part_a.tds_q1 + part_a.tds_q2 + part_a.tds_q3 + part_a.tds_q4
    if q_sum and abs(q_sum - part_a.total_tds_deducted) > Decimal("10"):
        warnings.append(
            f"TDS quarterly sum ({q_sum}) ≠ total TDS ({part_a.total_tds_deducted}) — check Part A."
        )

    return Form16Data(
        part_a=part_a,
        part_b=part_b,
        parse_confidence=confidence,
        raw_text_length=text_length,
        warnings=warnings,
        raw_extraction=raw,
    )


async def parse_form16(pdf_bytes: bytes, filename: str = "form16.pdf") -> Form16Data:
    """
    Parse a Form 16 PDF and return structured Form16Data.
    Raises ValueError for unrecoverable parse failures.
    """
    if settings.ANTHROPIC_API_KEY == "mock":
        mock = _MOCK_FORM16.model_copy()
        mock.warnings = ["MOCK DATA — set ANTHROPIC_API_KEY to parse real Form 16."]
        return mock

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    text = _extract_text_pypdf(pdf_bytes)
    use_vision = len(text.strip()) < 200  # scanned / image-based PDF

    if use_vision:
        # Vision path — send page images to Claude
        images = _pdf_pages_to_base64(pdf_bytes, max_pages=3)
        if not images:
            raise ValueError("Could not extract text or images from PDF. Is it password-protected?")

        content: list[dict] = []
        for b64 in images:
            if b64:
                content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": b64},
                })
        content.append({"type": "text", "text": _EXTRACTION_PROMPT})

        response = client.messages.create(
            model="claude-opus-4-8",  # Vision needs a capable model
            max_tokens=2048,
            messages=[{"role": "user", "content": content}],
        )
        raw_json = response.content[0].text.strip()
    else:
        # Text path — cheaper, faster
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # Haiku sufficient for structured extraction
            max_tokens=2048,
            system=_EXTRACTION_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Form 16 document text:\n\n{text[:15000]}",  # cap at 15k chars
            }],
        )
        raw_json = response.content[0].text.strip()

    # Strip markdown fences if Claude added them
    raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
    raw_json = re.sub(r"\s*```$", "", raw_json)

    try:
        raw = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned invalid JSON: {e}\nRaw: {raw_json[:200]}") from e

    return _build_form16(raw, text_length=len(text))
