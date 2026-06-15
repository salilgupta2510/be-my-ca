"""
Annual Information Statement (AIS) parser.

AIS is downloadable from IT portal: e-Filing → AIS/TIS → Download JSON or PDF.

Supports:
  - AIS JSON (preferred — direct from portal)
  - AIS PDF (text-based, extracted via pypdf)

Uses Claude to normalize the raw content into AISData regardless of
year-to-year format changes in the portal's export structure.

Key income categories extracted:
  salary_tds         — TDS u/s 192 from employer(s)
  interest_tds       — TDS u/s 194A on FD/savings interest
  interest_credited  — Interest income reported by banks (sans TDS)
  dividend           — Dividends reported u/s 194
  securities_sale    — Sale of listed securities (equity/ETF)
  mf_sale            — Mutual fund redemptions
  advance_tax        — Advance tax challans
  self_assessment    — Self-assessment tax paid
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

import anthropic

from app.core.config import settings
from app.schemas.itr import AISData, AISIncomeItem

_EXTRACTION_PROMPT = """\
You are an Indian income tax document parser. Extract income and TDS information from this Annual Information Statement (AIS) or 26AS document.

Return ONLY valid JSON — no markdown, no explanation, no trailing text.

JSON schema:
{
  "pan": "string or null",
  "taxpayer_name": "string or null",
  "assessment_year": "YYYY-YY format e.g. 2025-26 or null",
  "income_items": [
    {
      "category": "one of: salary_tds, interest_tds, interest_credited, dividend, securities_sale, mf_sale, advance_tax, self_assessment_tax",
      "description": "short description e.g. 'TDS from ACME Technologies (TAN: BLRA12345B)'",
      "payer_name": "string or null",
      "payer_tan_pan": "string or null",
      "amount": 0,
      "tds_deducted": 0
    }
  ],
  "advance_tax_paid": 0,
  "self_assessment_tax_paid": 0,
  "confidence": 0.0
}

Category guide:
  salary_tds         — TDS u/s 192 deducted by employer from salary
  interest_tds       — TDS u/s 194A on FD, savings, recurring deposit interest
  interest_credited  — Interest income where no TDS was deducted (below threshold)
  dividend           — Dividend income u/s 194 from companies
  securities_sale    — Sale proceeds of listed equity shares, ETFs reported by brokers
  mf_sale            — Mutual fund redemption amounts reported by RTAs (CAMS/KFintech)
  advance_tax        — Advance tax paid by taxpayer
  self_assessment_tax — Self-assessment tax paid

