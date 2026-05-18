"""
Claude AI service for natural language tax explanations and WhatsApp concierge.
"""
from app.core.config import settings

SYSTEM_PROMPT = """You are BeMyCa's Tax Concierge — an expert in Indian tax law (GST & Income Tax).
You explain tax concepts in simple, non-technical Hindi-English (Hinglish is fine).
You never give advice that requires a CA signature. You always add: "Consult your CA for final decisions."
Keep responses under 200 words. Be friendly, direct, helpful."""


async def explain_invoice(ocr_data: dict) -> str:
    if settings.ANTHROPIC_API_KEY == "mock":
        return (
            f"This invoice from {ocr_data.get('vendor_name', 'the vendor')} "
            f"is for ₹{ocr_data.get('taxable_value', 0):,.0f} + "
            f"₹{(ocr_data.get('cgst', 0) + ocr_data.get('igst', 0)):,.0f} GST. "
            "If you're GST registered, you can claim this as Input Tax Credit (ITC). "
            "Consult your CA for final decisions."
        )

    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Explain this invoice in simple terms: {ocr_data}",
        }],
    )
    return message.content[0].text


async def explain_risk_factor(factor: dict) -> str:
    if settings.ANTHROPIC_API_KEY == "mock":
        return f"[MOCK] Risk explanation for {factor['factor']}: {factor['description']}"

    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Explain this tax risk in simple English and what action to take: {factor}",
        }],
    )
    return message.content[0].text


async def chat_concierge(user_message: str, context: dict | None = None) -> str:
    if settings.ANTHROPIC_API_KEY == "mock":
        return f"[MOCK] Tax Concierge response to: {user_message[:50]}..."

    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    messages = []
    if context:
        messages.append({"role": "user", "content": f"My tax context: {context}"})
        messages.append({"role": "assistant", "content": "I have your tax context. How can I help?"})
    messages.append({"role": "user", "content": user_message})

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return message.content[0].text
