from celery import shared_task
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from redis import Redis
import os
import pickle
import numpy

from skyfield.constants import AU_M
from skyfield.positionlib import ICRS
from skyfield.api import load
from skyfield.toposlib import Topos

from skyfield.api import utc
from datetime import datetime
from .services.helpers import (
    format_epoch, GCRF_to_ITRF, earthPositions, Topos_xyz, linear_interpolation, download
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
    eph = load('de421.bsp')
    earth = eph['earth']
    ts = load.timescale()

    sat = []
    for epoch in epoches:
        date = datetime.strptime(epoch['date'], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=utc)
        r, v = GCRF_to_ITRF(epoch['location'], epoch['velocity'], date, earth_positions)
        t = Topos_xyz(r[0], r[1], r[2])

        epos = earth.at(ts.from_datetime(date)).position.km
        pos = (earth + Topos(t.latitude.degrees, t.longitude.degrees)).at(ts.from_datetime(date)).position.km
        er = numpy.sqrt(((pos - epos) ** 2).sum())

        sat.append({
            'date': date,
            'location': r,
            'velocity': v,
            'altitude': ICRS((r[0] * 1000 / AU_M, r[1] * 1000 / AU_M,
                             r[2] * 1000 / AU_M)).distance().km - er
        })

    sat_data = linear_interpolation(sat, 16)
    redis.set('sat_data', pickle.dumps(sat_data))
    redis.set('sat_data_not_interpolated', pickle.dumps(sat))
    redis.set('sat_data_updated_at', datetime.now(tz=utc).isoformat())
    return sat_data
