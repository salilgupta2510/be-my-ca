"""
WhatsApp bot logic — intent dispatch, filing status, invoice upload.
"""
import base64
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business
from app.models.gst_return import GSTReturn, ReturnType
from app.models.invoice import InwardInvoice, InvoiceSource, OutwardInvoice, InvoiceType
from app.models.user import User
from app.models.whatsapp import WhatsAppSession
from app.services.claude_ai import chat_concierge
from app.services.whatsapp_client import download_media


HELP_TEXT = """*BeMyCa Bot* — what I can do:
• *status* — filing status for current period
• Send a PDF/image invoice — I'll read and save it
• Any tax question — ask me!

Type *help* anytime."""

FILING_STATUS_KEYWORDS = {"status", "gstr", "filing", "filed", "return", "returns", "file"}


def _current_period() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year}-{now.month:02d}"


async def parse_intent(text: str) -> str:
    lower = text.lower().strip()
    if any(k in lower for k in FILING_STATUS_KEYWORDS):
        return "filing_status"
    if lower in {"help", "hi", "hello", "?", "menu"}:
        return "help"
    return "chat"


async def _get_filing_status(user: User, db: AsyncSession) -> str:
    business = await db.scalar(select(Business).where(Business.user_id == user.id))
    # TODO: enable multi-business selection when multi-business lands
    if not business:
        return "No business registered. Set up your GSTIN at bemyca.in/onboarding"

    period = _current_period()
    returns = await db.execute(
        select(GSTReturn).where(
            GSTReturn.business_id == business.id,
            GSTReturn.period == period,
            GSTReturn.return_type.in_([ReturnType.GSTR1, ReturnType.GSTR3B]),
        )
    )
    rows = {r.return_type: r for r in returns.scalars()}

    def fmt_return(key: ReturnType, label: str) -> str:
        r = rows.get(key)
        if not r:
            return f"• {label}: Not computed"
        if r.status.value == "filed":
            return f"• {label}: ✅ Filed (ARN: {r.arn})"
        return f"• {label}: 🔴 {r.status.value.replace('_', ' ').title()}"

    lines = [
        f"*Filing Status — {period}*",
        f"GSTIN: {business.gstin}",
        "",
        fmt_return(ReturnType.GSTR1, "GSTR-1"),
        fmt_return(ReturnType.GSTR3B, "GSTR-3B"),
    ]
    return "\n".join(lines)


async def _parse_invoice_bytes(file_bytes: bytes, mime_type: str) -> dict | None:
    """Use Claude Vision to extract invoice fields."""
    from app.core.config import settings
    if settings.ANTHROPIC_API_KEY == "mock":
        return {
            "vendor_name": "Mock Vendor Pvt Ltd",
            "invoice_number": "INV-2024-001",
            "invoice_date": "2025-01-15",
            "taxable_value": 10000.0,
            "igst": 0.0,
            "cgst": 900.0,
            "sgst": 900.0,
            "hsn_code": "998314",
            "supplier_gstin": None,
        }

    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    b64 = base64.standard_b64encode(file_bytes).decode()
    media_type = mime_type if mime_type in ("image/jpeg", "image/png", "image/gif", "image/webp") else "image/jpeg"

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                },
                {
                    "type": "text",
                    "text": (
                        "Extract from this invoice: vendor_name, invoice_number, invoice_date (YYYY-MM-DD), "
                        "taxable_value, igst, cgst, sgst, cess, hsn_code, supplier_gstin. "
                        "Reply ONLY as valid JSON with these keys. Use 0 for missing amounts. "
                        "Use null for missing strings."
                    ),
                },
            ],
        }],
    )
    import json, re
    text = message.content[0].text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    return json.loads(match.group())


