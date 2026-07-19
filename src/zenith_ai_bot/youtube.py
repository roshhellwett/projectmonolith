import asyncio
import re

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from core.logger import setup_logger

logger = setup_logger("YOUTUBE_TOOL")


def extract_yt_video_id(url: str) -> str | None:
    if not url:
        return None
    match = re.search(r"(?:(?:v|embed|shorts|live)=?\/|v=)([0-9A-Za-z_-]{11})|\/([0-9A-Za-z_-]{11})(?:\?|&|$)", url)
    if match:
        return match.group(1) or match.group(2)
    return None


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
