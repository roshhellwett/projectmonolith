from datetime import datetime

from utils.time_util import get_now_ist, utc_now


class TestTimeUtil:
    def test_utc_now_returns_naive_utc(self):
        now = utc_now()
        assert isinstance(now, datetime)
        assert now.tzinfo is None

    def test_get_now_ist_returns_aware_ist(self):
        now = get_now_ist()
        assert isinstance(now, datetime)
        assert now.tzinfo is not None
        assert str(now.tzinfo) == "Asia/Kolkata"
