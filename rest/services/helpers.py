from math import sin, cos, pi, floor, trunc, atan2, sqrt, asin, radians, degrees
import numpy
import requests
import datetime as dt
from skyfield import almanac
from skyfield.api import load, utc
from skyfield.searchlib import _find_discrete, _choose_brackets, _identify_maxima, _remove_adjacent_duplicates, _trace, _fix_numpy_deprecation
from .constants import omegaEarth, const_Arcs, JD_J2000_0, DJC, DAS2R, TURNAS, s0, s01, s02, s1, s11, s12, s2, s21, s22, s3, s31, s32, s4, s41, s42, DAY_S, no_kozai, tau

_identity = numpy.identity(3)

def diag3():
  return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]

def chunks(lst, n):
  for i in range(0, len(lst), n):
    yield lst[i:i + n]

def deg_to_compass(d):
  return ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"] [floor(((d+(360/16)/2)%360)/(360/16))]

def datetime_range(start, end, delta):
  current = start
  while current < end:
      yield current
      current += delta

def download(url):
  get_response = requests.get(url,stream=True)
  file_name  = url.split("/")[-1]
  with open(file_name, 'wb') as f:
    for chunk in get_response.iter_content(chunk_size=1024):
      if chunk:
        f.write(chunk)

def get_comment_value(value): 
  return float(value.split("=")[-1])

