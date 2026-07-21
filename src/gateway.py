import asyncio
import socket
from contextlib import asynccontextmanager

import uvicorn
from cachetools import TTLCache
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import run_admin_bot
import run_ai_bot
import run_crypto_bot
import run_group_bot
import run_support_bot
from core.config import DATABASE_URL, MAINTENANCE_MODE, PORT, WEBHOOK_SECRET
from core.data_cleanup import run_cleanup
from core.database import dispose_engine, get_engine, init_db
from core.db_health import is_db_healthy, set_db_unhealthy, start_health_monitor, stop_health_monitor
from core.logger import setup_logger
from core.secrets import enforce_startup_secrets
from core.webhook_router import router as webhook_router

logger = setup_logger("GATEWAY")

webhook_rate = TTLCache(maxsize=10000, ttl=5)
api_rate = TTLCache(maxsize=5000, ttl=5)

REQUEST_TIMEOUT_SECONDS = 25

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": "default-src 'self'",
}

MAX_REQUEST_SIZE = 1_000_000  # 1MB

SERVICE_REGISTRY = {}


async def rate_limit(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")

    if "/webhook/" in request.url.path:
        current = webhook_rate.get(client_ip, 0)
        webhook_rate[client_ip] = current + 1
        return current < 100

    current = api_rate.get(client_ip, 0)
    api_rate[client_ip] = current + 1
    return current < 50


async def check_request_size(request: Request) -> bool:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_SIZE:
                logger.warning(f"Request too large: {content_length}B from {request.client.host if request.client else 'unknown'}")
                return False
        except (ValueError, TypeError):
            pass
    return True


def _validate_environment():
    """Validate critical environment variables before startup."""
    issues = []

    if not DATABASE_URL:
        issues.append("DATABASE_URL is not set — all database operations will fail")

    if not WEBHOOK_SECRET:
        issues.append("WEBHOOK_SECRET is not set — webhooks are insecure")

    for issue in issues:
        logger.warning(f"⚠️ CONFIG: {issue}")

    enforce_startup_secrets()
    return len(issues) == 0


async def _diagnose_network():
    """Log DNS resolution for critical external hosts."""
    hosts = {
        "Telegram API": "api.telegram.org",
        "CoinGecko API": "api.coingecko.com",
    }
    for label, host in hosts.items():
        try:
            addrs = socket.getaddrinfo(host, 0)
            ips = list({a[4][0] for a in addrs})
            logger.info(f"🌐 {label} → {host} resolves to {ips}")
        except Exception as e:
            logger.warning(f"🌐 {label} → {host} DNS FAILED: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 MONOLITH STARTING")

    _validate_environment()
    await _diagnose_network()

    async def _startup():
        await asyncio.sleep(0.1)  # Yield loop immediately so uvicorn can start serving /health
        try:
            await init_db()
            await start_health_monitor(get_engine())
        except Exception as e:
            set_db_unhealthy()
            logger.error(f"❌ Database init failed: {e}")
        await asyncio.sleep(0.05)  # Yield before starting heavy service initialization

        async def safe_start(name, func):
            try:
                await asyncio.wait_for(func(), timeout=30.0)
                SERVICE_REGISTRY[name] = "online"
                logger.info(f"✅ {name} started")
            except TimeoutError:
                SERVICE_REGISTRY[name] = "failed: startup timeout"
                logger.error(f"❌ {name} startup timed out after 30s")
            except Exception as e:
                SERVICE_REGISTRY[name] = f"failed: {e}"
                logger.error(f"❌ {name} failed to start: {e}")

        services = [
            ("GROUP", run_group_bot.start_service),
            ("AI", run_ai_bot.start_service),
            ("CRYPTO", run_crypto_bot.start_service),
            ("SUPPORT", run_support_bot.start_service),
            ("ADMIN", run_admin_bot.start_service),
        ]
        await asyncio.gather(*(safe_start(n, f) for n, f in services))

        online = sum(1 for v in SERVICE_REGISTRY.values() if v == "online")
        total = len(SERVICE_REGISTRY)
        logger.info(f"📊 MONOLITH READY: {online}/{total} services online")

        await asyncio.sleep(3)
        for label, reg in [
            ("GROUP", run_group_bot.register_webhook),
            ("AI", run_ai_bot.register_webhook),
            ("CRYPTO", run_crypto_bot.register_webhook),
            ("SUPPORT", run_support_bot.register_webhook),
            ("ADMIN", run_admin_bot.register_webhook),
        ]:
            try:
                await asyncio.wait_for(reg(), timeout=30.0)
                logger.info(f"✅ {label} webhook registered")
            except Exception as e:
                logger.error(f"❌ {label} webhook registration failed: {e}")
            await asyncio.sleep(1)

    startup_task = asyncio.create_task(_startup())

    async def _daily_cleanup():
        await asyncio.sleep(3600)
        while True:
            logger.info("Starting daily data retention cleanup")
            try:
                await asyncio.wait_for(run_cleanup(), timeout=120.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Data cleanup failed: {e}")
            await asyncio.sleep(86400)

    cleanup_task = asyncio.create_task(_daily_cleanup())

    yield

    logger.info("🛑 MONOLITH SHUTDOWN")
    await stop_health_monitor()
    for t in [startup_task, cleanup_task]:
        t.cancel()
    await asyncio.gather(startup_task, cleanup_task, return_exceptions=True)
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                run_group_bot.stop_service(dispose_db=False),
                run_ai_bot.stop_service(dispose_db=False),
                run_crypto_bot.stop_service(dispose_db=False),
                run_support_bot.stop_service(dispose_db=False),
                run_admin_bot.stop_service(dispose_db=False),
                return_exceptions=True,
            ),
            timeout=20.0,
        )
        for service_name, result in zip(
            ["Group", "AI", "Crypto", "Support", "Admin"], results, strict=False
        ):
            if isinstance(result, Exception):
                logger.warning(f"⚠️ {service_name} service shutdown raised: {result}")
            else:
                logger.info(f"✅ {service_name} service stopped")
    except TimeoutError:
        logger.error("⚠️ Force closing: one or more services refused to shut down in time.")
    await dispose_engine()
    logger.info("👋 MONOLITH STOPPED")


