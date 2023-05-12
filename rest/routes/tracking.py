from math import ceil
import numpy
import requests
import requests_cache
import xml.etree.ElementTree as ET
import gzip

from flask import Blueprint, json, make_response, jsonify, request, current_app
from skyfield.api import EarthSatellite, load, utc, wgs84
from datetime import datetime, timedelta
from pytz import timezone
from ..services.helpers import (
  Topos_xyz, datetime_range, calculate_day_stage, download, ECEF_to_look_angles, get_comment_value, linear_interpolation, format_epoch, chunks, deg_to_compass, calculate_twinlites, GCRF_to_ITRF, find_events, earthPositions
)

requests_cache.install_cache(cache_name='local_cache', expire_after=3600)

bp = Blueprint('tracking', __name__, url_prefix='/tracking')
sat_data = None

@bp.route('')
def index():
  ts = load.timescale()
  norad = requests.get("https://celestrak.org/NORAD/elements/gp.php?NAME=ISS%20(ZARYA)&FORMAT=TLE").text.splitlines()
  satellite = EarthSatellite(norad[1], norad[2], norad[0], ts)

  f = open("log/track-log-" + datetime.today().strftime("%Y-%m-%d %H:%M:%S") + ".txt", "w")
  res = []

  current_date = datetime.now(tz=utc)

  for t in datetime_range(current_date, current_date + timedelta(days=5), timedelta(minutes=4)):
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

