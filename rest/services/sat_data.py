import os
import pickle
from datetime import datetime
from redis import Redis
from skyfield.api import utc
from ..tasks import get_sat_data

redis = Redis.from_url(os.getenv('REDIS_URL'))

def sat_data():
  global sat_data_cache
  global sat_data_cache_updated_at

  updated_at = redis.get('sat_data_updated_at')
  if updated_at is not None:
    redis_updated_at = datetime.fromisoformat(updated_at.decode('ascii'))
    if sat_data_cache_updated_at is None or redis_updated_at > sat_data_cache_updated_at:
      data = redis.get('sat_data')
      if data is not None:
        sat_data_cache = pickle.loads(data)
        sat_data_cache_updated_at = datetime.now(tz=utc)

  if sat_data_cache is None:
    get_sat_data()
    return sat_data()

  return sat_data_cache


sat_data_cache = None
sat_data_cache_updated_at = None
