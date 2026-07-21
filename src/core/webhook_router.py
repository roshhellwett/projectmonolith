"""
Shared webhook router for all bots.
Eliminates 5 nearly-identical webhook handlers across bot files.
"""

from fastapi import APIRouter, Request, Response
from telegram import Update

from core.gateway import get_update_id_dedup_cache, validate_webhook_auth
from core.logger import setup_logger

logger = setup_logger("WEBHOOK")

_bot_registry: dict[str, tuple] = {}
_update_counters: dict[str, int] = {}


def register_bot_webhook(bot_name: str, bot_app) -> None:
    _bot_registry[bot_name.lower()] = (bot_app, bot_name)
    _update_counters[bot_name.lower()] = 0


router = APIRouter()


@router.post("/webhook/{bot_name}/{secret}")
async def shared_webhook_handler(bot_name: str, secret: str, request: Request):
    if not validate_webhook_auth(secret, request):
        logger.warning(f"Webhook auth failed for {bot_name}")
        return Response(status_code=403)

    entry = _bot_registry.get(bot_name.lower())
    if not entry:
        logger.warning(f"No bot registered for: {bot_name}")
        return Response(status_code=404)

    bot_app, display_name = entry

    try:
        data = await request.json()
        dedup = get_update_id_dedup_cache(display_name.upper())
        update_id = data.get("update_id", 0)
        if update_id and update_id in dedup:
            return Response(status_code=200)
        if update_id:
            dedup[update_id] = True

        _update_counters[bot_name.lower()] = _update_counters.get(bot_name.lower(), 0) + 1
        count = _update_counters[bot_name.lower()]
        if count % 100 == 0:
            logger.info(f"[{display_name}] Processed {count} updates")

        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"[{display_name}] Webhook error: {e}")
        return Response(status_code=200)
