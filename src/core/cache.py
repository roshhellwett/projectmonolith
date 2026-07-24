import asyncio
import functools
import time
from cachetools import TTLCache

def async_ttl_cache(ttl=60, maxsize=128):
    """
    An asynchronous TTL cache decorator.
    """
    cache = TTLCache(maxsize=maxsize, ttl=ttl)

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key in cache:
                return cache[key]
            
            result = await func(*args, **kwargs)
            cache[key] = result
            return result
        return wrapper
    return decorator
