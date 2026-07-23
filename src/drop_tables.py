import asyncio
from core.database import get_engine, Base
from sqlalchemy import text
from zenith_crypto_bot.models import Subscription, ActivationKey

async def main():
    engine = get_engine()
    async with engine.begin() as conn:
        print("Dropping tables...")
        await conn.execute(text("DROP TABLE IF EXISTS crypto_subscriptions CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS crypto_activation_keys CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS group_subscriptions CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS group_activation_keys CASCADE;"))
        print("Tables dropped.")
        
if __name__ == "__main__":
    asyncio.run(main())
