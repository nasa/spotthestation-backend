import os
import pickle
from datetime import datetime
from redis import Redis
from skyfield.api import utc
from ..tasks import get_astronauts

redis = Redis.from_url(os.getenv('REDIS_URL'))

def astronauts():
    global astronauts_cache_updated_at
    global astronauts_cache

    updated_at = redis.get('astronauts_updated_at')
    if updated_at is not None:
        redis_updated_at = datetime.fromisoformat(updated_at.decode('ascii'))
        print(redis_updated_at)
        print(astronauts_cache_updated_at)
        if astronauts_cache_updated_at is None or redis_updated_at > astronauts_cache_updated_at:
            data = redis.get('astronauts')
            if data is not None:
                astronauts_cache = pickle.loads(data)
                astronauts_cache_updated_at = datetime.now(tz=utc)

    if astronauts_cache is None:
        get_astronauts()
        return astronauts()

    return astronauts_cache


def last_updated():
    updated_at = redis.get('astronauts_updated_at')
    if updated_at is None:
        return None

    return updated_at.decode('ascii')

astronauts_cache = None
astronauts_cache_updated_at = None
