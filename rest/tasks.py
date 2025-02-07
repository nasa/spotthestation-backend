import numpy as np
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from redis import Redis
import os
import pickle
import numpy
import requests
from splines import CatmullRom
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs


from skyfield.constants import AU_M
from skyfield.positionlib import ICRS
from skyfield.api import load
from skyfield.toposlib import Topos

from skyfield.api import utc
from datetime import datetime, timedelta
from .services.helpers import (
    format_epoch, GCRF_to_ITRF, earthPositions, Topos_xyz, linear_interpolation, download, is_in_shadow
)

load_dotenv()

redis = Redis.from_url(os.getenv('REDIS_URL'))

def get_sat_data():
    download("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
    download("http://www.celestrak.com/SpaceData/EOP-All.txt")

    earth_positions = earthPositions()
    result = ET.parse("ISS.OEM_J2K_EPH.xml").getroot().find("oem").find("body").find("segment")
    state_vectors = result.find("data").findall("stateVector")
    raw_epoches = list(map(format_epoch, state_vectors))
    eph = load('de421.bsp')
    earth = eph['earth']
    sun = eph['sun']
    ts = load.timescale()

    epoches = []
    shadow_intervals = []
    shadow_start = None
    for i in range(len(raw_epoches) - 1):
        date = datetime.strptime(raw_epoches[i]['date'], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=utc)

        if len(epoches) == 0 or (date - epoches[-1]['date']).total_seconds() >= 60 * 4:
            epoches.append({
                'date': date,
                'location': raw_epoches[i]['location'],
                'velocity': raw_epoches[i]['velocity']
            })

    spline_points = []
    for epoch in epoches:
        spline_points.append((epoch['location'][0], epoch['location'][1], epoch['location'][2]))

    curve = CatmullRom(spline_points)
    sat = []
    interpolated_sat = []

    for i in range(len(epoches) - 1):
        start = epoches[i]['date']
        end = epoches[i + 1]['date']

        steps = max(1, int((end - start).total_seconds() // 5))

        for j in range(steps):
            t0 = i
            t1 = i + 1
            t = t0 + (t1 - t0) * (j / steps)
            pt = curve.evaluate(t)
            date = (start + timedelta(seconds=j*5))

            if j == 0:
                r, v = GCRF_to_ITRF(pt, epoches[i]['velocity'], date, earth_positions)
                t = Topos_xyz(r[0], r[1], r[2])

                epos = earth.at(ts.from_datetime(date)).position.km
                pos = (earth + Topos(t.latitude.degrees, t.longitude.degrees)).at(ts.from_datetime(date)).position.km
                er = numpy.sqrt(((pos - epos) ** 2).sum())
                sat.append({
                    'date': date,
                    'location': r,
                    'altitude': ICRS((pt[0] * 1000 / AU_M, pt[1] * 1000 / AU_M,
                                      pt[2] * 1000 / AU_M)).distance().km - er
                })

            sun_m = earth.at(ts.from_datetime(date)).observe(sun).position.m
            in_shadow = is_in_shadow(sun_m, np.array([pt[0] * 1000, pt[1] * 1000, pt[2] * 1000]))
            if in_shadow == True and shadow_start is None:
                shadow_start = date

            if in_shadow == False and shadow_start is not None:
                shadow_intervals.append([shadow_start.timestamp(), date.timestamp()])
                shadow_start = None

    if shadow_start is not None:
        shadow_intervals.append([shadow_start.timestamp(), epoches[-1]['date'].timestamp()])

    redis.set('shadow_intervals', pickle.dumps(shadow_intervals))
    # Save to temporary key to avoid blocking current value
    redis.set('sat_data_new', pickle.dumps(sat))
    redis.rename('sat_data_new', 'sat_data_not_interpolated')
    redis.set('sat_data_updated_at', datetime.now(tz=utc).isoformat())
    return interpolated_sat

def get_astronauts():
    try:
        url = "https://www.nasa.gov/humans-in-space/astronauts/"
        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            container = soup.find(class_="hds-meet-the")
            astronaut_cards = container.find_all(class_='hds-meet-the-card')
            astronauts = []

            for card in astronaut_cards:
                image = card.find('img')['src']
                name = card.find('h3').get_text()
                title = card.find('p').get_text()
                link = card.find('a')['href']

                parsed_url = urlparse(image)
                existing_params = parse_qs(parsed_url.query)
                existing_params.update({ 'w': '700', 'h': '700' })

                encoded_params = urlencode(existing_params, doseq=True)
                resized_image = urlunparse(parsed_url._replace(query=encoded_params))

                astronauts.append({
                    'image': resized_image,
                    'name': name,
                    'title': title,
                    'link': link
                })

            redis.set('astronauts', pickle.dumps(astronauts))
            redis.set('astronauts_updated_at', datetime.now(tz=utc).isoformat())
        else:
            print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
    except Exception as e:
        print(f"Failed to parse the webpage: {e}")


def get_youtube_livestream_id():
    api_key = os.getenv('GOOGLE_API_TOKEN')
    channel_id = os.getenv('YT_CHANNEL_ID')
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=id,snippet&channelId={channel_id}&type=video&eventType=live&key={api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            items = list(reversed(data['items']))
            video_id = ""

            if len(items) > 0:
                video_id = items[0]['id']['videoId']
                for item in items:
                    if 'international space station' in item['snippet']['title'].lower():
                        video_id = item['id']['videoId']
                        break

            redis.set('youtube_livestream_id', pickle.dumps(video_id))
            redis.set('youtube_livestream_id_updated_at', datetime.now(tz=utc).isoformat())
            return True
        else:
            print(f"Failed to retrieve youtube livestream id. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Failed to retrieve youtube livestream id: {e}")
        return False

