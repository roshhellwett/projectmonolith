import pytest

from zenith_support_bot.models import SupportTicket, TicketStatus


class TestTicketStatusEnum:
    def test_has_expected_values(self):
        statuses = {e.value for e in TicketStatus}
        assert "open" in statuses
        assert "closed" in statuses
        assert "resolved" in statuses


class TestSupportModels:
    def test_support_ticket_model(self):
        assert SupportTicket.__tablename__ == "zenith_support_tickets"

    def test_ticket_has_expected_columns(self):
        columns = {c.name for c in SupportTicket.__table__.c}
        assert "id" in columns
        assert "user_id" in columns
        assert "status" in columns
        assert "created_at" in columns

    def test_faq_model_exists(self):
        from zenith_support_bot.models import FAQEntry

        assert FAQEntry.__tablename__ == "zenith_support_faq"

    def test_canned_response_model(self):
        from zenith_support_bot.models import CannedResponse

        assert CannedResponse.__tablename__ == "zenith_support_canned"


class TestSupportAiResponder:
    def test_generate_ai_response_exists(self):
        from zenith_support_bot.ai_responder import generate_ai_response

        assert callable(generate_ai_response)


class TestSupportNotifications:
    def test_notifications_import(self):
        import zenith_support_bot.notifications


class TestSupportScheduler:
    def test_scheduler_import(self):
        import zenith_support_bot.scheduler


class TestSupportUserHandlers:
    def test_user_handlers_import(self):
        import zenith_support_bot.user_handlers


class TestSupportProHandlers:
    def test_pro_handlers_import(self):
        import zenith_support_bot.pro_handlers


class TestSupportAiTriage:
    @pytest.mark.asyncio
    async def test_triage_support_ticket_exists_and_fallback(self, monkeypatch):
        from zenith_support_bot.ai_responder import triage_support_ticket

        assert callable(triage_support_ticket)
        # Test fallback behavior when API key is missing or fails
        monkeypatch.setattr("zenith_support_bot.ai_responder.get_groq_api_key", lambda prefer_support=True: None)
        category, priority, reply = await triage_support_ticket("Billing issue", "I was charged twice on my invoice")
        assert category == "general"
        assert priority == "normal"
        assert "support team will review it shortly" in reply

    def test_notify_admin_new_ticket_signature(self):
        import inspect
        from zenith_support_bot.notifications import notify_admin_new_ticket

        sig = inspect.signature(notify_admin_new_ticket)
        assert "priority" in sig.parameters
        assert "category" in sig.parameters
        assert "suggested_reply" in sig.parameters