def format_epoch(value): 
  return {
    'date': dt.datetime.strptime(value.find('EPOCH').text, "%Y-%jT%H:%M:%S.%fZ").strftime("%Y-%m-%dT%H:%M:%S.%f"),
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

def iauCal2jd(year, month, day, hour=0, min=0, sec=0):
  djm0 = 2400000.5
  b = 0
  c = 0
  if month <= 2:
    year = year - 1
    month = month + 12
  
  if year < 0:
    c = -0.75
  
  if year > 1582 or (year == 1582 and month > 10) or (year == 1582 and month == 10 and day > 14): 
    a = trunc(year/100)
    b = 2 - a + floor(a/4)

  jd = trunc(365.25 * year + c) + trunc(30.6001 * (month + 1))
  jd = jd + day + b + 1720994.5
  jd = jd + (hour + min/60 + sec/3600)/24
  djm = jd - djm0

  return djm0, djm

def iauObl06(date1, date2):
  t = ((date1 - JD_J2000_0) + date2) / DJC

  eps0 = (84381.406 + (-46.836769 + (-0.0001831 + (0.00200340 + (-0.000000576-0.0000000434 * t) * t) * t) * t) * t) * DAS2R
  return eps0 

def iauPfw06(date1, date2):
  t = ((date1 - JD_J2000_0) + date2) / DJC
  gamb = (-0.052928 + (10.556378 + (0.4932044 + (-0.00031238 + (-0.000002788+0.0000000260 * t) * t) * t) * t) * t) * DAS2R
  phib = (84381.412819 + (-46.811016 + (0.0511268 + (0.00053289 + (-0.000000440-0.0000000176 * t) * t) * t) * t) * t) * DAS2R
  psib = (-0.041775 + (5038.481484 + (1.5584175 + (-0.00018522 + (-0.000026452-0.0000000148 * t) * t) * t) * t) * t) * DAS2R
  epsa = iauObl06(date1, date2)

  return gamb, phib, psib, epsa

def iauFal03(t):
  return ((485868.249036 + t * (1717915923.2178 + t * (31.8792 + t * (0.051635 + t * (-0.00024470))))) % TURNAS) * DAS2R 

def iauFaf03(t):
  return ((335779.526232 + t * (1739527262.8478 + t * (-12.7512 + t * (-0.001037 + t * (0.00000417))))) % TURNAS) * DAS2R

def iauFaom03(t):
  return ((450160.398036 + t * (-6962890.5431 + t * (7.4722 + t * (0.007702 + t * (-0.00005939))))) % TURNAS) * DAS2R

def iauFalp03(t):
  return ((1287104.79305 + t * (129596581.0481 + t * (-0.5532 + t * (0.000136 + t * (-0.00001149))))) % TURNAS) * DAS2R

def iauFad03(t):
  return ((1072260.70369 + t * (1602961601.2090 + t * (-6.3706 + t * (0.006593 + t * (-0.00003169))))) % TURNAS) * DAS2R

def iauFave03(t):
  return (3.176146697 + 1021.3285546211 * t) % (2 * pi)

def iauFae03(t):
  return (1.753470314 + 628.3075849991 * t) % (2 * pi)

def iauFapa03(t):
  return (0.024381750 + 0.00000538691 * t) * t

def iauNut00a(date1, date2):
  U2R = DAS2R / 1e7
  
  t = ((date1 - JD_J2000_0) + date2) / DJC
  el = iauFal03(t)
  f = iauFaf03(t)
  d = iauFad03(t)
  om = iauFaom03(t)
  arg = (2 * el + 2 * f + 4 * d + 1 * om) % (2 * pi)
  sarg = sin(arg)
  carg = cos(arg)
  dp = -3 * sarg
  de = 2 * carg
  
  dpsils = dp * U2R
  depsls = de * U2R
    
  af = (1.627905234 + 8433.466158131 * t) % (2 * pi)
  ad = (5.198466741 + 7771.3771468121 * t) % (2 * pi)
  aom = (2.18243920 - 33.757045 * t) % (2 * pi)
  alea = iauFae03(t)
  alju = (0.599546497 + 52.9690962641 * t) % (2 * pi)

  arg = (2 * af + 2 * ad + 2 * aom + 2 * alea +(-2 * alju)) % (2 * pi)
  sarg = sin(arg)
  carg = cos(arg)
  dp = 3 * sarg
  de = -1 * carg
  
  dpsipl = dp * U2R
  depspl = de * U2R

  dpsi = dpsils + dpsipl
  deps = depsls + depspl
  
  return dpsi, deps

def iauNut06a(date1, date2): 
  t = ((date1 - JD_J2000_0) + date2) / DJC
  fj2 = -2.7774e-6 * t
  dpsi, deps = iauNut00a(date1, date2)
  dpsi = dpsi + dpsi * (0.4697e-6 + fj2)
  deps = deps + deps * fj2

  return dpsi, deps

def iauRz(psi, r):
  sin_psi = sin(psi)
  cos_psi = cos(psi)
  return [
    [cos_psi * r[0][0] + sin_psi * r[1][0], cos_psi * r[0][1] + sin_psi * r[1][1], cos_psi * r[0][2] + sin_psi * r[1][2]],
    [cos_psi * r[1][0] - sin_psi * r[0][0], cos_psi * r[1][1] - sin_psi * r[0][1], cos_psi * r[1][2] - sin_psi * r[0][2]],
    [r[2][0], r[2][1], r[2][2]]
  ]

def iauRx(phi, r):
  sin_phi = sin(phi)
  cos_phi = cos(phi)
  return [
    [r[0][0], r[0][1], r[0][2]],
    [cos_phi * r[1][0] + sin_phi * r[2][0], cos_phi * r[1][1] + sin_phi * r[2][1], cos_phi * r[1][2] + sin_phi * r[2][2]],
    [cos_phi * r[2][0] - sin_phi * r[1][0], cos_phi * r[2][1] - sin_phi * r[1][1], cos_phi * r[2][2] - sin_phi * r[1][2]]
  ]

def iauRy(theta, r):
  sin_theta = sin(theta)
  cos_theta = cos(theta)
  return [
    [cos_theta * r[0][0] - sin_theta * r[2][0], cos_theta * r[0][1] - sin_theta * r[2][1], cos_theta * r[0][2] - sin_theta * r[2][2]],
    [r[1][0], r[1][1], r[1][2]],
    [cos_theta * r[2][0] + sin_theta * r[0][0], cos_theta * r[2][1] + sin_theta * r[0][1], cos_theta * r[2][2] + sin_theta * r[0][2]]
  ]

def iauFw2m(gamb, phib, psi, eps):
  r = diag3()
  r = iauRz(gamb, r)
  r = iauRx(phib, r)
  r = iauRz(-psi, r)
  r = iauRx(-eps, r)

  return r

def iauPnm06a(date1, date2, dDeps=0, dDpsi=0):
  gamb, phib, psib, epsa = iauPfw06(date1, date2)
  dpsi, deps = iauNut06a(date1, date2)
  dpsi = dpsi + dDpsi
  deps = deps + dDeps

  return iauFw2m(gamb, phib, psib + dpsi, epsa + deps)

def iauS06(date1, date2, x, y):
  w0 = 9.4e-05
  w1 = 0.00380865
  w2 = -0.00012268
  w3 = -0.07257411
  w4 = 2.798e-05
  w5 = 1.562e-05
  t = ((date1 - JD_J2000_0) + date2) / DJC
  meanAnomalyMoon = iauFal03(t)
  meanAnomalySun = iauFalp03(t)
  meanLongitudeMoonMinusAN = iauFaf03(t)
  meanElongationMoonSun = iauFad03(t)
  meanLongitudeMoonAN = iauFaom03(t)
  meanLongitudeVenus = iauFave03(t)
  meanLongitudeEarth = iauFae03(t)
  generalLongitudeAccumulatedPrecesion = iauFapa03(t)
  fundamentalArguments = numpy.matrix([meanAnomalyMoon, meanAnomalySun, meanLongitudeMoonMinusAN,
                            meanElongationMoonSun, meanLongitudeMoonAN, meanLongitudeVenus,
                            meanLongitudeEarth, generalLongitudeAccumulatedPrecesion])

  def summ(a, b):
    return sum(numpy.multiply(numpy.matrix(a),numpy.transpose(b)).flatten().tolist()[0])

  a = numpy.multiply(numpy.matrix(s0),fundamentalArguments).sum(axis=1).flatten().tolist()
  w0 = w0 + summ(s01, numpy.sin(a)) + summ(s02, numpy.cos(a))
  a = numpy.multiply(numpy.matrix(s1),fundamentalArguments).sum(axis=1).flatten().tolist()
  w1 = w1 + summ(s11, numpy.sin(a)) + summ(s12, numpy.cos(a))
  a = numpy.multiply(numpy.matrix(s2),fundamentalArguments).sum(axis=1).flatten().tolist()
  w2 = w2 + summ(s21, numpy.sin(a)) + summ(s22, numpy.cos(a))
  a = numpy.multiply(numpy.matrix(s3),fundamentalArguments).sum(axis=1).flatten().tolist()
  w3 = w3 + summ(s31, numpy.sin(a)) + summ(s32, numpy.cos(a))
  a = numpy.multiply(numpy.matrix(s4),fundamentalArguments).sum(axis=1).flatten().tolist()
  w4 = w4 + summ(s41, numpy.sin(a)) + summ(s42, numpy.cos(a))
  
  return (w0 + (w1 + (w2 + (w3 + (w4 + w5 * t) * t) * t) * t) * t) * DAS2R - x * y / 2.0

def rem(x, y):
  return x - trunc(x / y) * y

def iauEra00(dj1, dj2):
  d1 = min([dj1, dj2])
  d2 = max([dj1, dj2])
  
  t = d1 + (d2 - JD_J2000_0)
  f = (d1 - trunc(d1)) + (d2 - trunc(d2))

  theta = rem((f + 0.7790572732640 + 0.00273781191135448 * t) * 2 * pi, (2 * pi))
  if theta < 0:
    theta = theta + 2 * pi
  
  return theta

def iauEors(rnpb, s):
  x = rnpb[2][0]
  ax =  x / (1 + rnpb[2][2])
  xs = 1 - ax * x
  ys = -ax * rnpb[2][1]
  zs = -x
  p = rnpb[0][0] * xs + rnpb[0][1] * ys + rnpb[0][2] * zs
  q = rnpb[1][0] * xs + rnpb[1][1] * ys + rnpb[1][2] * zs

  if p != 0 or q != 0: 
    return (s - atan2(q, p))
  else:
    return s
  
def iauGst06(uta, utb, tta, ttb, rnpb):
  cip_x = rnpb[2][0]
  cip_y = rnpb[2][1]
  s = iauS06(tta, ttb, cip_x, cip_y)
  era = iauEra00(uta, utb)
  eors = iauEors(rnpb, s)
  gst = rem(era - eors, 2 * pi)
  if gst < 0:
    gst = gst + 2 * pi
  
  return gst

def iauPom00(xp, yp, sp):
  return iauRx(-yp, iauRy(-xp, iauRz(sp, diag3())))

def iauSp00(date1, date2):
  t = ((date1 - JD_J2000_0) + date2) / DJC
  return -47e-6 * t * DAS2R

def timeDiffs(UT1_UTC, TAI_UTC):
  TT_TAI = 32.184
  GPS_TAI = -19.0
  TT_GPS = TT_TAI - GPS_TAI
  TAI_GPS = -GPS_TAI
  UT1_TAI = UT1_UTC - TAI_UTC
  UTC_TAI = -TAI_UTC
  UTC_GPS = UTC_TAI - GPS_TAI
  UT1_GPS = UT1_TAI - GPS_TAI
  TT_UTC = TT_TAI - UTC_TAI
  GPS_UTC = GPS_TAI - UTC_TAI
  return TT_TAI, GPS_TAI, TT_GPS, TAI_GPS, UT1_TAI, UTC_TAI, UTC_GPS, UT1_GPS, TT_UTC, GPS_UTC

def invjday(jd):
  z = trunc(jd + 0.5)
  fday = jd + 0.5 - z
  if fday < 0:
    fday = fday + 1
    z = z - 1
  
  if z < 2299161:
    a = z
  else:
    alpha = floor((z - 1867216.25) / 36524.25)
    a = z + 1 + alpha - floor(alpha/4)
  
  b = a + 1524
  c = trunc((b - 122.1) / 365.25)
  d = trunc(365.25 * c)
  e = trunc((b-d) / 30.6001)
  day = b - d - trunc(30.6001 * e) + fday
  if e < 14:
    month = e - 1
  else:
    month = e - 13

  if month > 2:
    year = c - 4716
  else:
    year = c - 4715
  
  hour = abs(day - floor(day))*24
  min = abs(hour - floor(hour))*60
  sec = abs(min - floor(min))*60
  day = floor(day)
  hour = floor(hour)
  min = floor(min)

  return year, month, day, hour, min, sec

def earthPositions():
  # raw_positions_data = requests.get("http://www.celestrak.com/SpaceData/EOP-All.txt").text.splitlines()
  # raw_positions_data = open('EOP-All.txt', 'r').readlines()
  raw_positions_data = []
  with open('EOP-All.txt', 'r') as f:
    raw_positions_data = [line.rstrip() for line in f]
  
  begin_observed = raw_positions_data.index("BEGIN OBSERVED")
  end_observed = raw_positions_data.index("END OBSERVED")
  begin_predicted = raw_positions_data.index("BEGIN PREDICTED")
  end_predicted = raw_positions_data.index("END PREDICTED")

  def split(value):
    res = value.split(" ")
    filtered = filter(lambda value: value != "", res)
    return list(map(lambda value: float(value.strip()), filtered))

  return list(map(split, raw_positions_data[begin_observed + 1:end_observed - 1:] + raw_positions_data[begin_predicted + 1:end_predicted - 1:]))

def IERS(eop, Mjd_UTC):
  mjd = floor(Mjd_UTC)
  i = 0
  for idx, line in enumerate(eop):
    if mjd == line[3]:
      i = idx
      break

  preeop = eop[i]
  nexteop = eop[i + 1]
  mfme = 1440 * (Mjd_UTC - mjd)
  fixf = mfme/1440
  
  x_pole = preeop[4] + (nexteop[4] - preeop[4]) * fixf
  y_pole = preeop[5] + (nexteop[5] - preeop[5]) * fixf
  UT1_UTC = preeop[6] + (nexteop[6] - preeop[6]) * fixf
  LOD = preeop[7] + (nexteop[7] - preeop[7]) * fixf
  dpsi = preeop[8] + (nexteop[8] - preeop[8]) * fixf
  deps = preeop[9] + (nexteop[9] - preeop[9]) * fixf
  dx_pole = preeop[10] + (nexteop[10] - preeop[10]) * fixf
  dy_pole = preeop[11] + (nexteop[11] - preeop[11]) * fixf
  TAI_UTC = preeop[12]
  x_pole = x_pole/const_Arcs
  y_pole = y_pole/const_Arcs
  dpsi = dpsi/const_Arcs
  deps = deps/const_Arcs
  dx_pole = dx_pole/const_Arcs
  dy_pole = dy_pole/const_Arcs

  return x_pole, y_pole, UT1_UTC, LOD, dpsi, deps, TAI_UTC
  
def ECI_to_ECEF(MJD_UTC, Y0, Y1):
  x_pole, y_pole, UT1_UTC, LOD, dpsi, deps, TAI_UTC = IERS(earthPositions(), MJD_UTC)
  TT_UTC = timeDiffs(UT1_UTC, TAI_UTC)[8]
  year, month, day, hour, min, sec = invjday(MJD_UTC + 2400000.5)
  DJMJD0, DATE  = iauCal2jd(year, month, day)
  TIME = (60 * (60 * hour + min) + sec)/86400
  UTC = DATE + TIME
  TT = UTC + TT_UTC/86400
  TUT = TIME + UT1_UTC/86400
  UT1 = DATE + TUT
  NPB = iauPnm06a(DJMJD0, TT, dpsi, deps)
  theta = numpy.matrix(iauRz(iauGst06(DJMJD0, UT1, DJMJD0, TT, NPB), diag3()))
  PMM = iauPom00(x_pole, y_pole, iauSp00(DJMJD0, TT))
  S = numpy.matrix([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 0.0]])

  omega = omegaEarth - 8.43994809e-10 * LOD

  dTheta = numpy.multiply(omega, S@theta)
  U = PMM@theta@NPB
  dU = PMM@dTheta@NPB
  r = U@Y0
  v = U@Y1 + dU@Y0
  return r.tolist()[0], v.tolist()[0]

