from core.config import AI_SEARCH_TRIGGERS
from core.llm_fallback import AIExecutionEngine
from core.logger import setup_logger
from zenith_ai_bot.prompts import CODE_PROMPT, IMAGINE_PROMPT, PERSONAS, RESEARCH_PROMPT, SUMMARIZE_PROMPT
from zenith_ai_bot.repository import UsageRepo
from zenith_ai_bot.search import perform_deep_research, perform_web_search
from zenith_ai_bot.youtube import get_youtube_transcript

logger = setup_logger("LLM_ENGINE")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Searches the live internet for recent news, facts, or data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_code_architecture",
            "description": "Generates complete, production-ready code architecture for a complex prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "The coding task description"}
                },
                "required": ["description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image_prompt",
            "description": "Crafts a high-quality visual prompt for image generation models like Midjourney.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "What to visualize"}
                },
                "required": ["description"]
            }
        }
    }
]



async def _check_and_record(user_id: int, query_text: str, response_text: str) -> tuple[bool, str]:
    """Check quota and record token usage. Returns (allowed, message)."""
    allowed, msg = await UsageRepo.check_quota(user_id)
    if not allowed:
        return False, msg
    estimated = len(query_text) // 4 + len(response_text) // 4
    await UsageRepo.record_tokens(user_id, max(1, estimated))
    return True, ""


async def process_ai_query(
    user_id: int,
    user_text: str,
    context_data: str = None,
    persona: str = "default",
    max_tokens: int = 1024,
    history: list = None,
    preferred_model: str = "llama-3.3-70b-versatile",
    api_key: str = None,
    image_base64: str = None,
) -> str:
    if not api_key:
        return "⚠️ AI service is not configured. Please use /setkey to connect your personal Groq API key."

    import re
    from zenith_ai_bot.search import scrape_url
    
    external_context = ""
    urls = re.findall(r'https?://[^\s<>"]+', user_text)

    if "youtube.com/watch" in user_text or "youtu.be/" in user_text:
        transcript = await get_youtube_transcript(user_text)
        if transcript:
            external_context = f"\n\n[YOUTUBE TRANSCRIPT]\n{transcript}"
    elif urls:
        scraped_text = await scrape_url(urls[0])
        if scraped_text:
            external_context = f"\n\n[WEBSITE CONTENT: {urls[0]}]\n{scraped_text}"
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

    if image_base64:
        messages.append({
            "role": "user", 
            "content": [
                {"type": "text", "text": final_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            ]
        })
        preferred_model = "llama-3.2-11b-vision-preview"
    else:
        messages.append({"role": "user", "content": final_prompt})

    resp = await AIExecutionEngine.execute(
        messages=messages,
        api_key=api_key,
        preferred_model=preferred_model,
        temperature=0.5,
        max_tokens=max_tokens,
        tools=TOOLS,
    )

    if resp.tool_calls:
        assistant_msg = {
            "role": "assistant",
            "content": resp.content,
            "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in resp.tool_calls]
        }
        messages.append(assistant_msg)
        
        import json
        for tc in resp.tool_calls:
            fn_name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except:
                args = {}
                
            if fn_name == "search_web":
                res = await perform_web_search(args.get("query", ""))
            elif fn_name == "generate_code_architecture":
                res = await process_code(user_id, args.get("description", ""), preferred_model, api_key)
            elif fn_name == "generate_image_prompt":
                res = await process_imagine(user_id, args.get("description", ""), preferred_model, api_key)
            else:
                res = "Tool not found."
            
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": fn_name,
                "content": res,
            })
        
        resp = await AIExecutionEngine.execute(
            messages=messages,
            api_key=api_key,
            preferred_model=preferred_model,
            temperature=0.5,
            max_tokens=max_tokens,
        )

    result = resp.get_formatted_content()
    await UsageRepo.record_tokens(user_id, len(user_text) // 4 + len(result) // 4)
    return result


async def process_research(user_id: int, topic: str, preferred_model: str = "llama-3.3-70b-versatile", api_key: str = None) -> str:
    if not api_key:
        return "⚠️ AI service is not configured. Please use /setkey to connect your personal Groq API key."

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
    result = resp.get_formatted_content()
    await UsageRepo.record_tokens(user_id, len(topic) // 4 + len(result) // 4)
    return result


async def process_summarize(user_id: int, text: str, preferred_model: str = "llama-3.3-70b-versatile", api_key: str = None) -> str:
    if not api_key:
        return "⚠️ AI service is not configured. Please use /setkey to connect your personal Groq API key."

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
    result = resp.get_formatted_content()
    await UsageRepo.record_tokens(user_id, len(text) // 4 + len(result) // 4)
    return result


async def process_code(user_id: int, description: str, preferred_model: str = "llama-3.3-70b-versatile", api_key: str = None) -> str:
    if not api_key:
        return "⚠️ AI service is not configured. Please use /setkey to connect your personal Groq API key."

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
    result = resp.get_formatted_content()
    await UsageRepo.record_tokens(user_id, len(description) // 4 + len(result) // 4)
    return result


async def process_imagine(user_id: int, description: str, preferred_model: str = "llama-3.3-70b-versatile", api_key: str = None) -> str:
    if not api_key:
        return "⚠️ AI service is not configured. Please use /setkey to connect your personal Groq API key."

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
    result = resp.get_formatted_content()
    await UsageRepo.record_tokens(user_id, len(description) // 4 + len(result) // 4)
    return result
