import requests

from flask import Blueprint, jsonify
from skyfield.api import EarthSatellite, load, utc
from datetime import datetime, timedelta

bp = Blueprint('tracking', __name__, url_prefix='/tracking')

def datetime_range(start, end, delta):
  current = start
  while current < end:
      yield current
      current += delta

@bp.route('')
def index():
  ts = load.timescale()
  norad = requests.get("https://celestrak.org/NORAD/elements/gp.php?NAME=ISS%20(ZARYA)&FORMAT=TLE").text.splitlines()
  satellite = EarthSatellite(norad[1], norad[2], norad[0], ts)

  f = open("log/track-log-" + datetime.today().strftime("%Y-%m-%d %H:%M:%S") + ".txt", "w")
  res = []

  current_date = datetime.now(tz=utc)

  for t in datetime_range(current_date, current_date + timedelta(days=4), timedelta(minutes=1)):
    geocentric = satellite.at(ts.from_datetime(t))
    
    obj = {
      'time': t.strftime("%Y-%m-%dT%H:%M:%S.%f"),
      'position': geocentric.position.km.tolist(),
      'velocity': geocentric.velocity.km_per_s.tolist(),
      'location': str(geocentric.subpoint())
    }

    f.write(obj['time'] 
    + "\n\t\tPosition: " + str(obj['position'])
    + "\n\t\tVelocity: " + str(obj['velocity'])
    + "\n\t\tLocation: " + obj['location']
    + "\n")

    res.append(obj)

  f.close()

  return jsonify(res)
