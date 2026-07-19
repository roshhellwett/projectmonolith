from groq import AsyncGroq

from core.circuit_breaker import get_breaker
from core.config import AI_SEARCH_TRIGGERS
from core.logger import setup_logger
from zenith_ai_bot.prompts import CODE_PROMPT, IMAGINE_PROMPT, PERSONAS, RESEARCH_PROMPT, SUMMARIZE_PROMPT
from zenith_ai_bot.search import perform_deep_research, perform_web_search
from zenith_ai_bot.youtube import get_youtube_transcript

logger = setup_logger("LLM_ENGINE")


def get_groq_client(api_key: str) -> AsyncGroq:
    return AsyncGroq(api_key=api_key, max_retries=2, timeout=30.0)


async def _call_groq_with_breaker(client: AsyncGroq, **kwargs) -> str:
    breaker = get_breaker("groq")
    if not breaker.can_execute():
        return "⚠️ AI service is momentarily unavailable due to high demand. Please try again in 1-2 minutes."
    try:
        response = await client.chat.completions.create(**kwargs)
        breaker.record_success()
        return response.choices[0].message.content
    except Exception as e:
        breaker.record_failure()
        error_str = str(e).lower()
        if "rate_limit" in error_str or "429" in error_str:
            logger.warning(f"Groq API rate limit hit: {e}")
            return "⏳ AI service limit temporarily reached. Please try again in a few seconds."
        elif "timeout" in error_str:
            logger.warning(f"Groq API timeout: {e}")
            return "⏱️ AI generation took too long to respond. Please try a simpler prompt or try again."
        else:
            logger.error(f"Groq API error: {e}")
            return "❌ AI engine encountered an unexpected issue. Please try again."


async def process_ai_query(
    user_text: str,
    context_data: str = None,
    persona: str = "default",
    max_tokens: int = 1024,
    history: list = None,
    api_key: str = None,
) -> str:
    if not api_key:
        return "Your Groq API key is not set. Use /setkey in the Crypto Bot to configure it."
    client = get_groq_client(api_key)
    external_context = ""

    if "youtube.com/watch" in user_text or "youtu.be/" in user_text:
        transcript = await get_youtube_transcript(user_text)
        if transcript:
            external_context = f"\n\n[YOUTUBE TRANSCRIPT]\n{transcript}"
    elif any(kw in user_text.lower() for kw in AI_SEARCH_TRIGGERS):
        search_results = await perform_web_search(user_text)
        if search_results:
            external_context = f"\n\n[LIVE WEB DATA]\n{search_results}\nCite your sources using HTML <a href>."

    final_context = ""
    if context_data:
        short_context = context_data[:2000] + "..." if len(context_data) > 2000 else context_data
        final_context += f"\n\n[CONVERSATION CONTEXT]\n{short_context}"

    final_prompt = f"{user_text}{final_context}{external_context}"

    persona_data = PERSONAS.get(persona, PERSONAS["default"])
    messages = [{"role": "system", "content": persona_data["prompt"]}]

    if history:
        for msg in history[-10:]:
            messages.append({"role": msg.role, "content": msg.content[:1000]})

    messages.append({"role": "user", "content": final_prompt})

    return await _call_groq_with_breaker(
        client,
        messages=messages,
        model="llama-3.3-70b-versatile",
        temperature=0.5,
        max_tokens=max_tokens,
    )


async def process_research(topic: str, api_key: str = None) -> str:
    if not api_key:
        return "Your Groq API key is not set. Use /setkey in the Crypto Bot to configure it."
    client = get_groq_client(api_key)
    research_data = await perform_deep_research(topic)
    if not research_data:
        return "No research data found for this topic. Try a different query."

    prompt = f"Research Topic: {topic}\n\n[RESEARCH DATA]\n{research_data}"

    return await _call_groq_with_breaker(
        client,
        messages=[
            {"role": "system", "content": RESEARCH_PROMPT},
            {"role": "user", "content": prompt},
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        max_tokens=4096,
    )


async def process_summarize(text: str, api_key: str = None) -> str:
    if not api_key:
        return "Your Groq API key is not set. Use /setkey in the Crypto Bot to configure it."
    client = get_groq_client(api_key)
    return await _call_groq_with_breaker(
        client,
        messages=[
            {"role": "system", "content": SUMMARIZE_PROMPT},
            {"role": "user", "content": f"Summarize this:\n\n{text}"},
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        max_tokens=2048,
    )


async def process_code(description: str, api_key: str = None) -> str:
    if not api_key:
        return "Your Groq API key is not set. Use /setkey in the Crypto Bot to configure it."
    client = get_groq_client(api_key)
    return await _call_groq_with_breaker(
        client,
        messages=[
            {"role": "system", "content": CODE_PROMPT},
            {"role": "user", "content": description},
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        max_tokens=4096,
    )


async def process_imagine(description: str, api_key: str = None) -> str:
    if not api_key:
        return "Your Groq API key is not set. Use /setkey in the Crypto Bot to configure it."
    client = get_groq_client(api_key)
    return await _call_groq_with_breaker(
        client,
        messages=[
            {"role": "system", "content": IMAGINE_PROMPT},
            {"role": "user", "content": f"Create image generation prompts for: {description}"},
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        max_tokens=2048,
    )
