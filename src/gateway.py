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
from core.circuit_breaker import get_all_breaker_statuses
from core.config import DATABASE_URL, PORT, WEBHOOK_SECRET
from core.database import dispose_engine, get_engine, init_db
from core.db_health import is_db_healthy, start_health_monitor, stop_health_monitor
from core.logger import setup_logger
from core.secrets import enforce_startup_secrets

logger = setup_logger("GATEWAY")

webhook_rate = TTLCache(maxsize=500000, ttl=5)
api_rate = TTLCache(maxsize=500000, ttl=5)
seen_update_ids = TTLCache(maxsize=100000, ttl=300)

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


async def rate_limit(request: Request):
    client_ip = "unknown" if not request.client else request.client.host or "unknown"

    if "/webhook/" in request.url.path:
        webhook_rate[client_ip] = webhook_rate.get(client_ip, 0) + 1
        return webhook_rate[client_ip] <= 200
    else:
        api_rate[client_ip] = api_rate.get(client_ip, 0) + 1
        return api_rate[client_ip] <= 50


async def check_request_size(request: Request):
    content_length = request.headers.get("content-length")
    if not content_length:
        return True
    try:
        return int(content_length) <= MAX_REQUEST_SIZE
    except (ValueError, TypeError):
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
        "Supabase PgBouncer": "aws-0-ap-northeast-1.pooler.supabase.com",
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
    try:
        await init_db()
        await start_health_monitor(get_engine())
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")

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

    await asyncio.gather(
        safe_start("GROUP", run_group_bot.start_service),
        safe_start("AI", run_ai_bot.start_service),
        safe_start("CRYPTO", run_crypto_bot.start_service),
        safe_start("SUPPORT", run_support_bot.start_service),
        safe_start("ADMIN", run_admin_bot.start_service),
    )

    online = sum(1 for v in SERVICE_REGISTRY.values() if v == "online")
    total = len(SERVICE_REGISTRY)
    logger.info(f"📊 MONOLITH READY: {online}/{total} services online")

    yield

    logger.info("🛑 MONOLITH SHUTDOWN")
    await stop_health_monitor()
    try:
        await asyncio.wait_for(
            asyncio.gather(
                run_group_bot.stop_service(dispose_db=False),
                run_ai_bot.stop_service(dispose_db=False),
                run_crypto_bot.stop_service(dispose_db=False),
                run_support_bot.stop_service(dispose_db=False),
                run_admin_bot.stop_service(dispose_db=False),
                return_exceptions=True,
            ),
            timeout=15.0,
        )
    except TimeoutError:
        logger.error("⚠️ Force closing: a service refused to shut down in time.")
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
    if "/webhook/" in request.url.path:
        logger.info(f"🌐 Webhook HTTP request arriving: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")

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


app.include_router(run_group_bot.router)
app.include_router(run_ai_bot.router)
app.include_router(run_crypto_bot.router)
app.include_router(run_support_bot.router)
app.include_router(run_admin_bot.router)


@app.get("/health")
async def health():
    from core.config import WEBHOOK_URL

    db_ok = is_db_healthy()
    breakers = get_all_breaker_statuses()
    all_breakers_closed = all(b.get("state") == "closed" for b in breakers)
    status_code = 200 if db_ok and all_breakers_closed else 503
    return JSONResponse(
        {
            "status": "ok" if status_code == 200 else "degraded",
            "db_healthy": db_ok,
            "circuit_breakers": breakers,
            "system": "Project Monolith",
            "webhook_base_url": WEBHOOK_URL,
            "services": SERVICE_REGISTRY,
        },
        status_code=status_code,
    )


@app.get("/")
async def root():
    return JSONResponse(
        {
            "status": "ok",
            "system": "Project Monolith",
            "message": "All systems operational.",
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
