import os
import base64
from groq import AsyncGroq
from zenith_ai_bot.prompts import ZENITH_SYSTEM_PROMPT
from zenith_ai_bot.search import perform_web_search
from zenith_ai_bot.youtube import get_youtube_transcript
from core.logger import setup_logger

logger = setup_logger("LLM_ENGINE")

async def transcribe_voice(file_path: str) -> str:
    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    try:
        with open(file_path, "rb") as file:
            transcription = await client.audio.transcriptions.create(
                file=(os.path.basename(file_path), file.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
            )
        if len(transcription.split()) < 3:
            return "ERROR:GIBBERISH"
        return transcription
    except Exception as e:
        logger.error(f"Whisper API Error: {e}")
        return "ERROR:API_FAIL"

async def process_ai_query(user_text: str, image_bytes: bytes = None, context_data: str = None) -> str:
    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    
    external_context = ""
    # Bug Fix: Properly checks standard YouTube URLs
    if "youtube.com/watch" in user_text or "youtu.be/" in user_text:
        transcript = await get_youtube_transcript(user_text)
        if transcript: external_context = f"\n\n[YOUTUBE TRANSCRIPT]\n{transcript}"
    elif any(keyword in user_text.lower() for keyword in ["today", "current", "news", "price", "latest"]):
        search_results = await perform_web_search(user_text)
        if search_results: external_context = f"\n\n[LIVE WEB DATA]\n{search_results}\nCite your sources using HTML <a href>."

    final_context = ""
    if context_data:
        short_context = context_data[:2000] + "..." if len(context_data) > 2000 else context_data
        final_context += f"\n\n[PROVIDED CONTEXT/FILE DATA]\n{short_context}"
    
    final_prompt = f"{user_text}{final_context}{external_context}"
    
    model_name = "llama-3.1-8b-instant" 
    content_payload = [{"type": "text", "text": final_prompt}]
    
    if image_bytes:
        model_name = "llama-3.2-90b-vision-preview"
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        content_payload.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })

    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": ZENITH_SYSTEM_PROMPT},
                {"role": "user", "content": content_payload}
            ],
            model=model_name, temperature=0.3, max_tokens=2048
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        return "📡 Connection to AI servers lost. Please try again."