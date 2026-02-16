import uvicorn
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Update
from core.config import WEBHOOK_URL, PORT, WEBHOOK_SECRET
from core.logger import setup_logger
from zenith_group_bot.group_app import setup_group_app
from zenith_group_bot.repository import dispose_group_engine
from run_ai_bot import setup_ai_app, ai_worker, dispose_db_engine

logger = setup_logger("MONOLITH")

# Global Bot Instances
group_bot_app = None
ai_bot_app = None
ai_worker_tasks = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global group_bot_app, ai_bot_app, ai_worker_tasks
    logger.info("🚀 PROJECT MONOLITH: INITIALIZING FASTAPI WEBHOOK ECOSYSTEM")

    # 1. Setup Applications
    group_bot_app = await setup_group_app()
    ai_bot_app = await setup_ai_app()

    # 2. Start Internal PTB Lifecycles
    if group_bot_app:
        await group_bot_app.initialize()
        await group_bot_app.start()
    if ai_bot_app:
        await ai_bot_app.initialize()
        await ai_bot_app.start()

    # 3. Format URL and Register Webhooks Safely
    # Auto-fixes the URL if you forgot "https://" in your env variables
    webhook_base = (WEBHOOK_URL or "").strip().rstrip('/')
    if webhook_base and not webhook_base.startswith("http"):
        webhook_base = f"https://{webhook_base}"

    if webhook_base:
        try:
            if group_bot_app:
                await group_bot_app.bot.set_webhook(
                    url=f"{webhook_base}/webhook/group/{WEBHOOK_SECRET}",
                    secret_token=WEBHOOK_SECRET,
                    allowed_updates=Update.ALL_TYPES
                )
            if ai_bot_app:
                await ai_bot_app.bot.set_webhook(
                    url=f"{webhook_base}/webhook/ai/{WEBHOOK_SECRET}",
                    secret_token=WEBHOOK_SECRET,
                    allowed_updates=Update.ALL_TYPES
                )
            logger.info(f"📡 Webhooks successfully registered to: {webhook_base}")
        except Exception as e:
            logger.error(f"❌ Failed to set webhooks with Telegram (Check your tokens): {e}")
    else:
        logger.warning("⚠️ WEBHOOK_URL is missing! Bots will not receive messages.")

    # 4. Spin up 5 concurrent AI Workers for the queue
    ai_worker_tasks = [asyncio.create_task(ai_worker()) for _ in range(5)]

    yield  # The FastAPI Application runs here while the server is alive

    # 5. Execute Graceful Cloud Shutdown Sequence
    logger.info("🛑 SHUTTING DOWN MONOLITH...")
    
    for task in ai_worker_tasks:
        task.cancel()
        
    if group_bot_app:
        await group_bot_app.stop()
        await group_bot_app.shutdown()
        
    if ai_bot_app:
        await ai_bot_app.stop()
        await ai_bot_app.shutdown()
        await dispose_db_engine()
        
    await dispose_group_engine()
    logger.info("✅ Disconnected from database safely.")

# Initialize FastAPI with the robust lifespan manager
app = FastAPI(lifespan=lifespan)

@app.post("/webhook/group/{secret}")
async def group_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET: return Response(status_code=403)
    if not group_bot_app: return Response(status_code=503) # Failsafe if bot crashed
    
    try:
        data = await request.json()
        await group_bot_app.update_queue.put(Update.de_json(data, group_bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Group Webhook Processing Error: {e}")
        return Response(status_code=500)

@app.post("/webhook/ai/{secret}")
async def ai_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET: return Response(status_code=403)
    if not ai_bot_app: return Response(status_code=503) # Failsafe if bot crashed
    
    try:
        data = await request.json()
        await ai_bot_app.update_queue.put(Update.de_json(data, ai_bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"AI Webhook Processing Error: {e}")
        return Response(status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)