Rules:
- amount: gross income amount (before TDS). For securities/MF sale: total sale value.
- tds_deducted: TDS deducted on that item (0 if none).
- Include ALL income items found, even small amounts.
- confidence: 0.0-1.0 reflecting how complete/readable the document was.
"""

_MOCK = AISData(
    pan="ABCPS1234D",
    taxpayer_name="RAHUL SHARMA",
    assessment_year="2025-26",
    income_items=[
        AISIncomeItem(
            category="salary_tds",
            description="TDS from ACME Technologies Pvt Ltd (TAN: BLRA12345B)",
            payer_name="ACME Technologies Pvt Ltd",
            payer_tan_pan="BLRA12345B",
            amount=Decimal("1200000"),
            tds_deducted=Decimal("75000"),
        ),
        AISIncomeItem(
            category="interest_tds",
            description="TDS on FD interest from HDFC Bank",
            payer_name="HDFC Bank",
            payer_tan_pan="MUMB00123A",
            amount=Decimal("15000"),
            tds_deducted=Decimal("1500"),
        ),
        AISIncomeItem(
            category="dividend",
            description="Dividend from Infosys Ltd",
            payer_name="Infosys Ltd",
            payer_tan_pan=None,
            amount=Decimal("5000"),
            tds_deducted=Decimal("500"),
        ),
    ],
    total_tds_from_salary=Decimal("75000"),
    total_tds_from_others=Decimal("2000"),
    total_interest_income=Decimal("15000"),
    total_dividend_income=Decimal("5000"),
    total_securities_sale_value=Decimal("0"),
    total_mf_redemption_value=Decimal("0"),
    advance_tax_paid=Decimal("0"),
    self_assessment_tax_paid=Decimal("0"),
    parse_confidence=1.0,
    raw_text_length=0,
    warnings=["MOCK DATA — upload real AIS JSON or PDF from IT portal."],
)


def _extract_text_pypdf(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception:
        return ""
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n\n--- PAGE BREAK ---\n\n".join(pages)


def _d(val: Any) -> Decimal:
    try:
        cleaned = str(val).replace(",", "").replace("₹", "").strip()
        if cleaned in ("", "null", "None", "nan", "-"):
            return Decimal("0")
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _aggregate(items: list[AISIncomeItem]) -> dict[str, Decimal]:
    agg: dict[str, Decimal] = {
        "salary_tds": Decimal("0"),
        "other_tds": Decimal("0"),
        "interest": Decimal("0"),
        "dividend": Decimal("0"),
        "securities_sale": Decimal("0"),
        "mf_sale": Decimal("0"),
    }
    for item in items:
        cat = item.category
        if cat == "salary_tds":
            agg["salary_tds"] += item.tds_deducted
        elif cat in ("interest_tds", "interest_credited"):
            agg["interest"] += item.amount
            if cat == "interest_tds":
                agg["other_tds"] += item.tds_deducted
        elif cat == "dividend":
            agg["dividend"] += item.amount
            agg["other_tds"] += item.tds_deducted
        elif cat == "securities_sale":
            agg["securities_sale"] += item.amount
        elif cat == "mf_sale":
            agg["mf_sale"] += item.amount
        elif cat in ("advance_tax", "self_assessment_tax"):
            pass  # handled separately
    return agg


def _build(raw: dict[str, Any], text_len: int) -> AISData:
    raw_items = raw.get("income_items", [])
    items = [
        AISIncomeItem(
            category=str(item.get("category", "other")),
            description=str(item.get("description", "")),
            payer_name=item.get("payer_name"),
            payer_tan_pan=item.get("payer_tan_pan"),
            amount=_d(item.get("amount", 0)),
            tds_deducted=_d(item.get("tds_deducted", 0)),
        )
        for item in raw_items
        if isinstance(item, dict)
    ]

    agg = _aggregate(items)
    warnings: list[str] = []
    if not items:
        warnings.append("No income items extracted — document may be incomplete or in an unsupported format.")

    return AISData(
        pan=raw.get("pan"),
        taxpayer_name=raw.get("taxpayer_name"),
        assessment_year=raw.get("assessment_year"),
        income_items=items,
        total_tds_from_salary=agg["salary_tds"],
        total_tds_from_others=agg["other_tds"],
        total_interest_income=agg["interest"],
        total_dividend_income=agg["dividend"],
        total_securities_sale_value=agg["securities_sale"],
        total_mf_redemption_value=agg["mf_sale"],
        advance_tax_paid=_d(raw.get("advance_tax_paid", 0)),
        self_assessment_tax_paid=_d(raw.get("self_assessment_tax_paid", 0)),
        parse_confidence=float(raw.get("confidence", 0.7)),
        raw_text_length=text_len,
        warnings=warnings,
    )


async def parse_ais(file_bytes: bytes, filename: str) -> AISData:
    """
    Parse AIS JSON or PDF. Returns AISData.
    Raises ValueError for unreadable files.
    """
    if settings.ANTHROPIC_API_KEY == "mock":
        return _MOCK

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    fname_lower = filename.lower()

    if fname_lower.endswith(".json"):
        try:
            content_text = file_bytes.decode("utf-8-sig", errors="replace")
            # Pretty-print for Claude — structured JSON is easier to parse
            raw_parsed = json.loads(content_text)
            content_text = json.dumps(raw_parsed, indent=2)[:20000]
        except (json.JSONDecodeError, UnicodeDecodeError):
            content_text = file_bytes.decode("utf-8-sig", errors="replace")[:20000]
        text_len = len(content_text)
        doc_label = "AIS JSON file"
    else:
        # PDF path
        content_text = _extract_text_pypdf(file_bytes)
        if len(content_text.strip()) < 50:
            raise ValueError(
                "Could not extract text from AIS PDF. "
                "Try downloading the AIS JSON from IT portal instead."
            )
        content_text = content_text[:20000]
        text_len = len(content_text)
        doc_label = "AIS PDF text"

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": f"{doc_label}:\n\n{content_text}"}],
    )

    raw_json = response.content[0].text.strip()
    raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
    raw_json = re.sub(r"\s*```$", "", raw_json)

    try:
        raw = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Claude response: {e}\nRaw: {raw_json[:300]}") from e

    return _build(raw, text_len)
