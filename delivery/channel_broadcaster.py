import asyncio
import logging
from telegram.error import RetryAfter, TimedOut, NetworkError

from bot.telegram_app import get_bot
from core.config import CHANNEL_ID

logger = logging.getLogger("CHANNEL_BROADCAST")

BASE_DELAY = 1.0
MAX_DELAY = 10.0
MAX_RETRIES = 5  # Stop trying to send a specific message after 5 fails

async def broadcast_channel(messages):
    bot = get_bot()

    if not messages:
        return

    delay = BASE_DELAY
    sent = 0

    for msg in messages:
        retries = 0
        
        while True:
            try:
                if retries >= MAX_RETRIES:
                    logger.error(f"DROPPING MESSAGE after {MAX_RETRIES} fails")
                    break

                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=msg,
                    disable_web_page_preview=True
                )

                sent += 1
                delay = max(BASE_DELAY, delay * 0.9) # Recover speed
                await asyncio.sleep(delay)
                break

            except RetryAfter as e:
                wait = int(e.retry_after)
                logger.warning(f"Flood wait {wait}s")
                await asyncio.sleep(wait)
                # Do not increment retries for FloodWait, just wait it out

            except (TimedOut, NetworkError):
                retries += 1
                delay = min(MAX_DELAY, delay + 1.0)
                logger.warning(f"Network retry {retries}/{MAX_RETRIES} | delay {delay}s")
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Critical Send Fail: {e}")
                break

    logger.info(f"CHANNEL SENT {sent}/{len(messages)}")