app = FastAPI(
    title="Project Monolith",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


@app.middleware("http")
async def global_protection(request: Request, call_next):
    if request.url.path in ("/health", "/") or request.url.path.startswith("/health/"):
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response

    if "/webhook/" in request.url.path and MAINTENANCE_MODE:
        return JSONResponse({"ok": True, "maintenance": True}, status_code=200)

    if not await check_request_size(request):
        return JSONResponse({"error": "Payload too large. Max 1MB."}, status_code=413)

    if not await rate_limit(request):
        return JSONResponse({"error": "Rate Limit Exceeded."}, status_code=429)

    try:
        response = await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_SECONDS)
    except TimeoutError:
        logger.warning(f"Request timeout on {request.url.path}")
        return JSONResponse({"error": "Request timed out"}, status_code=504)

    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    if "/webhook/" in request.url.path:
        return JSONResponse({"ok": True}, status_code=200)
    return JSONResponse({"error": "An internal error occurred"}, status_code=500)


app.include_router(webhook_router)


@app.get("/health")
async def health():
    if MAINTENANCE_MODE:
        return JSONResponse({"status": "maintenance"}, status_code=503)
    return JSONResponse(
        {
            "status": "ok",
            "db_healthy": is_db_healthy(),
            "maintenance_mode": MAINTENANCE_MODE,
            "services": {k: v for k, v in SERVICE_REGISTRY.items() if v is not None},
        },
        status_code=200,
    )


@app.get("/")
async def root():
    return JSONResponse(
        {
            "status": "ok",
            "system": "Project Monolith",
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        access_log=True,
        server_header=False,
    )
