import uvicorn
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from cachetools import TTLCache

from core.config import PORT, WEBHOOK_SECRET
from core.logger import setup_logger

import run_group_bot
import run_ai_bot
import run_crypto_bot
import run_support_bot

logger = setup_logger("GATEWAY")

webhook_rate = TTLCache(maxsize=500000, ttl=5)


async def rate_limit(request: Request):
    ip = request.headers.get(
        "x-forwarded-for", request.client.host if request.client else "unknown"
    ).split(",")[0].strip()
    webhook_rate[ip] = webhook_rate.get(ip, 0) + 1
    if "/webhook/" in request.url.path:
        return webhook_rate[ip] <= 200
    return webhook_rate[ip] <= 50


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 MONOLITH STARTING")
    if not WEBHOOK_SECRET:
        logger.critical("⚠️ WEBHOOK_SECRET is not set! Webhooks are insecure.")

    async def safe_start(name, func):
        try:
            await func()
            logger.info(f"✅ {name} started")
        except Exception as e:
            logger.error(f"{name} failed to start: {e}")

    await asyncio.gather(
        safe_start("GROUP", run_group_bot.start_service),
        safe_start("AI", run_ai_bot.start_service),
        safe_start("CRYPTO", run_crypto_bot.start_service),
        safe_start("SUPPORT", run_support_bot.start_service),
    )
    yield
    logger.info("🛑 MONOLITH SHUTDOWN")
    try:
        await asyncio.wait_for(
            asyncio.gather(
                run_group_bot.stop_service(),
                run_ai_bot.stop_service(),
                run_crypto_bot.stop_service(),
                run_support_bot.stop_service(),
                return_exceptions=True,
            ),
            timeout=10.0,
        )
    except asyncio.TimeoutError:
        logger.error("⚠️ Force closing: a service refused to shut down in time.")


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def global_protection(request: Request, call_next):
    if not await rate_limit(request):
        return JSONResponse({"error": "Rate Limit Exceeded."}, status_code=429)
    return await call_next(request)


app.include_router(run_group_bot.router)
app.include_router(run_ai_bot.router)
app.include_router(run_crypto_bot.router)
app.include_router(run_support_bot.router)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "system": "Project Monolith"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)