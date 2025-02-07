import os
import pickle
from datetime import datetime
from redis import Redis
from skyfield.api import utc
from ..tasks import get_youtube_livestream_id

redis = Redis.from_url(os.getenv('REDIS_URL'))

def youtube_livestream_id():
    global youtube_livestream_id_cache_updated_at
    global youtube_livestream_id_cache

    updated_at = redis.get('youtube_livestream_id_updated_at')
    if updated_at is not None:
        redis_updated_at = datetime.fromisoformat(updated_at.decode('ascii'))
        print(redis_updated_at)
        print(youtube_livestream_id_cache_updated_at)
        if youtube_livestream_id_cache_updated_at is None or redis_updated_at > youtube_livestream_id_cache_updated_at:
            data = redis.get('youtube_livestream_id')
            if data is not None:
                youtube_livestream_id_cache = pickle.loads(data)
                youtube_livestream_id_cache_updated_at = datetime.now(tz=utc)

    if youtube_livestream_id_cache is None:
        result = get_youtube_livestream_id()
        if result is True:
            return youtube_livestream_id()

    return youtube_livestream_id_cache


def last_updated():
    updated_at = redis.get('youtube_livestream_id_updated_at')
    if updated_at is None:
        return None

    return updated_at.decode('ascii')

youtube_livestream_id_cache = None
youtube_livestream_id_cache_updated_at = None