@bp.route('/nasa')
def getNasaData():
  download("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
  download("http://www.celestrak.com/SpaceData/EOP-All.txt")
  result = ET.parse("ISS.OEM_J2K_EPH.xml").getroot().find("oem").find("body").find("segment")
  metadata = result.find("metadata")
  comments = result.find("data").findall("COMMENT")
  state_vectors = result.find("data").findall("stateVector")

  obj = {
    'id': metadata.find("OBJECT_ID").text,
    'name': metadata.find("OBJECT_NAME").text,
    'centerName': metadata.find("CENTER_NAME").text,
    'mass': get_comment_value(comments[1].text),
    'dragArea': get_comment_value(comments[2].text),
    'gragCoefficient': get_comment_value(comments[3].text), 
    'solarRadArea': get_comment_value(comments[4].text), 
    'solarRadCoefficient': get_comment_value(comments[5].text),
    'epoches': list(map(format_epoch, state_vectors[0:1550:]))
  }

  content = gzip.compress(json.dumps(obj, separators=(',', ':')).encode('utf8'), 9)
  response = make_response(content)
  response.headers['Content-length'] = len(content)
  response.headers['Content-Encoding'] = 'gzip'
  return response

@bp.route('/tle-predict-for-location')
def getTLEPredictedSightings():
  lon = float(request.args.get('lon'))
  lat = float(request.args.get('lat'))
  zone = timezone(request.args.get('zone'))
  ts = load.timescale()
  norad = requests.get("https://celestrak.org/NORAD/elements/gp.php?NAME=ISS%20(ZARYA)&FORMAT=TLE").text.splitlines()
  iss = EarthSatellite(norad[1], norad[2], norad[0], ts)
  location = wgs84.latlon(lat, lon)
  t0 = ts.from_datetime(zone.localize(datetime.fromisoformat('2023-02-03')))
  t1 = ts.from_datetime(zone.localize(datetime.fromisoformat('2023-02-19')))
  t, events = iss.find_events(location, t0, t1, 10)
  
  res = []

  for event in chunks(list(zip(t, events)), 3):
    ti0, _ = event[0]
    ti1, _ = event[1]
    ti2, _ = event[2]

    twinlites = calculate_twinlites(location, ti1.astimezone(zone), zone)
    if ti0.astimezone(zone) <= twinlites[2] or ti2.astimezone(zone) >= twinlites[4]:
      maxHeight, _, _ = (iss - location).at(ti1).altaz()
      appears_altitude, appears_azimut, _ = (iss - location).at(ti0).altaz()
      disappears_altitude, disappears_azimut, _ = (iss - location).at(ti2).altaz()

      item = {
        'date': ti0.astimezone(zone).strftime('%a %b %-d, %-I:%M %p'),
        'maxHeight': round(maxHeight.degrees),
        'appears': str(round(appears_altitude.degrees)) + " " + deg_to_compass(appears_azimut.degrees),
        'disappears': str(round(disappears_altitude.degrees)) + " " + deg_to_compass(disappears_azimut.degrees),
        'visible': ceil((ti2.astimezone(zone) - ti0.astimezone(zone)).seconds / 60.0)
      }

      res.append(item)

  return jsonify(res)

@bp.route('/oem-nasa')
def getOemNasa():
  global sat_data
  current_app.logger.error('**********')
  current_app.logger.error(request.args)
  lon = float(request.args.get('lon'))
  lat = float(request.args.get('lat'))
  zone = timezone(request.args.get('zone'))
  ts = load.timescale()
  sat = sat_data or get_sat_data()
  current_app.logger.error('...Events1...')
  events = find_events(sat, [lat, lon, 0], 10)
  res = []
  
  current_app.logger.error('...Events...')
  for event in events:
    ti0 = ts.from_datetime(event['start_time'].replace(tzinfo=utc))
    ti1 = ts.from_datetime(event['max_elevation_time'].replace(tzinfo=utc))
    ti2 = ts.from_datetime(event['end_time'].replace(tzinfo=utc))

    twinlites = calculate_twinlites(wgs84.latlon(lat, lon), ti1.astimezone(zone), zone)
    day_stage = calculate_day_stage(twinlites, ti1.astimezone(zone))
    # if ti0.astimezone(zone) <= twinlites[2] or ti2.astimezone(zone) >= twinlites[4]:
    if twinlites[0] < ti1.astimezone(zone) < twinlites[2] or twinlites[4] < ti1.astimezone(zone) < twinlites[len(twinlites) - 1]:
      item = {
        'date': ti0.astimezone(zone).strftime("%Y-%m-%dT%H:%M:%S.%f"),
        'maxHeight': round(event['max_elevation']),
        'appears': str(round(event['min_altitude'])) + " " + deg_to_compass(event['min_azimut']),
        'disappears': str(round(event['max_altitude'])) + " " + deg_to_compass(event['max_azimut']),
        'visible': ceil((ti2.astimezone(zone) - ti0.astimezone(zone)).seconds / 60.0),
        'dayStage': day_stage
      }
      res.append(item)

  current_app.logger.error('==========')
  return jsonify(res)

@bp.route('/iss-data')
def getISSPath():
  global sat_data
  current_app.logger.error('**********')
  current_app.logger.error(request.args)
  lon = float(request.args.get('lon'))
  lat = float(request.args.get('lat'))
  
  interpolated_data = sat_data or get_sat_data()

  # Limit the data to the +/- 100 min from now
  start_dt = (datetime.utcnow() - timedelta(minutes=100)).replace(tzinfo=utc)
  end_dt = (datetime.utcnow() + timedelta(minutes=100)).replace(tzinfo=utc)

  res = []
  for position in interpolated_data:
    date = position['date']
    if date < start_dt or date > end_dt:
      continue

    t = Topos_xyz(position['location'][0], position['location'][1], position['location'][2])
    Az, El, range_set = ECEF_to_look_angles(lat, lon, 0, position['location'][0], position['location'][1], position['location'][2])
    res.append({
      'date': position['date'],
      'latitude': t.latitude.degrees,
      'longitude': t.longitude.degrees,
      'azimuth': numpy.rad2deg(Az),
      'elevation': numpy.rad2deg(El)
    })

  return jsonify(res)

def get_sat_data():
  global sat_data
  download("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
  download("http://www.celestrak.com/SpaceData/EOP-All.txt")
  
  earth_positions = earthPositions()
  result = ET.parse("ISS.OEM_J2K_EPH.xml").getroot().find("oem").find("body").find("segment")
  state_vectors = result.find("data").findall("stateVector")
  epoches = list(map(format_epoch, state_vectors))

  sat = []
  for epoch in epoches:
    date = datetime.strptime(epoch['date'], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=utc)
    r, v = GCRF_to_ITRF(epoch['location'], epoch['velocity'], date, earth_positions)

    sat.append({
      'date': date,
      'location': r,
      'velocity': v
    })
  sat_data = linear_interpolation(sat, 60)
  return sat_data
