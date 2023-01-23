import requests
import xml.etree.ElementTree as ET
import gzip

from flask import Blueprint, json, make_response, jsonify
from skyfield.api import EarthSatellite, load, utc
from datetime import datetime, timedelta

bp = Blueprint('tracking', __name__, url_prefix='/tracking')

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
    'date': value.find('EPOCH').text,
    'location': [float(value.find('X').text), float(value.find('Y').text), float(value.find('Z').text)],
    'velocity': [float(value.find('X_DOT').text), float(value.find('Y_DOT').text), float(value.find('Z_DOT').text)],
  }
  

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

@bp.route('/nasa')
def getNasaData():
  download("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
  result = ET.parse("log/ISS.OEM_J2K_EPH.xml").getroot().find("oem").find("body").find("segment")
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
  