from core.config import AI_SEARCH_TRIGGERS
from core.llm_fallback import AIExecutionEngine
from core.logger import setup_logger
from zenith_ai_bot.prompts import CODE_PROMPT, IMAGINE_PROMPT, PERSONAS, RESEARCH_PROMPT, SUMMARIZE_PROMPT
from zenith_ai_bot.search import perform_deep_research, perform_web_search
from zenith_ai_bot.youtube import get_youtube_transcript

logger = setup_logger("LLM_ENGINE")


async def process_ai_query(
    user_text: str,
    context_data: str = None,
    persona: str = "default",
    max_tokens: int = 1024,
    history: list = None,
    api_key: str = None,
    preferred_model: str = "llama-3.3-70b-versatile",
) -> str:
    if not api_key:
        return "Your Groq API key is not set. Use /setkey to configure your key."
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

    resp = await AIExecutionEngine.execute(
        messages=messages,
        api_key=api_key,
        preferred_model=preferred_model,
        temperature=0.5,
        max_tokens=max_tokens,
    )
    return resp.get_formatted_content()


async def process_research(topic: str, api_key: str = None, preferred_model: str = "llama-3.3-70b-versatile") -> str:
    if not api_key:
        return "Your Groq API key is not set. Use /setkey to configure your key."
    research_data = await perform_deep_research(topic)
    if not research_data:
        return "No research data found for this topic. Try a different query."

    prompt = f"Research Topic: {topic}\n\n[RESEARCH DATA]\n{research_data}"

    resp = await AIExecutionEngine.execute(
        messages=[
            {"role": "system", "content": RESEARCH_PROMPT},
            {"role": "user", "content": prompt},
        ],
        api_key=api_key,
        preferred_model=preferred_model,
        temperature=0.3,
        max_tokens=4096,
    )
    return resp.get_formatted_content()


async def process_summarize(text: str, api_key: str = None, preferred_model: str = "llama-3.3-70b-versatile") -> str:
    if not api_key:
        return "Your Groq API key is not set. Use /setkey to configure your key."
    resp = await AIExecutionEngine.execute(
        messages=[
            {"role": "system", "content": SUMMARIZE_PROMPT},
            {"role": "user", "content": f"Summarize this:\n\n{text}"},
        ],
        api_key=api_key,
        preferred_model=preferred_model,
        temperature=0.3,
        max_tokens=2048,
    )
    return resp.get_formatted_content()


async def process_code(description: str, api_key: str = None, preferred_model: str = "llama-3.3-70b-versatile") -> str:
    if not api_key:
        return "Your Groq API key is not set. Use /setkey to configure your key."
    resp = await AIExecutionEngine.execute(
        messages=[
            {"role": "system", "content": CODE_PROMPT},
            {"role": "user", "content": description},
        ],
        api_key=api_key,
        preferred_model=preferred_model,
        temperature=0.2,
        max_tokens=4096,
    )
    return resp.get_formatted_content()


async def process_imagine(
    description: str, api_key: str = None, preferred_model: str = "llama-3.3-70b-versatile"
) -> str:
    if not api_key:
        return "Your Groq API key is not set. Use /setkey to configure your key."
    resp = await AIExecutionEngine.execute(
        messages=[
            {"role": "system", "content": IMAGINE_PROMPT},
            {"role": "user", "content": f"Create image generation prompts for: {description}"},
        ],
        api_key=api_key,
        preferred_model=preferred_model,
        temperature=0.7,
        max_tokens=2048,
    )
    return resp.get_formatted_content()
