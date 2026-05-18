from fastapi import APIRouter, Request, Query, HTTPException
from app.core.config import settings
from app.services.ocr_service import parse_invoice_pdf
from app.services.claude_ai import explain_invoice, chat_concierge
import httpx

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

WHATSAPP_API = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(403, "Forbidden")


@router.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()

    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        message = value["messages"][0]
        from_number = message["from"]
        msg_type = message["type"]
    except (KeyError, IndexError):
        return {"status": "no_message"}

    reply_text = ""

    if msg_type == "text":
        user_text = message["text"]["body"]
        reply_text = await chat_concierge(user_text)

    elif msg_type == "document":
        doc = message["document"]
        # In production: download doc, parse, explain
        reply_text = (
            "Got your document! I'm analyzing it now. "
            "I'll send you the tax breakdown in a moment. "
            "Please wait 30 seconds."
        )

    elif msg_type == "image":
        reply_text = "Got your image. Please send invoices as PDF for best results."

    if reply_text:
        await _send_whatsapp_message(from_number, reply_text)

    return {"status": "processed"}


async def _send_whatsapp_message(to: str, text: str):
    if settings.WHATSAPP_TOKEN == "mock":
        print(f"[MOCK WhatsApp] To: {to} | Message: {text[:100]}")
        return

    async with httpx.AsyncClient() as client:
        await client.post(
            WHATSAPP_API,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text},
            },
        )
