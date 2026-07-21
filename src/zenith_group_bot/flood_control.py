import time
from collections import deque

from cachetools import TTLCache

user_message_history = TTLCache(maxsize=2000, ttl=5.0)
seen_albums = TTLCache(maxsize=1000, ttl=10.0)

user_command_history = TTLCache(maxsize=2000, ttl=60.0)
user_command_count = TTLCache(maxsize=2000, ttl=3600)
user_cooldowns = TTLCache(maxsize=2000, ttl=60)

user_warnings = TTLCache(maxsize=1000, ttl=86400)


def is_flooding(user_id: int, media_group_id: str = None, strength: str = "medium") -> tuple[bool, str]:
    now = time.time()

    if media_group_id:
        if media_group_id in seen_albums:
            return False, ""
        seen_albums[media_group_id] = True

    thresholds = {"low": 8, "medium": 5, "strict": 3}
    limit = thresholds.get(strength, 5)

    if user_id not in user_message_history:
        user_message_history[user_id] = deque(maxlen=limit)

    history = user_message_history[user_id]
    history.append(now)

    if len(history) == limit and (history[-1] - history[0] < 3.0):
        return True, "Message Flooding (Spamming)"

    return False, ""


def check_bot_command_limit(user_id: int, is_pro: bool = False) -> tuple[bool, str, int]:
    now = time.time()

    if user_id in user_cooldowns:
        remaining = int(user_cooldowns[user_id] - now)
        if remaining > 0:
            return True, f"Cooldown active. Wait {remaining}s", remaining
        else:
            user_cooldowns.pop(user_id, None)

    cooldown = 5 if is_pro else 15
    max_per_minute = 20 if is_pro else 5
    max_per_hour = 200 if is_pro else 50

    user_command_count[user_id] = user_command_count.get(user_id, 0) + 1

    count = user_command_count[user_id]
    if count > max_per_hour:
        return True, f"Hourly limit exceeded ({max_per_hour}/hour)", -1

    if user_id in user_command_history:
        recent_cmds = user_command_history[user_id]
        while recent_cmds and now - recent_cmds[0] > 60.0:
            recent_cmds.popleft()
        recent_cmds.append(now)

        if len(recent_cmds) > max_per_minute:
            return True, f"Rate limit exceeded ({max_per_minute}/min)", -1
    else:
        user_command_history[user_id] = deque(maxlen=max_per_minute)
        user_command_history[user_id].append(now)

    user_cooldowns[user_id] = now + cooldown

    return False, "", 0


def get_warning_count(user_id: int) -> int:
    return user_warnings.get(user_id, 0)


def add_warning(user_id: int) -> int:
    current = user_warnings.get(user_id, 0)
    user_warnings[user_id] = current + 1
    return user_warnings[user_id]


def clear_warnings(user_id: int):
    user_warnings.pop(user_id, None)


def get_flood_action(warning_count: int, is_pro: bool = False) -> tuple[str, int]:
    if is_pro:
        if warning_count >= 5:
            return "kick", 3600
        elif warning_count >= 3:
            return "mute", 1800
        else:
            return "warn", 0
    else:
        if warning_count >= 3:
            return "kick", 86400
        elif warning_count >= 2:
            return "mute", 3600
        else:
            return "warn", 0
