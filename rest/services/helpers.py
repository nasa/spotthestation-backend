import requests
from datetime import datetime

def chunks(lst, n):
  for i in range(0, len(lst), n):
    yield lst[i:i + n]

def deg_to_compass(d):
  return ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"] [round(((d+(360/16)/2)%360)/(360/16))]

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
    'date': datetime.strptime(value.find('EPOCH').text, "%Y-%jT%H:%M:%S.%fZ").strftime("%Y-%m-%dT%H:%M:%S.%f"),
    'location': [float(value.find('X').text), float(value.find('Y').text), float(value.find('Z').text)],
    'velocity': [float(value.find('X_DOT').text), float(value.find('Y_DOT').text), float(value.find('Z_DOT').text)],
  }
