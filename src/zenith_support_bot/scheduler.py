import asyncio
import contextlib

from core.logger import setup_logger
from zenith_support_bot.notifications import notify_ticket_auto_closed, send_24h_reminder
from zenith_support_bot.repository import TicketRepo

logger = setup_logger("TICKET_SCHEDULER")

scheduler_running = False
scheduler_task = None


async def start_ticket_scheduler():
    global scheduler_running, scheduler_task
    if scheduler_running:
        logger.warning("Ticket scheduler already running")
        return

    scheduler_running = True
    scheduler_task = asyncio.create_task(ticket_scheduler_loop())
    logger.info("✅ Ticket scheduler started")


async def stop_ticket_scheduler():
    global scheduler_running, scheduler_task
    scheduler_running = False

    if scheduler_task:
        scheduler_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await scheduler_task

    logger.info("🛑 Ticket scheduler stopped")


async def ticket_scheduler_loop():
    while scheduler_running:
        try:
            await check_and_process_tickets()
        except Exception as e:
            logger.error(f"Error in ticket scheduler: {e}")

        await asyncio.sleep(300)


async def check_and_process_tickets():
    try:
        reminder_tickets = await TicketRepo.get_reminder_tickets(hours=23)
        for ticket in reminder_tickets:
            try:
                await send_24h_reminder(
                    user_id=ticket.user_id,
                    ticket_id=ticket.id,
                    subject=ticket.subject,
                )
                await TicketRepo.mark_reminder_sent(ticket.id)
                logger.info(f"Sent reminder for ticket {ticket.id}")
            except Exception as e:
                logger.error(f"Failed to send reminder for ticket {ticket.id}: {e}")

        auto_close_tickets = await TicketRepo.get_awaiting_reply_tickets(hours=24)
        for ticket in auto_close_tickets:
            try:
                await TicketRepo.auto_close_ticket(ticket.id)
                await notify_ticket_auto_closed(
                    user_id=ticket.user_id,
                    ticket_id=ticket.id,
                    subject=ticket.subject,
                )
                logger.info(f"Auto-closed ticket {ticket.id}")
            except Exception as e:
                logger.error(f"Failed to auto-close ticket {ticket.id}: {e}")

    except Exception as e:
        logger.error(f"Error checking tickets: {e}")