async def _save_invoice(
    inv_type: str,
    parsed: dict,
    business_id,
    db: AsyncSession,
) -> str:
    period = _current_period()
    try:
        date_str = parsed.get("invoice_date") or datetime.now().strftime("%Y-%m-%d")
        from datetime import date as date_type
        inv_date = date_type.fromisoformat(date_str)
    except ValueError:
        from datetime import date as date_type
        inv_date = date_type.today()

    taxable = Decimal(str(parsed.get("taxable_value") or 0))
    igst = Decimal(str(parsed.get("igst") or 0))
    cgst = Decimal(str(parsed.get("cgst") or 0))
    sgst = Decimal(str(parsed.get("sgst") or 0))
    cess = Decimal(str(parsed.get("cess") or 0))
    total_gst = igst + cgst + sgst

    if inv_type == "sales":
        inv = OutwardInvoice(
            business_id=business_id,
            period=period,
            invoice_number=parsed.get("invoice_number") or "WA-UPLOAD",
            invoice_date=inv_date,
            customer_name=parsed.get("vendor_name") or "Unknown",
            customer_gstin=parsed.get("supplier_gstin"),
            place_of_supply="27",
            invoice_type=InvoiceType.B2B if parsed.get("supplier_gstin") else InvoiceType.B2C_SMALL,
            taxable_value=taxable,
            igst=igst,
            cgst=cgst,
            sgst=sgst,
            cess=cess,
            source=InvoiceSource.OCR_UPLOAD,
        )
    else:
        inv = InwardInvoice(
            business_id=business_id,
            period=period,
            supplier_name=parsed.get("vendor_name") or "Unknown",
            supplier_gstin=parsed.get("supplier_gstin"),
            invoice_number=parsed.get("invoice_number") or "WA-UPLOAD",
            invoice_date=inv_date,
            taxable_value=taxable,
            igst=igst,
            cgst=cgst,
            sgst=sgst,
            source="whatsapp_upload",
        )

    db.add(inv)
    await db.commit()

    return (
        f"✅ Invoice saved!\n"
        f"*{parsed.get('vendor_name', 'Vendor')}*\n"
        f"#{parsed.get('invoice_number', '')} · {date_str}\n"
        f"Taxable: ₹{taxable:,.2f}\n"
        f"GST: ₹{total_gst:,.2f}\n"
        f"Saved as {'sale' if inv_type == 'sales' else 'purchase'} for {period}."
    )


async def _upsert_session(
    user: User,
    wa_number: str,
    awaiting: str | None,
    payload: dict | None,
    db: AsyncSession,
) -> None:
    existing = await db.scalar(
        select(WhatsAppSession).where(WhatsAppSession.wa_number == wa_number)
    )
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    if existing:
        existing.awaiting = awaiting
        existing.payload = payload
        existing.expires_at = expires
    else:
        db.add(WhatsAppSession(
            user_id=user.id,
            wa_number=wa_number,
            awaiting=awaiting,
            payload=payload,
            expires_at=expires,
        ))
    await db.commit()


async def handle_message(
    user: User,
    message: dict,
    msg_type: str,
    session: WhatsAppSession | None,
    db: AsyncSession,
) -> str:
    from_number = message["from"]

    # ── Session: awaiting upload type selection ───────────────────────────────
    if session and session.awaiting == "upload_type":
        text = (message.get("text") or {}).get("body", "").strip().lower()
        if text in {"1", "purchase", "inward"}:
            inv_type = "purchase"
        elif text in {"2", "sales", "sale", "outward"}:
            inv_type = "sales"
        else:
            return "Reply *1* for Purchase or *2* for Sales."

        media_id = (session.payload or {}).get("media_id")
        mime_type = (session.payload or {}).get("mime_type", "image/jpeg")
        if not media_id:
            await _upsert_session(user, from_number, None, None, db)
            return "Session expired. Please send the invoice again."

        try:
            file_bytes = await download_media(media_id)
        except Exception:
            await _upsert_session(user, from_number, None, None, db)
            return "Couldn't download your file. Please try again."

        parsed = await _parse_invoice_bytes(file_bytes, mime_type)
        if not parsed:
            await _upsert_session(user, from_number, None, None, db)
            return "Couldn't read this invoice. Try a clearer photo or PDF."

        business = await db.scalar(select(Business).where(Business.user_id == user.id))
        if not business:
            return "No business registered. Set up your GSTIN at bemyca.in"

        await _upsert_session(user, from_number, None, None, db)
        return await _save_invoice(inv_type, parsed, business.id, db)

    # ── Incoming media (document or image) ────────────────────────────────────
    if msg_type in ("document", "image"):
        doc = message.get("document") or message.get("image") or {}
        media_id = doc.get("id")
        mime_type = doc.get("mime_type", "image/jpeg")

        if msg_type == "image":
            await _upsert_session(user, from_number, "upload_type", {"media_id": media_id, "mime_type": mime_type}, db)
            return "Got your image! Is this a:\n*1* — Purchase invoice (you received it)\n*2* — Sales invoice (you issued it)"

        # Documents (PDF): try to infer from file name
        filename = doc.get("filename", "")
        await _upsert_session(user, from_number, "upload_type", {"media_id": media_id, "mime_type": mime_type}, db)
        return f"Got *{filename or 'document'}*! Is this a:\n*1* — Purchase invoice\n*2* — Sales invoice"

    # ── Text messages ─────────────────────────────────────────────────────────
    text = (message.get("text") or {}).get("body", "")
    intent = await parse_intent(text)

    if intent == "help":
        return HELP_TEXT

    if intent == "filing_status":
        return await _get_filing_status(user, db)

    # Fallback: Claude concierge
    return await chat_concierge(text)
