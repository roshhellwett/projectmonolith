"""
Health monitor for Project Monolith.

Designed to run as a Railway cron job (every 12 hours).
Checks all services and sends a status report to the admin via Telegram.

Usage:
    python scripts/health_monitor.py

Environment variables required:
    ADMIN_BOT_TOKEN  — Telegram bot token for sending status
    ADMIN_USER_ID    — Telegram user ID to receive the report
    DATABASE_URL     — Database connection string
    WEBHOOK_URL      — Base URL of the deployed app
"""

import asyncio
import os
import sys
import time

import httpx

from core.database import get_engine
from core.logger import setup_logger

logger = setup_logger("HEALTH")

REPORT_INTERVAL_HOURS = 12


async def check_http_health(base_url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}/health")
            if resp.status_code == 200:
                data = resp.json()
                services = data.get("services", {})
                online = sum(1 for v in services.values() if v == "online")
                total = len(services)
                return {
                    "status": "ok",
                    "code": resp.status_code,
                    "online": online,
                    "total": total,
                    "services": services,
                }
            return {"status": "error", "code": resp.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_database() -> dict:
    from sqlalchemy import text

    try:
        start = time.monotonic()
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = round((time.monotonic() - start) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_telegram_webhook(bot_token: str, bot_name: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://api.telegram.org/bot{bot_token}/getWebhookInfo")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    webhook = data["result"]
                    url = webhook.get("url", "")
                    pending = webhook.get("pending_update_count", 0)
                    last_error = webhook.get("last_error_date")
                    return {
                        "status": "ok" if url else "no_webhook",
                        "url": url,
                        "pending": pending,
                        "last_error": last_error,
                    }
            return {"status": "error", "code": resp.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def build_status_message(
    http: dict,
    db: dict,
    webhooks: dict[str, dict],
) -> str:
    lines = ["🔍 <b>Monolith Health Report</b>", "─" * 25, ""]

    for bot_name in ["ADMIN", "AI", "CRYPTO", "GROUP", "SUPPORT"]:
        wh = webhooks.get(bot_name, {})
        wh_status = wh.get("status", "unknown")
        pending = wh.get("pending", "?")
        if wh_status == "ok":
            icon = "🟢"
            detail = f"webhook OK ({pending} pending)"
        elif wh_status == "no_webhook":
            icon = "🟡"
            detail = "no webhook set"
        else:
            icon = "🔴"
            detail = f"webhook ERROR: {wh.get('error', wh_status)}"

        svc_status = (http.get("services", {}) or {}).get(bot_name, "unknown")
        lines.append(f"{icon} <b>{bot_name}</b> — {svc_status}, {detail}")

    db_status = db.get("status", "unknown")
    if db_status == "ok":
        db_icon = "🟢"
        db_detail = f"{db.get('latency_ms', '?')}ms"
    else:
        db_icon = "🔴"
        db_detail = f"ERROR: {db.get('error', db_status)}"
    lines.append(f"{db_icon} <b>Database</b> — {db_detail}")

    http_status = http.get("status", "unknown")
    if http_status == "ok":
        total = http.get("total", 0)
        online = http.get("online", 0)
        overall_icon = "🟢" if online == total else "🟡"
        overall = f"{overall_icon} <b>Overall:</b> {online}/{total} services healthy"
    else:
        overall = f"🔴 <b>Overall:</b> HTTP unreachable ({http.get('code', '?')})"

    lines.append("")
    lines.append("─" * 25)
    lines.append(overall)
    lines.append("")
    lines.append(f"⏰ Next check: in {REPORT_INTERVAL_HOURS}h")

    return "\n".join(lines)


async def send_telegram_message(bot_token: str, chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=15.0) as client:
        await client.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_notification": False,
            },
        )
    logger.info("Status report sent to admin")


async def main():
    logger.info("Health monitor started")

    admin_bot_token = os.getenv("ADMIN_BOT_TOKEN", "")
    admin_user_id = os.getenv("ADMIN_USER_ID", "")
    webhook_url = os.getenv("WEBHOOK_URL", "")

    errors = []
    if not admin_bot_token:
        errors.append("ADMIN_BOT_TOKEN not set")
    if not admin_user_id:
        errors.append("ADMIN_USER_ID not set")
    if not webhook_url:
        errors.append("WEBHOOK_URL not set")

    if errors:
        for e in errors:
            logger.error(e)
        sys.exit(1)

    admin_chat_id = int(admin_user_id)
    base_url = webhook_url.rstrip("/")

    logger.info(f"Checking HTTP health at {base_url}/health")
    http_result = await check_http_health(base_url)
    logger.info(f"HTTP health: {http_result.get('status')}")

    logger.info("Checking database")
    db_result = await check_database()
    logger.info(f"Database: {db_result.get('status')}")

    bot_tokens = {
        "ADMIN": admin_bot_token,
        "AI": os.getenv("AI_BOT_TOKEN", ""),
        "CRYPTO": os.getenv("CRYPTO_BOT_TOKEN", ""),
        "GROUP": os.getenv("GROUP_BOT_TOKEN", ""),
        "SUPPORT": os.getenv("SUPPORT_BOT_TOKEN", ""),
    }

    logger.info("Checking Telegram webhooks")
    webhook_results = {}
    for name, token in bot_tokens.items():
        if token:
            result = await check_telegram_webhook(token, name)
            webhook_results[name] = result
            wh_status = result.get("status", "error")
            logger.info(f"  {name} webhook: {wh_status}")
        else:
            webhook_results[name] = {"status": "no_token"}
            logger.warning(f"  {name}: no token configured")

    message = build_status_message(http_result, db_result, webhook_results)
    logger.info("Sending status report to admin")
    await send_telegram_message(admin_bot_token, admin_chat_id, message)

    online = http_result.get("online", 0)
    total = http_result.get("total", 0)
    if http_result.get("status") == "ok" and online == total and db_result.get("status") == "ok":
        logger.info("All systems healthy")
        sys.exit(0)
    else:
        logger.warning("Some systems have issues")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
