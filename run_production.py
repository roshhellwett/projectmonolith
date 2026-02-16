import uvicorn
import asyncio
from fastapi import FastAPI, Request, Response
from telegram import Update
from core.config import WEBHOOK_URL, PORT, WEBHOOK_SECRET
from core.logger import setup_logger
from zenith_group_bot.group_app import setup_group_app
from zenith_group_bot.repository import dispose_group_engine
from run_ai_bot import setup_ai_app, ai_worker, dispose_db_engine

logger = setup_logger("MONOLITH")
app = FastAPI()

# Global Bot Instances
group_bot_app = None
ai_bot_app = None
ai_worker_tasks = []

@app.on_event("startup")
async def on_startup():
    global group_bot_app, ai_bot_app, ai_worker_tasks
    logger.info("🚀 PROJECT MONOLITH: INITIALIZING FASTAPI WEBHOOK ECOSYSTEM")

    # 1. Setup Applications
    group_bot_app = await setup_group_app()
    ai_bot_app = await setup_ai_app()

    # 2. Start Lifecycles
    await group_bot_app.initialize()
    await group_bot_app.start()
    if ai_bot_app:
        await ai_bot_app.initialize()
        await ai_bot_app.start()

    # 3. Register Webhooks with Telegram
    if WEBHOOK_URL:
        await group_bot_app.bot.set_webhook(
            url=f"{WEBHOOK_URL}/webhook/group/{WEBHOOK_SECRET}",
            secret_token=WEBHOOK_SECRET
        )
        if ai_bot_app:
            await ai_bot_app.bot.set_webhook(
                url=f"{WEBHOOK_URL}/webhook/ai/{WEBHOOK_SECRET}",
                secret_token=WEBHOOK_SECRET
            )
        logger.info(f"📡 Webhooks registered to: {WEBHOOK_URL}")

    # 4. Spin up AI Workers
    ai_worker_tasks = [asyncio.create_task(ai_worker()) for _ in range(5)]

@app.post("/webhook/group/{secret}")
async def group_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET: return Response(status_code=403)
    data = await request.json()
    await group_bot_app.update_queue.put(Update.de_json(data, group_bot_app.bot))
    return Response(status_code=200)

@app.post("/webhook/ai/{secret}")
async def ai_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET: return Response(status_code=403)
    data = await request.json()
    await ai_bot_app.update_queue.put(Update.de_json(data, ai_bot_app.bot))
    return Response(status_code=200)

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("🛑 SHUTTING DOWN MONOLITH...")
    for task in ai_worker_tasks: task.cancel()
    if group_bot_app: await group_bot_app.stop()
    if ai_bot_app: 
        await ai_bot_app.stop()
        await dispose_db_engine()
    await dispose_group_engine()
    logger.info("✅ Disconnected from database safely.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)