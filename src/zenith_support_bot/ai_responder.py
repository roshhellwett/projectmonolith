from core.llm_fallback import AIExecutionEngine
from core.logger import setup_logger
from core.secrets import get_groq_api_key
from zenith_ai_bot.utils import sanitize_telegram_html

logger = setup_logger("SUPPORT_AI")

SUPPORT_SYSTEM_PROMPT = """You are Zenith Support AI, a highly intelligent and empathetic customer support engineering assistant. Your role is to provide instant, accurate, and friendly technical solutions to user inquiries.

Guidelines:
1. Be concise, professional, and clear in all responses.
2. Provide step-by-step technical solutions when applicable.
3. If you don't have enough information, ask targeted clarifying questions.
4. For technical issues, gather relevant details (error codes, steps to reproduce, device details).
5. Always be warm, polite, and empathetic.
6. If a ticket requires human engineering intervention, clearly state that our engineering team will investigate.
7. Format responses cleanly using HTML tags (<b>bold</b>, <code>code</code>, bullet points). Do not use markdown like **bold**.
8. Keep responses well-structured and concise.

You have access to general troubleshooting knowledge for common issues. For complex or specific technical problems, provide initial guidance and assure the user that the engineering team is on it."""


async def generate_ai_response(subject: str, description: str, preferred_model: str = "llama-3.3-70b-versatile") -> str:
    api_key = get_groq_api_key(prefer_support=True)
    if not api_key:
        return "Thank you for your ticket! Our support team will review it shortly."

    prompt = f"""Support Ticket:
Subject: {subject}
Description: {description}

Please provide a helpful, step-by-step solution to address this support inquiry. If this requires human attention, briefly explain and provide initial guidance."""

    try:
        resp = await AIExecutionEngine.execute(
            messages=[
                {"role": "system", "content": SUPPORT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            api_key=api_key,
            preferred_model=preferred_model,
            temperature=0.4,
            max_tokens=1024,
        )
        if resp.is_error:
            logger.warning(f"Support AI execution failed: {resp.error_type} ({resp.error_message})")
            return "Thank you for your ticket! Our support team will review it shortly. For urgent issues, please describe your problem in more detail."
        return sanitize_telegram_html(resp.content)
    except Exception as e:
        logger.error(f"Groq AI Response Error: {e}")
        return "Thank you for your ticket! Our support team will review it shortly. For urgent issues, please describe your problem in more detail."


async def generate_faq_answer(
    question: str, faq_context: str = None, preferred_model: str = "llama-3.3-70b-versatile"
) -> str:
    api_key = get_groq_api_key(prefer_support=True)
    if not api_key:
        return None

    context = f"Relevant FAQ entries:\n{faq_context}\n\n" if faq_context else ""
    prompt = f"""{context}User Question: {question}

Provide a helpful answer based on the FAQ entries above. If the question isn't directly answered by the FAQs, provide a general helpful response."""

    try:
        resp = await AIExecutionEngine.execute(
            messages=[
                {"role": "system", "content": SUPPORT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            api_key=api_key,
            preferred_model=preferred_model,
            temperature=0.3,
            max_tokens=512,
        )
        if resp.is_error:
            return None
        return sanitize_telegram_html(resp.content)
    except Exception as e:
        logger.error(f"Groq FAQ Answer Error: {e}")
        return None
