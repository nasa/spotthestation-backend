from celery import shared_task
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from redis import Redis
import os
import pickle

from skyfield.api import utc
from datetime import datetime
from .services.helpers import (
    download, linear_interpolation, format_epoch, GCRF_to_ITRF, earthPositions
)

load_dotenv()

redis = Redis.from_url(os.getenv('REDIS_URL'))

@shared_task
def get_sat_data():
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
    redis.set('sat_data', pickle.dumps(sat_data))
    return sat_data
