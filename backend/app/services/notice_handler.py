"""
IT department notice PDF parser.

Extracts: notice type, section, AY, DIN, deadline, amount demanded.
Generates: severity, plain-language explanation, action steps.

Supported notice types:
  143(1)  — Intimation (processed return)
  139(9)  — Defective return (15 days to fix)
  148     — Reassessment notice
  245     — Refund adjusted against demand
  156     — Tax demand notice
  271     — Penalty notice
  131     — Summons
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

import anthropic

from app.core.config import settings
from app.schemas.itr import ITNotice, ITNoticeType, NoticeExplanation

_EXTRACTION_PROMPT = """\
You are an Indian income tax notice parser. Extract key details from this IT department notice.

Return ONLY valid JSON — no markdown, no explanation, no trailing text.

JSON schema:
{
  "notice_type": "one of: 143(1), 139(9), 148, 245, 156, 271, 131, unknown",
  "section": "full section string e.g. '143(1)' or 'section 148 read with 147' or null",
  "assessment_year": "YYYY-YY format e.g. 2024-25 or null",
  "financial_year": "YYYY-YY format e.g. 2023-24 or null",
  "din": "Document Identification Number (DIN) — alphanumeric code usually near top of notice, or null",
  "notice_date": "DD/MM/YYYY or null",
  "deadline": "compliance/response deadline DD/MM/YYYY or null",
  "amount_demanded": 0,
  "compliance_required": "brief description of what the taxpayer must do, or null",
  "confidence": 0.0,
  "severity": "low | medium | high | critical",
  "plain_english": "2-3 sentence plain English explanation of what this notice means and why it was sent",
  "action_required": "specific numbered steps the taxpayer should take",
  "key_points": ["array", "of", "key", "bullet", "points"],
  "do_not_ignore": true
}

Severity guide:
  low      — 143(1) intimation with no demand; 245 refund adjustment (informational)
  medium   — 139(9) defective return (must fix within 15 days or return treated as not filed)
             156 with moderate demand (verify and pay/contest)
  high     — 148 reassessment; 271 penalty; 156 with large demand
  critical — 131 summons; criminal proceedings; contempt risk

Rules:
- amount_demanded: 0 if no demand. Negative if refund. Exact INR amount as plain number.
- do_not_ignore: false ONLY for 143(1) with zero demand and no discrepancy. true for everything else.
- deadline: extract exact date if stated. Very important — taxpayers miss deadlines.
- If notice has multiple sections, use the primary one for notice_type.
"""

_MOCK = NoticeExplanation(
    notice=ITNotice(
        notice_type=ITNoticeType.INTIMATION_143_1,
        section="143(1)",
        assessment_year="2024-25",
        financial_year="2023-24",
        din="ITBA/CPC/24/25/1234567890",
        notice_date="15/01/2025",
        deadline="31/03/2025",
        amount_demanded=Decimal("0"),
        compliance_required="No action required if you agree with the computation.",
        raw_text_length=0,
        parse_confidence=1.0,
    ),
    severity="low",
    plain_english=(
        "This is an intimation under section 143(1) — the IT department's automated "
        "processing result for your filed return. It confirms that your return was "
        "processed and no additional tax demand has been raised."
    ),
    action_required=(
        "1. Compare the intimation figures with your filed ITR. "
        "2. If figures match, no action needed — keep this for records. "
        "3. If there's a discrepancy, file a rectification request u/s 154 within 4 years."
    ),
    deadline_urgent=False,
    key_points=[
        "Intimation u/s 143(1) — routine processing result",
        "No additional tax demand raised",
        "Compare with your filed return figures",
        "MOCK DATA — upload real IT notice PDF",
    ],
    do_not_ignore=False,
)


def _extract_text(pdf_bytes: bytes) -> str:
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


def _notice_type(raw: str) -> ITNoticeType:
    mapping = {
        "143(1)": ITNoticeType.INTIMATION_143_1,
        "139(9)": ITNoticeType.DEFECTIVE_139_9,
        "148": ITNoticeType.REASSESSMENT_148,
        "245": ITNoticeType.REFUND_ADJUSTED_245,
        "156": ITNoticeType.DEMAND_156,
        "271": ITNoticeType.PENALTY_271,
        "131": ITNoticeType.SUMMONS_131,
    }
    return mapping.get(raw.strip(), ITNoticeType.UNKNOWN)


def _deadline_urgent(deadline_str: str | None) -> bool:
    if not deadline_str:
        return False
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            dl = datetime.strptime(deadline_str.strip(), fmt).date()
            return (dl - date.today()).days <= 30
        except ValueError:
            continue
    return False


async def parse_notice(pdf_bytes: bytes, filename: str = "notice.pdf") -> NoticeExplanation:
    """
    Parse IT department notice PDF.
    Returns structured data + plain-language explanation with severity and action steps.
    Raises ValueError for unreadable PDFs.
    """
    if settings.ANTHROPIC_API_KEY == "mock":
        return _MOCK

    text = _extract_text(pdf_bytes)
    if len(text.strip()) < 50:
        raise ValueError(
            "Could not extract text from notice PDF. "
            "Check if it is scanned (image PDF) or password-protected."
        )

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": f"IT Notice text:\n\n{text[:12000]}"}],
    )

    raw_json = response.content[0].text.strip()
    raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
    raw_json = re.sub(r"\s*```$", "", raw_json)

    try:
        raw = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Claude response: {e}\nRaw: {raw_json[:300]}") from e

    severity = raw.get("severity", "medium")
    if severity not in {"low", "medium", "high", "critical"}:
        severity = "medium"

    notice = ITNotice(
        notice_type=_notice_type(str(raw.get("notice_type", "unknown"))),
        section=raw.get("section"),
        assessment_year=raw.get("assessment_year"),
        financial_year=raw.get("financial_year"),
        din=raw.get("din"),
        notice_date=raw.get("notice_date"),
        deadline=raw.get("deadline"),
        amount_demanded=Decimal(str(raw.get("amount_demanded") or 0)),
        compliance_required=raw.get("compliance_required"),
        raw_text_length=len(text),
        parse_confidence=float(raw.get("confidence", 0.7)),
    )

    return NoticeExplanation(
        notice=notice,
        severity=severity,
        plain_english=raw.get("plain_english", ""),
        action_required=raw.get("action_required", ""),
        deadline_urgent=_deadline_urgent(notice.deadline),
        key_points=raw.get("key_points", []),
        do_not_ignore=bool(raw.get("do_not_ignore", True)),
    )
