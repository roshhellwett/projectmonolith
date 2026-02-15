import re
import asyncio
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from core.logger import setup_logger

logger = setup_logger("YOUTUBE_TOOL")

def extract_yt_video_id(url: str) -> str | None:
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

def _fetch_transcript_sync(video_id: str) -> str | None:
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        formatter = TextFormatter()
        text = formatter.format_transcript(transcript)
        
        words = text.split()
        if len(words) > 1000:
            return " ".join(words[:1000]) + "\n\n[Transcript truncated to save tokens]"
        return text
    except Exception as e:
        logger.warning(f"Failed to fetch transcript for {video_id}: {e}")
        return None

async def get_youtube_transcript(url: str) -> str | None:
    video_id = extract_yt_video_id(url)
    if not video_id:
        return None
    return await asyncio.to_thread(_fetch_transcript_sync, video_id)