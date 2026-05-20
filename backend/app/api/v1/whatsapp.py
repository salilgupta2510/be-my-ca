import hashlib
import os
import secrets
import tempfile
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.gst_return import GSTReturn
from app.models.user import User
from app.models.whatsapp import WhatsAppAlertLog, WhatsAppOTP, WhatsAppSession
from app.services.whatsapp_bot import handle_message
from app.services.whatsapp_client import send_template, send_text

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class SendOTPRequest(BaseModel):
    number: str  # E.164, e.g. +919876543210


class VerifyOTPRequest(BaseModel):
    number: str
    code: str


class PreferencesRequest(BaseModel):
    alerts_enabled: bool
    prefs: dict


# ── Webhook (Meta verification + incoming messages) ────────────────────────────

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    from app.core.config import settings
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(403, "Forbidden")


@router.post("/webhook")
async def receive_message(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    try:
        entry = body["entry"][0]
        value = entry["changes"][0]["value"]
        message = value["messages"][0]
        from_number = message["from"]
        msg_type = message["type"]
    except (KeyError, IndexError):
        return {"status": "no_message"}

    # Resolve user by verified WA number
    user = await db.scalar(
        select(User).where(User.whatsapp_number == from_number, User.whatsapp_verified == True)
    )
    if not user:
        await send_text(from_number, "Hi! Link your WhatsApp in the BeMyCa dashboard to get started.")
        return {"status": "unlinked"}

    # Load or clear stale session
    session = await db.scalar(
        select(WhatsAppSession).where(
            WhatsAppSession.wa_number == from_number,
            WhatsAppSession.expires_at > datetime.now(timezone.utc),
        )
    )

    reply = await handle_message(
        user=user, message=message, msg_type=msg_type,
        session=session, db=db,
    )

    if reply:
        await send_text(from_number, reply)

    return {"status": "processed"}


# ── OTP linking ────────────────────────────────────────────────────────────────

@router.post("/link/send-otp")
async def send_otp(
    body: SendOTPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    number = body.number.strip()
    if not number.startswith("+"):
        raise HTTPException(400, "Number must be in E.164 format e.g. +919876543210")

    # Check number not already claimed by another user
    existing = await db.scalar(
        select(User).where(User.whatsapp_number == number, User.id != current_user.id)
    )
    if existing:
        raise HTTPException(400, "Number already linked to another account")

    # Delete old OTPs for this user
    await db.execute(delete(WhatsAppOTP).where(WhatsAppOTP.user_id == current_user.id))

    code = f"{secrets.randbelow(1000000):06d}"
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    otp = WhatsAppOTP(
        user_id=current_user.id,
        number=number,
        code_hash=code_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(otp)
    await db.commit()

    # Send OTP via WhatsApp authentication template (auto-approved by Meta)
    # Template body must contain {{1}} = code. Falls back to plain text in mock mode.
    try:
        await send_template(
            to=number,
            template_name="bemyca_otp",
            components=[{"type": "body", "parameters": [{"type": "text", "text": code}]}],
        )
    except Exception:
        await send_text(number, f"Your BeMyCa verification code is: {code}\nValid for 10 minutes.")

    return {"message": "OTP sent"}


@router.post("/link/verify-otp")
async def verify_otp(
    body: VerifyOTPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    number = body.number.strip()
    code_hash = hashlib.sha256(body.code.strip().encode()).hexdigest()

    otp = await db.scalar(
        select(WhatsAppOTP).where(
            WhatsAppOTP.user_id == current_user.id,
            WhatsAppOTP.number == number,
            WhatsAppOTP.code_hash == code_hash,
            WhatsAppOTP.used == False,
            WhatsAppOTP.expires_at > datetime.now(timezone.utc),
        )
    )
    if not otp:
        raise HTTPException(400, "Invalid or expired OTP")

    otp.used = True
    current_user.whatsapp_number = number
    current_user.whatsapp_verified = True
    await db.commit()

    return {"message": "WhatsApp linked successfully", "number": number}


@router.post("/unlink")
async def unlink(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.whatsapp_number = None
    current_user.whatsapp_verified = False
    current_user.whatsapp_alerts_enabled = False
    await db.execute(delete(WhatsAppOTP).where(WhatsAppOTP.user_id == current_user.id))
    await db.execute(delete(WhatsAppSession).where(WhatsAppSession.user_id == current_user.id))
    await db.commit()
    return {"message": "WhatsApp unlinked"}


# ── Preferences ────────────────────────────────────────────────────────────────

@router.put("/preferences")
async def update_preferences(
    body: PreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.whatsapp_verified:
        raise HTTPException(400, "Link WhatsApp first")
    current_user.whatsapp_alerts_enabled = body.alerts_enabled
    current_user.whatsapp_alert_prefs = body.prefs
    await db.commit()
    return {"message": "Preferences updated"}


@router.get("/status")
async def get_status(current_user: User = Depends(get_current_user)):
    return {
        "linked": current_user.whatsapp_verified,
        "number": current_user.whatsapp_number,
        "alerts_enabled": current_user.whatsapp_alerts_enabled,
        "alert_prefs": current_user.whatsapp_alert_prefs or {"deadlines": True, "recon": True, "itc_expiry": True},
    }
