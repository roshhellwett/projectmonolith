import asyncio

from fastapi import APIRouter, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler

from core.config import ADMIN_BOT_TOKEN, WEBHOOK_SECRET
from core.database import dispose_engine
from core.error_handler import handle_bot_error
from core.gateway import attach_gateway, get_update_id_dedup_cache, setup_bot_webhook, validate_webhook_auth
from core.logger import setup_logger
from zenith_admin_bot.commands import (
    cmd_audit,
    cmd_botlist,
    cmd_broadcast,
    cmd_bulk_keygen,
    cmd_canned,
    cmd_dbstats,
    cmd_extend,
    cmd_faq,
    cmd_group_search,
    cmd_groups_list,
    cmd_health,
    cmd_key_history,
    cmd_keygen,
    cmd_keys,
    cmd_lookup,
    cmd_metrics,
    cmd_revenue_report,
    cmd_revoke,
    cmd_search,
    cmd_stale_tickets,
    cmd_start,
    cmd_stats,
    cmd_subs,
    cmd_ticket_close_admin,
    cmd_ticket_detail,
    cmd_ticket_inprogress,
    cmd_ticket_metrics,
    cmd_ticket_resolve,
    cmd_tickets,
)
from zenith_admin_bot.dashboard import handle_dashboard
from zenith_admin_bot.monitoring import start_monitoring, stop_monitoring

logger = setup_logger("ADMIN")
router = APIRouter()
bot_app = None
background_tasks = set()


async def start_service():
    global bot_app
    if not ADMIN_BOT_TOKEN:
        logger.warning("ADMIN_BOT_TOKEN missing! Admin Service disabled.")
        return

    bot_app = ApplicationBuilder().token(ADMIN_BOT_TOKEN).build()
    attach_gateway(bot_app, "Admin")

    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("keygen", cmd_keygen))
    bot_app.add_handler(CommandHandler("extend", cmd_extend))
    bot_app.add_handler(CommandHandler("revoke", cmd_revoke))
    bot_app.add_handler(CommandHandler("lookup", cmd_lookup))
    bot_app.add_handler(CommandHandler("keys", cmd_keys))
    bot_app.add_handler(CommandHandler("stats", cmd_stats))
    bot_app.add_handler(CommandHandler("subs", cmd_subs))
    bot_app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    bot_app.add_handler(CommandHandler("audit", cmd_audit))
    bot_app.add_handler(CommandHandler("health", cmd_health))
    bot_app.add_handler(CommandHandler("metrics", cmd_metrics))
    bot_app.add_handler(CommandHandler("botlist", cmd_botlist))
    bot_app.add_handler(CommandHandler("tickets", cmd_tickets))
    bot_app.add_handler(CommandHandler("ticket", cmd_ticket_detail))
    bot_app.add_handler(CommandHandler("resolve", cmd_ticket_resolve))
    bot_app.add_handler(CommandHandler("inprogress", cmd_ticket_inprogress))
    bot_app.add_handler(CommandHandler("close", cmd_ticket_close_admin))
    bot_app.add_handler(CommandHandler("search", cmd_search))
    bot_app.add_handler(CommandHandler("groups", cmd_groups_list))
    bot_app.add_handler(CommandHandler("gsearch", cmd_group_search))
    bot_app.add_handler(CommandHandler("bulkkeygen", cmd_bulk_keygen))
    bot_app.add_handler(CommandHandler("dbstats", cmd_dbstats))
    bot_app.add_handler(CommandHandler("revenue", cmd_revenue_report))
    bot_app.add_handler(CommandHandler("keyhistory", cmd_key_history))
    bot_app.add_handler(CommandHandler("ticketmetrics", cmd_ticket_metrics))
    bot_app.add_handler(CommandHandler("stale", cmd_stale_tickets))
    bot_app.add_handler(CommandHandler("faq", cmd_faq))
    bot_app.add_handler(CommandHandler("canned", cmd_canned))
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))
    bot_app.add_error_handler(handle_bot_error)

    await bot_app.initialize()
    await bot_app.start()

    try:
        await start_monitoring(bot_app)
    except Exception as e:
        logger.warning(f"Monitoring startup skipped (DB unavailable): {e}")

    logger.info("Admin Bot: Online")


async def register_webhook():
    if bot_app:
        await setup_bot_webhook(bot_app, "admin")


async def stop_service(dispose_db: bool = False):
    try:
        await stop_monitoring()
    except Exception as e:
        logger.warning(f"Monitoring stop error (non-fatal): {e}")

    for t in list(background_tasks):
        t.cancel()
    if background_tasks:
        await asyncio.gather(*list(background_tasks), return_exceptions=True)

    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()

    if dispose_db:
        await dispose_engine()
    logger.info("Admin Bot: Stopped")


@router.post("/webhook/admin/{secret}")
async def admin_webhook(secret: str, request: Request):
    if not validate_webhook_auth(secret, request):
        logger.warning(f"❌ [Admin] Webhook auth failed! Expected len={len(WEBHOOK_SECRET)}, got len={len(secret)}")
        return Response(status_code=403)
    if not bot_app:
        return Response(status_code=503)

    try:
        data = await request.json()
        dedup = get_update_id_dedup_cache("ADMIN")
        update_id = data.get("update_id", 0)
        if update_id and update_id in dedup:
            return Response(status_code=200)
        if update_id:
            dedup[update_id] = True
        logger.info(
            f"📥 [Admin] Enqueuing update {update_id} into update_queue (qsize before={bot_app.update_queue.qsize()})"
        )
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Admin Webhook Error: {e}", exc_info=True)
        return Response(status_code=200)
