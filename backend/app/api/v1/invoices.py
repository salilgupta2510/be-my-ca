import asyncio
import base64
import json
import random
import string
import uuid
from datetime import date
from decimal import Decimal

import anthropic
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.config import settings
from app.core.database import get_db
from app.models.business import Business
from app.models.invoice import OutwardInvoice, InwardInvoice, InvoiceSource, InvoiceType
from app.models.user import User
from app.services.rcm_engine import classify_inward_invoice
from app.services.itc_monitor import check_itc_expiry_at_create
from app.schemas.invoice import (
    OutwardInvoiceCreate, OutwardInvoiceUpdate, OutwardInvoiceOut,
    InwardInvoiceCreate, InwardInvoiceUpdate, InwardInvoiceOut,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/invoices", tags=["invoices"])


async def _get_business(db: AsyncSession, user: User) -> Business:
    business = await db.scalar(select(Business).where(Business.user_id == user.id))
    if not business:
        raise HTTPException(404, "Complete onboarding to register your business first.")
    return business


# ─── Outward Invoices (Sales) ─────────────────────────────────────────────────

@router.get("/outward", response_model=list[OutwardInvoiceOut])
async def list_outward(
    period: str = Query(..., examples=["2025-01"]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    records = await db.scalars(
        select(OutwardInvoice)
        .where(OutwardInvoice.business_id == business.id, OutwardInvoice.period == period)
        .order_by(OutwardInvoice.invoice_date)
    )
    return records.all()


@router.post("/outward", response_model=OutwardInvoiceOut, status_code=201)
async def create_outward(
    body: OutwardInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    inv = OutwardInvoice(id=uuid.uuid4(), business_id=business.id, source=InvoiceSource.MANUAL, **body.model_dump())
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


OCR_PROMPT = """You are an Indian GST invoice parser. Extract all fields from this invoice image.

Return ONLY valid JSON with exactly these keys (no extra text, no markdown):
{
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "customer_name": "string or null",
  "customer_gstin": "15-char GSTIN or null",
  "place_of_supply": "2-digit state code string or null",
  "invoice_type": "B2B or B2C_SMALL or B2C_LARGE or EXPORT or CREDIT_NOTE",
  "taxable_value": number,
  "igst": number,
  "cgst": number,
  "sgst": number,
  "cess": number
}

Rules:
- invoice_type is B2B if customer_gstin is present, else B2C_SMALL
- All tax amounts must be numbers (0 if not found)
- taxable_value is total before tax
- place_of_supply: 2-digit code from GSTIN first 2 chars, or infer from state name (e.g. Maharashtra=27, Delhi=07, Karnataka=29, Haryana=06)
"""


async def _extract_with_claude(image_bytes: bytes, media_type: str) -> dict:
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    msg = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": OCR_PROMPT},
            ],
        }],
    )
    text = msg.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