def GCRF_to_ITRF(position_GCRF, velocity_GCRF, date):
  year = date.year
  month = date.month
  day = date.day
  hour = date.hour
  minute = date.minute
  second = date.second
  _, Mjd_UTC = iauCal2jd(year, month, day, hour, minute, second)

  return ECI_to_ECEF(Mjd_UTC, position_GCRF, velocity_GCRF)

def geodetic_to_ECEF(longitude, latitude, altitude):
  a = 6378.137
  b = 6356.7523142
  f = (a - b) / a
  e2 = ((2 * f) - (f * f))
  normal = a / sqrt(1 - (e2 * (sin(latitude) * sin(latitude))))

  x = (normal + altitude) * cos(latitude) * cos(longitude)
  y = (normal + altitude) * cos(latitude) * sin(longitude)
  z = ((normal * (1 - e2)) + altitude) * sin(latitude)
  return x, y, z

def topocentric(longitude, latitude, altitude, x, y, z):
  ox, oy, oz = geodetic_to_ECEF(longitude, latitude, altitude)

  rx = x - ox
  ry = y - oy
  rz = z - oz

  topS = ((sin(latitude) * cos(longitude) * rx) + (sin(latitude) * sin(longitude) * ry)) - (cos(latitude) * rz)

  topE = (-sin(longitude) * rx) + (cos(longitude) * ry)

  topZ = (cos(latitude) * cos(longitude) * rx) + (cos(latitude) * sin(longitude) * ry) + (sin(latitude) * rz)

  return topS, topE, topZ

