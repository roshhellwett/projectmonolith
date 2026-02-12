from datetime import datetime
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import UserStrike

STRIKE_LIMIT = 3
MUTE_DURATION_SECONDS = 3600

async def add_strike(user_id: int) -> bool:
    """Increments strikes in the database. Returns True if limit reached."""
    async with AsyncSessionLocal() as db:
        stmt = select(UserStrike).where(UserStrike.user_id == user_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            record = UserStrike(user_id=user_id, strike_count=1, last_violation=datetime.utcnow())
            db.add(record)
        else:
            record.strike_count += 1
            record.last_violation = datetime.utcnow()

        await db.commit()
        
        if record.strike_count >= STRIKE_LIMIT:
            # Reset strikes after triggering a mute
            record.strike_count = 0
            await db.commit()
            return True
            
        return False