from celery import shared_task
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from redis import Redis
import os
import pickle
import numpy
from splines import CatmullRom

from skyfield.constants import AU_M
from skyfield.positionlib import ICRS
from skyfield.api import load
from skyfield.toposlib import Topos

from skyfield.api import utc
from datetime import datetime, timedelta
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
    raw_epoches = list(map(format_epoch, state_vectors))
    eph = load('de421.bsp')
    earth = eph['earth']
    ts = load.timescale()

    epoches = []
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

        steps = max(1, int((end - start).total_seconds() // 15))

        for j in range(steps):
            t0 = i
            t1 = i + 1
            t = t0 + (t1 - t0) * (j / steps)
            pt = curve.evaluate(t)
            date = (start + timedelta(seconds=j*15))

            r, v = GCRF_to_ITRF(pt, epoches[i]['velocity'], date, earth_positions)
            t = Topos_xyz(r[0], r[1], r[2])

            epos = earth.at(ts.from_datetime(date)).position.km
            pos = (earth + Topos(t.latitude.degrees, t.longitude.degrees)).at(ts.from_datetime(date)).position.km
            er = numpy.sqrt(((pos - epos) ** 2).sum())

            if j == 0:
                sat.append({
                    'date': date,
                    'location': r,
                    'altitude': ICRS((pt[0] * 1000 / AU_M, pt[1] * 1000 / AU_M,
                                      pt[2] * 1000 / AU_M)).distance().km - er
                })

            interpolated_sat.append({
                'date': date,
                'location': r,
                'altitude': ICRS((pt[0] * 1000 / AU_M, pt[1] * 1000 / AU_M,
                                  pt[2] * 1000 / AU_M)).distance().km - er
            })

    redis.set('sat_data', pickle.dumps(interpolated_sat))
    redis.set('sat_data_not_interpolated', pickle.dumps(sat))
    redis.set('sat_data_updated_at', datetime.now(tz=utc).isoformat())
    return interpolated_sat