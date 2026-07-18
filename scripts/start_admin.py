import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from run_admin_bot import start_service  # noqa: E402

if __name__ == "__main__":
    import asyncio

    asyncio.run(start_service())
