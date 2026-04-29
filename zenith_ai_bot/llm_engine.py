from typing import Optional
from groq import AsyncGroq
from zenith_ai_bot.prompts import PERSONAS, RESEARCH_PROMPT, SUMMARIZE_PROMPT, CODE_PROMPT, IMAGINE_PROMPT
from zenith_ai_bot.search import perform_web_search, perform_deep_research
from zenith_ai_bot.youtube import get_youtube_transcript
from core.config import GROQ_API_KEY
from core.logger import setup_logger

logger = setup_logger("LLM_ENGINE")
_groq_client: Optional[AsyncGroq] = None


def get_groq_client() -> AsyncGroq:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=GROQ_API_KEY, max_retries=2)
    return _groq_client


async def process_ai_query(user_text: str, context_data: str = None,
                           persona: str = "default", max_tokens: int = 1024,
                           history: list = None) -> str:
    client = get_groq_client()
    external_context = ""

    if "youtube.com/watch" in user_text or "youtu.be/" in user_text:
        transcript = await get_youtube_transcript(user_text)
        if transcript:
            external_context = f"\n\n[YOUTUBE TRANSCRIPT]\n{transcript}"
    elif any(kw in user_text.lower() for kw in ["today", "current", "news", "price", "latest", "search"]):
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

    try:
        response = await client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        return "📡 Connection to AI servers lost. Please try again."


async def process_research(topic: str) -> str:
    client = get_groq_client()
    research_data = await perform_deep_research(topic)
    if not research_data:
        return "⚠️ No research data found for this topic. Try a different query."

    prompt = f"Research Topic: {topic}\n\n[RESEARCH DATA]\n{research_data}"

    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": RESEARCH_PROMPT},
                {"role": "user", "content": prompt},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=4096,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Research mode error: {e}")
        return "📡 Research engine connection lost. Please try again."


async def process_summarize(text: str) -> str:
    client = get_groq_client()
    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": SUMMARIZE_PROMPT},
                {"role": "user", "content": f"Summarize this:\n\n{text}"},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Summarize error: {e}")
        return "📡 Summarization engine offline. Please try again."


async def process_code(description: str) -> str:
    client = get_groq_client()
    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": CODE_PROMPT},
                {"role": "user", "content": description},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=4096,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Code gen error: {e}")
        return "📡 Code generation engine offline. Please try again."


async def process_imagine(description: str) -> str:
    client = get_groq_client()
    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": IMAGINE_PROMPT},
                {"role": "user", "content": f"Create image generation prompts for: {description}"},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Imagine error: {e}")
        return "📡 Image prompt engine offline. Please try again."