def topocentric_to_look_angles(topS, topE, topZ):
  rangeSat = sqrt((topS * topS) + (topE * topE) + (topZ * topZ))
  El = asin(topZ / rangeSat)
  Az = atan2(-topE, topS) + pi

  return Az, El, rangeSat

def ECEF_to_look_angles(longitude, latitude, altitude, x, y, z):
  topS, topE, topZ = topocentric(radians(longitude), radians(latitude), altitude, x, y, z)
  return topocentric_to_look_angles(topS, topE, topZ)

def altaz_at(sat, topos, t, ts):
  altitudes = []
  azimuts = []
  distances = []
  
  positions = []

  for position in sat: 
    for time in list(t):
      if ts.from_datetime(position['date'].replace(tzinfo=utc)).tt == time.tt:
        positions.append(position)

  for position in positions:
    r = position['location']
    Az, El, rangeSat = ECEF_to_look_angles(topos[0], topos[1], topos[2], r[0], r[1], r[2])
    altitudes.append(degrees(El))
    azimuts.append(degrees(Az))
    distances.append(rangeSat)

  return numpy.array(altitudes), numpy.array(azimuts), numpy.array(distances)

def find_maxima(start_time, end_time, jd, f, epsilon=1.0 / DAY_S, num=12):
  ts = start_time.ts
  jd0 = start_time.tt
  jd1 = end_time.tt

  end_alpha = numpy.linspace(0.0, 1.0, num)
  start_alpha = end_alpha[::-1]
  o = numpy.multiply.outer

  while True:
    t = ts.tt_jd(jd)
    y = f(t)
    
    if t[1] - t[0] <= epsilon:
      
      jd, y = _identify_maxima(jd, y)
      keepers = (jd >= jd0) & (jd <= jd1)

      jd = jd[keepers]
      y = y[keepers]

      if len(jd):
        mask = numpy.concatenate(((True,), numpy.diff(jd) > epsilon))
        jd = jd[mask]
        y = y[mask]
      
      break

    left, right = _choose_brackets(y)
    
    if _trace is not None:
      _trace((t, y, left, right))

    if not len(left):
      jd = y = y[0:0]
      break
    
    starts = jd.take(left)
    ends = jd.take(right)
    
    jd = o(starts, start_alpha).flatten() + o(ends, end_alpha).flatten()
    
    jd = _remove_adjacent_duplicates(jd)
      
  return ts.tt_jd(jd), _fix_numpy_deprecation(y)