@router.post("/outward/upload")
async def upload_outward_image(
    period: str = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    image_bytes = await file.read()

    # Determine media type
    content_type = file.content_type or "image/jpeg"
    if content_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        content_type = "image/jpeg"

    extracted: dict = {}
    use_real_ocr = settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY != "mock"

    if use_real_ocr:
        try:
            extracted = await _extract_with_claude(image_bytes, content_type)
        except Exception as e:
            # Fall through to mock on any failure
            extracted = {}

    suffix = "".join(random.choices(string.digits, k=4))

    def _d(val, default="0") -> Decimal:
        try:
            return Decimal(str(val)) if val not in (None, "") else Decimal(default)
        except Exception:
            return Decimal(default)

    def _inv_type(val: str | None) -> InvoiceType:
        try:
            return InvoiceType[val] if val else InvoiceType.B2C_SMALL
        except KeyError:
            return InvoiceType.B2C_SMALL

    invoice_date_val = date.today()
    if extracted.get("invoice_date"):
        try:
            invoice_date_val = date.fromisoformat(extracted["invoice_date"])
        except ValueError:
            pass

    draft = OutwardInvoice(
        id=uuid.uuid4(),
        business_id=business.id,
        period=period,
        invoice_number=extracted.get("invoice_number") or f"OCR-{suffix}",
        invoice_date=invoice_date_val,
        customer_name=extracted.get("customer_name") or "Unknown Customer",
        customer_gstin=extracted.get("customer_gstin") or None,
        place_of_supply=extracted.get("place_of_supply") or business.state_code,
        invoice_type=_inv_type(extracted.get("invoice_type")),
        taxable_value=_d(extracted.get("taxable_value")),
        igst=_d(extracted.get("igst")),
        cgst=_d(extracted.get("cgst")),
        sgst=_d(extracted.get("sgst")),
        cess=_d(extracted.get("cess")),
        source=InvoiceSource.OCR_UPLOAD,
        raw_image_url=f"uploads/{file.filename}",
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return {
        "draft_id": str(draft.id),
        "ocr_used": use_real_ocr and bool(extracted),
        "extracted": {
            "invoice_number": draft.invoice_number,
            "invoice_date": draft.invoice_date.isoformat(),
            "customer_name": draft.customer_name,
            "customer_gstin": draft.customer_gstin,
            "place_of_supply": draft.place_of_supply,
            "invoice_type": draft.invoice_type.value,
            "taxable_value": str(draft.taxable_value),
            "igst": str(draft.igst),
            "cgst": str(draft.cgst),
            "sgst": str(draft.sgst),
            "cess": str(draft.cess),
        },
        "message": "Review and confirm the extracted values." if use_real_ocr else "OCR not configured — values pre-filled. Edit before saving.",
    }


@router.put("/outward/{invoice_id}", response_model=OutwardInvoiceOut)
async def update_outward(
    invoice_id: str,
    body: OutwardInvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    inv = await db.get(OutwardInvoice, uuid.UUID(invoice_id))
    if not inv or inv.business_id != business.id:
        raise HTTPException(404, "Invoice not found")

    for field, value in body.model_dump().items():
        setattr(inv, field, value)
    await db.commit()
    await db.refresh(inv)
    return inv


@router.delete("/outward/{invoice_id}", status_code=204)
async def delete_outward(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    inv = await db.get(OutwardInvoice, uuid.UUID(invoice_id))
    if not inv or inv.business_id != business.id:
        raise HTTPException(404, "Invoice not found")
    await db.delete(inv)
    await db.commit()


# ─── Inward Invoices (Purchases) ─────────────────────────────────────────────

@router.get("/inward", response_model=list[InwardInvoiceOut])
async def list_inward(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    records = await db.scalars(
        select(InwardInvoice)
        .where(InwardInvoice.business_id == business.id, InwardInvoice.period == period)
        .order_by(InwardInvoice.invoice_date)
    )
    return records.all()


@router.post("/inward", response_model=InwardInvoiceOut, status_code=201)
async def create_inward(
    body: InwardInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    data = body.model_dump()

    # Auto-classify RCM and Section 17(5) blocks unless caller already set them
    if not data.get("is_rcm") and not data.get("itc_blocked_reason"):
        rcm = classify_inward_invoice(
            supplier_gstin=data.get("supplier_gstin"),
            hsn_code=data.get("hsn_code"),
            supplier_name=data["supplier_name"],
        )
        data["is_rcm"] = rcm.is_rcm
        if rcm.itc_blocked_reason:
            data["itc_blocked_reason"] = rcm.itc_blocked_reason

    # Check ITC time-bar at creation — mark lapsed immediately if overdue
    lapse_reason = check_itc_expiry_at_create(data["invoice_date"])
    if lapse_reason and not data.get("itc_blocked_reason"):
        data["itc_blocked_reason"] = lapse_reason

    inv = InwardInvoice(id=uuid.uuid4(), business_id=business.id, **data)
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


@router.put("/inward/{invoice_id}", response_model=InwardInvoiceOut)
async def update_inward(
    invoice_id: str,
    body: InwardInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    inv = await db.get(InwardInvoice, uuid.UUID(invoice_id))
    if not inv or inv.business_id != business.id:
        raise HTTPException(404, "Invoice not found")

    for field, value in body.model_dump().items():
        setattr(inv, field, value)
    await db.commit()
    await db.refresh(inv)
    return inv


@router.delete("/inward/{invoice_id}", status_code=204)
async def delete_inward(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = await _get_business(db, current_user)
    inv = await db.get(InwardInvoice, uuid.UUID(invoice_id))
    if not inv or inv.business_id != business.id:
        raise HTTPException(404, "Invoice not found")
    await db.delete(inv)
    await db.commit()
