import asyncio
from datetime import datetime, timezone
from core.logger import setup_logger
from core.config import ADMIN_USER_ID, WEBHOOK_URL
from zenith_admin_bot.repository import BotRegistryRepo, MonitoringRepo

logger = setup_logger("ADMIN_MONITOR")

alert_queue = asyncio.Queue(maxsize=100)
background_tasks = set()
bot_app = None

bot_app_references = {
    "AI": None,
    "Crypto": None,
    "Group": None,
    "Support": None,
    "Admin": None,
}

last_alert_time = {}
ALERT_COOLDOWN = 3600


def track_task(task):
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


def set_bot_app(app, bot_name="Admin"):
    global bot_app
    bot_app = app
    if bot_name in bot_app_references:
        bot_app_references[bot_name] = app


def register_bot_app(bot_name, app):
    bot_app_references[bot_name] = app
    logger.info(f"Registered {bot_name} bot app for monitoring")


async def safe_loop(name, coro):
    while True:
        try:
            await coro()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Loop '{name}' crashed: {e}")
            await asyncio.sleep(5)


async def alert_dispatcher():
    while True:
        chat_id, text = await alert_queue.get()
        try:
            if bot_app:
                await bot_app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Alert dispatch failed: {e}")
        finally:
            alert_queue.task_done()


async def check_bot_health():
    while True:
        await asyncio.sleep(300)
        try:
            bots = await BotRegistryRepo.get_all_bots()
            for bot in bots:
                await check_single_bot(bot)
        except Exception as e:
            logger.error(f"Health check error: {e}")


async def check_single_bot(bot):
    status = "healthy"
    previous_status = bot.health_status
    
    target_app = bot_app_references.get(bot.bot_name)
    
    if target_app is None:
        target_app = bot_app
    
    try:
        if target_app:
            me = await target_app.bot.get_me()
            status = "healthy"
        else:
            status = "unknown"
            logger.warning(f"No app reference for bot: {bot.bot_name}")
    except Exception as e:
        logger.warning(f"Bot {bot.bot_name} health check failed: {e}")
        status = "error"

    await BotRegistryRepo.update_health_status(bot.bot_name, status)

    now = datetime.now(timezone.utc)
    alert_key = f"bot_down_{bot.bot_name}"
    last_alert = last_alert_time.get(alert_key, None)

    if status == "error" and bot.status != "inactive":
        if last_alert is None or (now - last_alert).total_seconds() > ALERT_COOLDOWN:
            await queue_alert(
                f"🚨 <b>BOT DOWN ALERT</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Bot:</b> {bot.bot_name}\n"
                f"<b>Status:</b> Error - not responding\n"
                f"<b>Time:</b> {datetime.now().strftime('%d %b %Y %H:%M UTC')}"
            )
            last_alert_time[alert_key] = now

    if previous_status == "error" and status == "healthy" and bot.status != "inactive":
        if last_alert is None or (now - last_alert).total_seconds() > ALERT_COOLDOWN:
            await queue_alert(
                f"✅ <b>BOT RECOVERED</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Bot:</b> {bot.bot_name}\n"
                f"<b>Status:</b> Back online\n"
                f"<b>Time:</b> {datetime.now().strftime('%d %b %Y %H:%M UTC')}"
            )
            last_alert_time[alert_key] = now


async def monitor_subscriptions():
    previous_expiring = None
    first_run = True

    while True:
        await asyncio.sleep(3600)
        try:
            stats = await MonitoringRepo.get_subscription_stats()
            current_expiring = stats.get("expiring_within_7_days", 0)

            if first_run:
                if current_expiring > 0:
                    await queue_alert(
                        f"⚠️ <b>SUBSCRIPTION ALERT</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"<b>{current_expiring} subscription(s)</b> expiring within 7 days!\n\n"
                        f"<i>Consider running a retention campaign.</i>"
                    )
                first_run = False
            elif current_expiring > previous_expiring and previous_expiring is not None and previous_expiring > 0:
                diff = current_expiring - previous_expiring
                await queue_alert(
                    f"⚠️ <b>REVENUE ALERT</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"<b>{diff} new subscription(s)</b> expiring within 7 days!\n"
                    f"<b>Total at risk:</b> {current_expiring}\n\n"
                    f"<i>Consider running a retention campaign.</i>"
                )

            previous_expiring = current_expiring

        except Exception as e:
            logger.error(f"Subscription monitor error: {e}")


async def queue_alert(message: str):
    if ADMIN_USER_ID:
        try:
            alert_queue.put_nowait((ADMIN_USER_ID, message))
        except asyncio.QueueFull:
            logger.warning("Alert queue full, dropping alert")


async def start_monitoring(app):
    set_bot_app(app, "Admin")
    await BotRegistryRepo.register_bot("AI")
    await BotRegistryRepo.register_bot("Crypto")
    await BotRegistryRepo.register_bot("Group")
    await BotRegistryRepo.register_bot("Support")
    await BotRegistryRepo.register_bot("Admin")

    track_task(asyncio.create_task(safe_loop("health_check", check_bot_health)))
    track_task(asyncio.create_task(safe_loop("sub_monitor", monitor_subscriptions)))
    track_task(asyncio.create_task(safe_loop("dispatcher", alert_dispatcher)))

    logger.info("👀 Admin Monitoring: Started")


async def stop_monitoring():
    for t in list(background_tasks):
        t.cancel()
    logger.info("👀 Admin Monitoring: Stopped")
