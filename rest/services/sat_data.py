import os
import pickle
from datetime import datetime
from redis import Redis
from skyfield.api import utc
from ..tasks import get_sat_data

redis = Redis.from_url(os.getenv('REDIS_URL'))

def sat_data():
  global sat_data_cache_updated_at
  global sat_data_not_interpolated_cache
  global shadow_intervals_cache

  updated_at = redis.get('sat_data_updated_at')
  if updated_at is not None:
    redis_updated_at = datetime.fromisoformat(updated_at.decode('ascii'))
    if sat_data_cache_updated_at is None or redis_updated_at > sat_data_cache_updated_at:
      data = redis.get('sat_data_not_interpolated')
      shadow_data = redis.get('shadow_intervals')
      if data is not None and shadow_data is not None:
        sat_data_not_interpolated_cache = pickle.loads(data)
        shadow_intervals_cache = pickle.loads(shadow_data)
        sat_data_cache_updated_at = datetime.now(tz=utc)

  if sat_data_not_interpolated_cache is None:
    get_sat_data()
    return sat_data()

  return {
    "points": sat_data_not_interpolated_cache,
    "shadow_intervals": shadow_intervals_cache
  }


def last_updated():
  updated_at = redis.get('sat_data_updated_at')
  if updated_at is None:
    return None

  return updated_at.decode('ascii')

sat_data_not_interpolated_cache = None
shadow_intervals_cache = None
sat_data_cache_updated_at = None
