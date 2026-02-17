from fastapi import APIRouter, Request, Response
from telegram import Update
from core.config import WEBHOOK_URL, WEBHOOK_SECRET
from core.logger import setup_logger
from zenith_group_bot.group_app import setup_group_app
from zenith_group_bot.repository import dispose_group_engine

logger = setup_logger("SVC_GROUP")
router = APIRouter()
bot_app = None

async def start_service():
    global bot_app
    bot_app = await setup_group_app()
    if not bot_app: return
    
    await bot_app.initialize()
    await bot_app.start()

    # Format URL and Register Webhook
    webhook_base = (WEBHOOK_URL or "").strip().rstrip('/')
    if webhook_base and not webhook_base.startswith("http"):
        webhook_base = f"https://{webhook_base}"

    if webhook_base:
        try:
            await bot_app.bot.set_webhook(
                url=f"{webhook_base}/webhook/group/{WEBHOOK_SECRET}",
                secret_token=WEBHOOK_SECRET,
                allowed_updates=Update.ALL_TYPES
            )
            logger.info(f"✅ Group Bot Online & Webhook Registered.")
        except Exception as e:
            logger.error(f"❌ Group Bot Webhook Failed: {e}")

async def stop_service():
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await dispose_group_engine()

# 🚀 The Bot's Personal Webhook Router
@router.post("/webhook/group/{secret}")
async def group_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET: return Response(status_code=403)
    if not bot_app: return Response(status_code=503)
    
    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Group Webhook Processing Error: {e}")
        return Response(status_code=500)