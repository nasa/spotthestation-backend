import math
import requests
import datetime as dt
from skyfield import almanac
from skyfield.api import load

def chunks(lst, n):
  for i in range(0, len(lst), n):
    yield lst[i:i + n]

def deg_to_compass(d):
  return ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"] [math.floor(((d+(360/16)/2)%360)/(360/16))]

def datetime_range(start, end, delta):
  current = start
  while current < end:
      yield current
      current += delta

def download(url):
  get_response = requests.get(url,stream=True)
  file_name  = url.split("/")[-1]
  with open("log/" + file_name, 'wb') as f:
    for chunk in get_response.iter_content(chunk_size=1024):
      if chunk:
        f.write(chunk)

def get_comment_value(value): 
  return float(value.split("=")[-1])

def format_epoch(value): 
  return {
    'date': dt.strptime(value.find('EPOCH').text, "%Y-%jT%H:%M:%S.%fZ").strftime("%Y-%m-%dT%H:%M:%S.%f"),
    'location': [float(value.find('X').text), float(value.find('Y').text), float(value.find('Z').text)],
    'velocity': [float(value.find('X_DOT').text), float(value.find('Y_DOT').text), float(value.find('Z_DOT').text)],
  }

def calculate_twinlites(bluffton, now, zone):
  midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
  next_midnight = midnight + dt.timedelta(days=1)

  ts = load.timescale()
  t0 = ts.from_datetime(midnight)
  t1 = ts.from_datetime(next_midnight)
  eph = load('de421.bsp')

  f = almanac.dark_twilight_day(eph, bluffton)
  times, events = almanac.find_discrete(t0, t1, f)

  res = []
  for t, _ in zip(times, events):
    res.append(t.astimezone(zone))

  return res
