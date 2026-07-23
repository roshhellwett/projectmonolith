import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("src"))

from core.database import get_engine, Base

# Import all models to ensure they are registered with Base.metadata
from zenith_admin_bot import models as admin_models
from zenith_ai_bot import models as ai_models
from zenith_crypto_bot import models as crypto_models
from zenith_group_bot import models as group_models
from zenith_support_bot import models as support_models

async def run_migration():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Migration complete. All tables across the whole project have been checked and created if missing.")

if __name__ == "__main__":
    asyncio.run(run_migration())
