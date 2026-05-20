import httpx
from app.core.config import settings

GRAPH_API = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}"


async def send_text(to: str, text: str) -> None:
    if settings.WHATSAPP_TOKEN == "mock":
        print(f"[MOCK WhatsApp] To:{to} | {text[:120]}")
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GRAPH_API}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text},
            },
        )


async def send_template(to: str, template_name: str, lang: str = "en", components: list | None = None) -> None:
    if settings.WHATSAPP_TOKEN == "mock":
        print(f"[MOCK WhatsApp] Template:{template_name} To:{to} Components:{components}")
        return
    payload: dict = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {"name": template_name, "language": {"code": lang}},
    }
    if components:
        payload["template"]["components"] = components
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GRAPH_API}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            json=payload,
        )


async def download_media(media_id: str) -> bytes:
    async with httpx.AsyncClient() as client:
        # Step 1: get media URL
        r = await client.get(
            f"https://graph.facebook.com/v18.0/{media_id}",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
        )
        r.raise_for_status()
        url = r.json()["url"]
        # Step 2: download
        r2 = await client.get(url, headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"})
        r2.raise_for_status()
        return r2.content