def get_jd(sat, ts):
  res = []
  for elem in sat:
    res.append(ts.from_datetime(elem['date'].replace(tzinfo=utc)).tt)

  return numpy.array(res)

def find_events(sat, topos, t0, t1, altitude_degrees=0.0):
  ts = t0.ts
  jd = get_jd(sat, ts)
  half_second = 0.5 / DAY_S
  
  def cheat(t):
    t.gast = t.tt * 0.0
    t.M = t.MT = _identity

  def altitude_at(t):
    cheat(t)
    return altaz_at(sat, topos, t, ts)[0]

  tmax, altitude = find_maxima(t0, t1, jd, altitude_at, half_second, 12)

  print(tmax)
  print(altitude)

  if not tmax:
    return tmax, numpy.ones_like(tmax)

  print('here')
  keepers = altitude >= altitude_degrees
  jdmax = tmax.tt[keepers]
  ones = numpy.ones_like(jdmax, 'uint8')

  def below_horizon_at(t):
    cheat(t)
    return altaz_at(sat, topos, t, ts)[0] < altitude_degrees

  doublets = numpy.repeat(numpy.concatenate(((t0.tt,), jdmax, (t1.tt,))), 2)
  jdo = (doublets[:-1] + doublets[1:]) / 2.0

  trs, rs = _find_discrete(t0.ts, jdo, below_horizon_at, half_second, 8)

  jd = numpy.concatenate((jdmax, trs.tt))
  v = numpy.concatenate((ones, rs * 2))

  i = jd.argsort()
  return ts.tt_jd(jd[i]), v[i]
