import uvicorn
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.config import PORT
from core.logger import setup_logger

# 🔌 Import your isolated Bot Modules
import run_group_bot
import run_ai_bot
import run_crypto_bot # 🐋 MOUNTING ZENITH WHALE

logger = setup_logger("GATEWAY")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 PROJECT MONOLITH: STARTING API GATEWAY")
    
    # 1. Boot up all isolated microservices
    await run_group_bot.start_service()
    await run_ai_bot.start_service()
    await run_crypto_bot.start_service() # 🐋 BOOTING ZENITH WHALE
    
    yield  # Server runs here
    
    # 2. Graceful Cloud Shutdown
    logger.info("🛑 SHUTTING DOWN GATEWAY...")
    try:
        await asyncio.wait_for(
            asyncio.gather(
                run_group_bot.stop_service(),
                run_ai_bot.stop_service(),
                run_crypto_bot.stop_service(), # 🐋 SHUTTING DOWN ZENITH WHALE
                return_exceptions=True
            ),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        logger.error("⚠️ Force closing gateway: A microservice refused to shut down in time.")
    finally:
        logger.info("✅ Gateway offline.")

# Initialize the Master Server
app = FastAPI(lifespan=lifespan)

# 3. Mount the isolated bot webhooks
app.include_router(run_group_bot.router)
app.include_router(run_ai_bot.router)
app.include_router(run_crypto_bot.router) # 🐋 EXPOSING CRYPTO ROUTES

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)