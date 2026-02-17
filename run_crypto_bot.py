import asyncio

from fastapi import APIRouter, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder

from core.logger import setup_logger
from core.config import CRYPTO_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET
from zenith_crypto_bot.repository import (
    SubscriptionRepo,
    init_crypto_db,
    dispose_crypto_engine
)

logger = setup_logger("CRYPTO_SVC")
router = APIRouter()

bot_app = None
background_tasks = set()

alert_queue = asyncio.Queue(maxsize=10000)


def track_task(task):
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


async def safe_loop(name, coro):
    while True:
        try:
            await coro()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"{name} crashed: {e}")
            await asyncio.sleep(5)


async def alert_dispatcher():
    while True:
        chat_id, text = await alert_queue.get()
        try:
            await bot_app.bot.send_message(chat_id, text, parse_mode="HTML")
        except Exception:
            pass
        alert_queue.task_done()
        await asyncio.sleep(0.05)


async def fake_chain_watcher():
    coins = ["ETH", "USDT", "SOL"]

    while True:
        await asyncio.sleep(300)

        subs = await SubscriptionRepo.get_all_active_users()

        for uid in subs:
            text = f"🐋 Whale Alert Demo"
            await alert_queue.put((uid, text))


async def start_service():
    global bot_app

    if not CRYPTO_BOT_TOKEN:
        return

    await init_crypto_db()

    bot_app = ApplicationBuilder().token(CRYPTO_BOT_TOKEN).build()

    await bot_app.initialize()
    await bot_app.start()

    webhook_base = (WEBHOOK_URL or "").strip().rstrip("/")
    if webhook_base and not webhook_base.startswith("http"):
        webhook_base = f"https://{webhook_base}"

    if webhook_base:
        try:
            await bot_app.bot.set_webhook(
                url=f"{webhook_base}/webhook/crypto/{WEBHOOK_SECRET}",
                secret_token=WEBHOOK_SECRET
            )
            logger.info("✅ Crypto Bot Online & Webhook Registered.")
        except Exception as e:
            logger.error(f"❌ Crypto Bot Webhook Failed: {e}")

    track_task(asyncio.create_task(safe_loop("dispatcher", alert_dispatcher)))
    track_task(asyncio.create_task(safe_loop("watcher", fake_chain_watcher)))


async def stop_service():
    for t in list(background_tasks):
        t.cancel()

    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()

    await dispose_crypto_engine()


@router.post("/webhook/crypto/{secret}")
async def webhook(secret: str, request: Request):

    if secret != WEBHOOK_SECRET:
        return Response(status_code=403)

    if not bot_app:
        return Response(status_code=503)

    data = await request.json()
    await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
    return Response(status_code=200)
