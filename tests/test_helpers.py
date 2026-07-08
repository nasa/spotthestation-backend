"""Unit tests for the pure helper functions in ``rest.services.helpers``.

These cover the small, deterministic building blocks (chunking, formatting,
astrodynamics math) without touching the network, filesystem, or Flask app.
"""

import contextlib
import datetime as dt
import xml.etree.ElementTree as ET
from math import pi, radians
from typing import ClassVar

import numpy
import pytest

from rest.services import helpers
from rest.services.helpers import (
    IERS,
    ECEF_to_look_angles,
    altaz,
    altaz_to_latlon,
    calculate_day_stage,
    chunks,
    datetime_range,
    deg_to_compass,
    diag3,
    download,
    find_events,
    format_epoch,
    geodetic_to_ECEF,
    get_comment_value,
    get_earth_positions,
    iauCal2jd,
    iauEra00,
    iauObl06,
    iauPnm06a,
    iauRz,
    invjday,
    is_in_shadow,
    linear_interpolation,
    rem,
    time_diffs,
    topocentric,
    topocentric_to_look_angles,
    topos_xyz,
)


class TestChunks:
    def test_splits_into_even_chunks(self):
        assert list(chunks([1, 2, 3, 4], 2)) == [[1, 2], [3, 4]]

    def test_last_chunk_may_be_shorter(self):
        assert list(chunks([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]

    def test_empty_input(self):
        assert list(chunks([], 3)) == []


class TestDegToCompass:
    @pytest.mark.parametrize(
        "degrees,expected",
        [
            (0, "N"),
            (45, "NE"),
            (90, "E"),
            (180, "S"),
            (270, "W"),
            (360, "N"),  # wraps back to North
        ],
    )
    def test_cardinal_and_intercardinal(self, degrees, expected):
        assert deg_to_compass(degrees) == expected


class TestDatetimeRange:
    def test_yields_expected_steps(self):
        start = dt.datetime(2024, 1, 1, 0, 0, 0)
        end = dt.datetime(2024, 1, 1, 0, 3, 0)
        delta = dt.timedelta(minutes=1)
        assert list(datetime_range(start, end, delta)) == [
            dt.datetime(2024, 1, 1, 0, 0, 0),
            dt.datetime(2024, 1, 1, 0, 1, 0),
            dt.datetime(2024, 1, 1, 0, 2, 0),
        ]

    def test_end_is_exclusive(self):
        start = dt.datetime(2024, 1, 1)
        end = dt.datetime(2024, 1, 1)
        assert list(datetime_range(start, end, dt.timedelta(hours=1))) == []


class TestGetCommentValue:
    def test_parses_trailing_float(self):
        assert get_comment_value("MASS = 123.45") == pytest.approx(123.45)

    def test_negative_value(self):
        assert get_comment_value("DRAG_AREA=-0.5") == pytest.approx(-0.5)


class TestCalculateDayStage:
    # A twilight list has (at least) indices 0, 2, 5 and -1 that bracket
    # the various day stages; plain numbers stand in for the datetimes.
    twilight: ClassVar[list[int]] = [0, 1, 2, 3, 4, 5, 6]

    def test_before_first_event_is_night(self):
        assert calculate_day_stage(self.twilight, -1) == 0

    def test_after_last_event_is_night(self):
        assert calculate_day_stage(self.twilight, 7) == 0

    def test_early_twilight_is_stage_one(self):
        assert calculate_day_stage(self.twilight, 1) == 1

    def test_late_twilight_is_stage_one(self):
        assert calculate_day_stage(self.twilight, 5.5) == 1

    def test_daytime_is_stage_two(self):
        assert calculate_day_stage(self.twilight, 3) == 2


class TestRem:
    @pytest.mark.parametrize(
        "x,y,expected",
        [
            (7, 3, 1),
            (-7, 3, -1),  # truncated (not floored) toward zero
            (5.5, 2, 1.5),
        ],
    )
    def test_truncated_remainder(self, x, y, expected):
        assert rem(x, y) == pytest.approx(expected)


class TestTimeDiffs:
    def test_known_offsets(self):
        result = time_diffs(UT1_UTC=0.1, TAI_UTC=37.0)
        (
            TT_TAI,
            GPS_TAI,
            TT_GPS,
            TAI_GPS,
            UT1_TAI,
            UTC_TAI,
            UTC_GPS,
            UT1_GPS,
            TT_UTC,
            GPS_UTC,
        ) = result

        assert pytest.approx(32.184) == TT_TAI
        assert pytest.approx(-19.0) == GPS_TAI
        assert pytest.approx(51.184) == TT_GPS
        assert pytest.approx(19.0) == TAI_GPS
        assert pytest.approx(-36.9) == UT1_TAI
        assert pytest.approx(-37.0) == UTC_TAI
        assert pytest.approx(69.184) == TT_UTC
        assert pytest.approx(18.0) == GPS_UTC
        assert pytest.approx(-18.0) == UTC_GPS
        assert pytest.approx(-17.9) == UT1_GPS


class TestDiag3:
    def test_is_identity_matrix(self):
        assert diag3() == [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]


class TestIauCal2jd:
    def test_j2000_epoch_midnight(self):
        # 2000-01-01 00:00 UTC -> JD 2451544.5, MJD 51544.0
        djm0, djm = iauCal2jd(2000, 1, 1)
        assert djm0 == pytest.approx(2400000.5)
        assert djm == pytest.approx(51544.0)

    def test_noon_adds_half_day(self):
        _, djm = iauCal2jd(2000, 1, 1, 12, 0, 0)
        assert djm == pytest.approx(51544.5)


class TestInvjday:
    def test_round_trips_with_cal2jd(self):
        djm0, djm = iauCal2jd(2024, 3, 25, 6, 30, 0)
        jd = djm0 + djm
        year, month, day, hour, minute, sec = invjday(jd)
        assert (year, month, day, hour, minute) == (2024, 3, 25, 6, 30)
        assert sec == pytest.approx(0.0, abs=1e-3)


class TestIauRz:
    def test_quarter_turn_of_identity(self):
        r = iauRz(pi / 2, diag3())
        expected = [
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
        for row, exp_row in zip(r, expected, strict=True):
            for value, exp in zip(row, exp_row, strict=True):
                assert value == pytest.approx(exp, abs=1e-12)


class TestGeodeticToECEF:
    def test_equator_prime_meridian(self):
        # At lat=0, lon=0, altitude=0 the point lies on the +X axis at the
        # equatorial radius (km).
        x, y, z = geodetic_to_ECEF(0.0, 0.0, 0.0)
        assert x == pytest.approx(6378.137)
        assert y == pytest.approx(0.0, abs=1e-9)
        assert z == pytest.approx(0.0, abs=1e-9)

    def test_north_pole(self):
        # At the north pole X and Y vanish and Z is the polar radius (km).
        x, y, z = geodetic_to_ECEF(radians(90.0), 0.0, 0.0)
        assert x == pytest.approx(0.0, abs=1e-6)
        assert y == pytest.approx(0.0, abs=1e-9)
        assert z == pytest.approx(6356.7523142, rel=1e-6)


class TestTopocentricToLookAngles:
    def test_straight_overhead(self):
        # A target directly overhead: only the Z (up) component is non-zero.
        az, el, rng = topocentric_to_look_angles(0.0, 0.0, 100.0)
        assert rng == pytest.approx(100.0)
        assert el == pytest.approx(pi / 2)
        assert az == pytest.approx(pi)


class TestLinearInterpolation:
    def test_inserts_midpoint(self):
        data = [
            {
                "date": dt.datetime(2024, 1, 1, 0, 0, 0),
                "location": [0.0, 0.0, 0.0],
                "velocity": [10.0, 0.0, 0.0],
                "altitude": 400.0,
            },
            {
                "date": dt.datetime(2024, 1, 1, 0, 2, 0),
                "location": [2.0, 4.0, 6.0],
                "velocity": [12.0, 0.0, 0.0],
                "altitude": 420.0,
            },
        ]

        result = linear_interpolation(data, parts=2)

        # Original endpoints plus one interpolated midpoint.
        assert len(result) == 3
        assert result[0] is data[0]
        assert result[-1] is data[-1]

        midpoint = result[1]
        assert midpoint["date"] == dt.datetime(2024, 1, 1, 0, 1, 0)
        assert midpoint["location"] == pytest.approx([1.0, 2.0, 3.0])
        assert midpoint["velocity"] == pytest.approx([11.0, 0.0, 0.0])
        assert midpoint["altitude"] == pytest.approx(410.0)


class TestIsInShadow:
    def test_sunlit_when_sun_on_same_side(self):
        r_iss = numpy.array([6771000.0, 0.0, 0.0])  # ~400 km altitude on +X
        r_sun = numpy.array([1.5e11, 0.0, 0.0])  # Sun far along +X
        assert bool(is_in_shadow(r_sun, r_iss)) is False

    def test_in_shadow_when_behind_earth(self):
        # ISS just off the anti-Sun axis, close enough to the Earth-Sun line
        # that Earth's disk (radius ~6378 km) eclipses it.
        r_iss = numpy.array([6771000.0, 1_000_000.0, 0.0])
        r_sun = numpy.array([-1.5e11, 0.0, 0.0])  # Sun on the opposite (-X) side
        assert bool(is_in_shadow(r_sun, r_iss)) is True


class TestFormatEpoch:
    def test_parses_state_vector_element(self):
        xml = """<stateVector>
          <EPOCH>2024-001T12:30:45.500000Z</EPOCH>
          <X>1.0</X><Y>2.0</Y><Z>3.0</Z>
          <X_DOT>-4.0</X_DOT><Y_DOT>5.0</Y_DOT><Z_DOT>-6.0</Z_DOT>
        </stateVector>"""
        result = format_epoch(ET.fromstring(xml))
        assert result == {
            # day-of-year 001 -> January 1st, and the trailing Z is dropped
            "date": "2024-01-01T12:30:45.500000",
            "location": [1.0, 2.0, 3.0],
            "velocity": [-4.0, 5.0, -6.0],
        }


class TestGetEarthPositions:
    def test_parses_observed_and_predicted_blocks(self, mocker):
        # NOTE: characterization test. The slice bounds in get_earth_positions
        # are ``[begin + 1 : end - 1]``, so the final row of each block is
        # intentionally (if surprisingly) dropped.
        fake_file = "\n".join(
            [
                "header junk",
                "BEGIN OBSERVED",
                " 1.0  2.0  3.0 ",
                "4.0 5.0 6.0",  # dropped by the ``end - 1`` bound
                "END OBSERVED",
                "separator",
                "BEGIN PREDICTED",
                "7.0 8.0",
                "9.0 10.0",  # dropped by the ``end - 1`` bound
                "END PREDICTED",
            ]
        )
        mocker.patch("builtins.open", mocker.mock_open(read_data=fake_file))

        assert get_earth_positions() == [[1.0, 2.0, 3.0], [7.0, 8.0]]


class TestDownload:
    def test_streams_chunks_to_file(self, mocker, tmp_path):
        response = mocker.MagicMock()
        response.iter_content.return_value = [
            b"abc",
            b"",
            b"def",
        ]  # empty chunk skipped
        get_cm = mocker.MagicMock()
        get_cm.__enter__.return_value = response
        mocker.patch("rest.services.helpers.requests.get", return_value=get_cm)
        mocker.patch(
            "rest.services.helpers.requests_cache.disabled",
            return_value=contextlib.nullcontext(),
        )

        target = tmp_path / "nested" / "payload.bin"
        result = download("http://example.com/payload.bin", str(target))

        assert result == str(target)
        assert target.read_bytes() == b"abcdef"
        response.raise_for_status.assert_called_once()

    def test_derives_name_from_url(self, mocker, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        response = mocker.MagicMock()
        response.iter_content.return_value = [b"data"]
        get_cm = mocker.MagicMock()
        get_cm.__enter__.return_value = response
        mocker.patch("rest.services.helpers.requests.get", return_value=get_cm)
        mocker.patch(
            "rest.services.helpers.requests_cache.disabled",
            return_value=contextlib.nullcontext(),
        )

        result = download("http://example.com/dir/file.txt")

        assert result == "file.txt"
        assert (tmp_path / "file.txt").read_bytes() == b"data"


class TestIauObl06:
    def test_mean_obliquity_at_j2000(self):
        # Mean obliquity of the ecliptic at J2000.0 ~= 84381.406 arcsec.
        assert iauObl06(2451545.0, 0.0) == pytest.approx(0.4090926006, abs=1e-10)


class TestIauEra00:
    def test_earth_rotation_angle_at_j2000(self):
        # ERA at J2000.0 = 0.7790572732640 turns.
        assert iauEra00(2451545.0, 0.0) == pytest.approx(4.894961212823, abs=1e-9)

    def test_result_within_zero_to_two_pi(self):
        theta = iauEra00(2451545.0, 0.25)
        assert 0.0 <= theta < 2 * pi


class TestIauPnm06a:
    def test_matrix_is_orthonormal_rotation(self):
        m = numpy.array(iauPnm06a(2451545.0, 0.0))
        # A proper rotation: R @ R.T == I and det(R) == +1.
        assert numpy.allclose(m @ m.T, numpy.eye(3), atol=1e-12)
        assert numpy.linalg.det(m) == pytest.approx(1.0, abs=1e-12)


class TestIERS:
    # Two-row synthetic Earth-orientation table. Columns used by IERS():
    # [3]=MJD [4]=x_pole [5]=y_pole [6]=UT1_UTC [7]=LOD [8]=dpsi [9]=deps
    # [10]=dx_pole [11]=dy_pole [12]=TAI_UTC
    eop: ClassVar[list[list[float]]] = [
        [0, 0, 0, 59000.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 37.0],
        [0, 0, 0, 59001.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 37.0],
    ]

    def test_exact_mjd_returns_first_row(self):
        from rest.services.constants import const_arcs

        x_pole, y_pole, ut1_utc, lod, dpsi, deps, tai_utc = IERS(self.eop, 59000.0)
        assert x_pole == pytest.approx(0.1 / const_arcs)
        assert y_pole == pytest.approx(0.2 / const_arcs)
        assert ut1_utc == pytest.approx(0.3)  # not scaled
        assert lod == pytest.approx(0.4)  # not scaled
        assert dpsi == pytest.approx(0.5 / const_arcs)
        assert deps == pytest.approx(0.6 / const_arcs)
        assert tai_utc == pytest.approx(37.0)

    def test_midpoint_interpolates_linearly(self):
        from rest.services.constants import const_arcs

        x_pole, y_pole, ut1_utc, lod, *_ = IERS(self.eop, 59000.5)
        assert x_pole == pytest.approx(0.15 / const_arcs)
        assert y_pole == pytest.approx(0.30 / const_arcs)
        assert ut1_utc == pytest.approx(0.4)
        assert lod == pytest.approx(0.5)


class TestTopocentric:
    def test_target_directly_overhead(self):
        # Observer at (lat=0, lon=0); target straight up along +X (ECEF, km).
        top_s, top_e, top_z = topocentric(0.0, 0.0, 0.0, 7000.0, 0.0, 0.0)
        assert top_s == pytest.approx(0.0, abs=1e-9)
        assert top_e == pytest.approx(0.0, abs=1e-9)
        assert top_z == pytest.approx(7000.0 - 6378.137)


class TestECEFToLookAngles:
    def test_overhead_is_ninety_degrees_elevation(self):
        az, el, rng = ECEF_to_look_angles(0.0, 0.0, 0.0, 7000.0, 0.0, 0.0)
        assert el == pytest.approx(pi / 2)
        assert az == pytest.approx(pi)
        assert rng == pytest.approx(7000.0 - 6378.137)


class TestAltaz:
    def test_maps_positions_to_look_angles(self):
        sat = [{"location": [7000.0, 0.0, 0.0], "date": "2024-01-01T00:00:00"}]
        result = altaz(sat, (0.0, 0.0, 0.0))
        assert len(result) == 1
        assert result[0]["time"] == "2024-01-01T00:00:00"
        assert result[0]["elevation"] == pytest.approx(90.0)
        assert result[0]["azimut"] == pytest.approx(180.0)


class TestFindEvents:
    def _samples(self, elevations):
        # find_events only reads elevation/azimut/time from altaz()'s output.
        return [
            {"time": i, "elevation": el, "azimut": 10.0 * i}
            for i, el in enumerate(elevations)
        ]

    def test_detects_a_single_pass(self, mocker):
        mocker.patch.object(
            helpers, "altaz", return_value=self._samples([-5.0, 10.0, 30.0, -2.0])
        )
        periods = find_events(sat=None, topos=None, threshold=0.0)

        assert len(periods) == 1
        period = periods[0]
        assert period["start_time"] == 1
        assert period["end_time"] == 3
        assert period["max_elevation"] == pytest.approx(30.0)
        assert period["max_elevation_time"] == 2

    def test_no_pass_when_always_below_threshold(self, mocker):
        mocker.patch.object(
            helpers, "altaz", return_value=self._samples([-5.0, -1.0, -3.0])
        )
        assert find_events(sat=None, topos=None, threshold=0.0) == []

    def test_pass_still_open_at_end_is_not_emitted(self, mocker):
        # A rise with no subsequent fall never closes the period.
        mocker.patch.object(
            helpers, "altaz", return_value=self._samples([-5.0, 10.0, 20.0])
        )
        assert find_events(sat=None, topos=None, threshold=0.0) == []


class TestAltazToLatlon:
    def test_returns_finite_lat_lon(self):
        # Characterization test locking current output for a fixed input.
        lat, lon = altaz_to_latlon(0.5, 0.3, 1.0, 0.8, 2.0)
        assert lat == pytest.approx(64.29600111, abs=1e-6)
        assert lon == pytest.approx(65.62346448, abs=1e-6)


class TestToposXyz:
    def test_builds_topos_from_ecef(self):
        # Point on the equator at the prime meridian, ~400 km up (km units).
        topos = topos_xyz(6778.137, 0.0, 0.0)
        assert topos.latitude.degrees == pytest.approx(0.0, abs=1e-6)
        assert topos.longitude.degrees == pytest.approx(0.0, abs=1e-6)
