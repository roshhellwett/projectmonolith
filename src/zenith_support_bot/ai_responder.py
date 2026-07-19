from groq import AsyncGroq

from core.circuit_breaker import get_breaker
from core.logger import setup_logger
from core.secrets import get_groq_api_key

logger = setup_logger("SUPPORT_AI")
_groq_client: AsyncGroq | None = None

SUPPORT_SYSTEM_PROMPT = """You are Zenith Support AI, a helpful customer support assistant. Your role is to provide instant, accurate, and friendly responses to user support inquiries.

Guidelines:
1. Be concise and professional in all responses
2. Provide step-by-step solutions when applicable
3. If you don't have enough information, ask clarifying questions
4. For technical issues, gather relevant details (error messages, steps to reproduce)
5. Always be polite and empathetic
6. If a ticket requires human intervention, suggest contacting support
7. Use markdown formatting for clarity (bold, lists, code blocks)
8. Keep responses under 500 words unless detailed troubleshooting is needed

You have access to general troubleshooting knowledge for common issues. For complex or specific technical problems, provide initial guidance and suggest creating a support ticket."""


def get_groq_client() -> AsyncGroq | None:
    api_key = get_groq_api_key(prefer_support=True)
    if not api_key:
        return None
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=api_key, max_retries=2, timeout=30.0)
    return _groq_client


async def generate_ai_response(subject: str, description: str) -> str:
    client = get_groq_client()
    if not client:
        return "Thank you for your ticket! Our support team will review it shortly."

    breaker = get_breaker("groq")
    if not breaker.can_execute():
        return "Thank you for your ticket! Our support team will review it shortly. (AI auto-response temporarily busy)"

    prompt = f"""Support Ticket:
Subject: {subject}
Description: {description}

Please provide a helpful, step-by-step solution to address this support inquiry. If this requires human attention, briefly explain and provide initial guidance."""

    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": SUPPORT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.4,
            max_tokens=1024,
        )
        breaker.record_success()
        return response.choices[0].message.content
    except Exception as e:
        breaker.record_failure()
        logger.error(f"Groq AI Response Error: {e}")
        return "Thank you for your ticket! Our support team will review it shortly. For urgent issues, please describe your problem in more detail."


async def generate_faq_answer(question: str, faq_context: str = None) -> str:
    client = get_groq_client()
    if not client:
        return None

    breaker = get_breaker("groq")
    if not breaker.can_execute():
        return None

    context = f"Relevant FAQ entries:\n{faq_context}\n\n" if faq_context else ""
    prompt = f"""{context}User Question: {question}

Provide a helpful answer based on the FAQ entries above. If the question isn't directly answered by the FAQs, provide a general helpful response."""

    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": SUPPORT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=512,
        )
        breaker.record_success()
        return response.choices[0].message.content
    except Exception as e:
        breaker.record_failure()
        logger.error(f"Groq FAQ Answer Error: {e}")
        return None
