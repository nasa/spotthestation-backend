"""Tests for the Redis-backed cache accessors in ``rest.services``.

The service modules build a Redis client at import time but never connect
until a method is called, so each test patches the module-level ``redis``
object and resets the module-level cache globals.
"""

import pickle

import pytest

from rest.services import (
    astronauts as astro_mod,
    sat_data as sat_mod,
    youtube as yt_mod,
)

ALL_MODULES = [astro_mod, sat_mod, yt_mod]


def _redis_returning(mocker, module, mapping):
    """Patch ``module.redis`` so ``.get(key)`` reads from ``mapping``."""
    mocker.patch.object(module, "redis")
    module.redis.get.side_effect = lambda key: mapping.get(key)
    return module.redis


class TestLastUpdated:
    @pytest.mark.parametrize("module", ALL_MODULES)
    def test_returns_none_when_absent(self, mocker, module):
        _redis_returning(mocker, module, {})
        assert module.last_updated() is None

    @pytest.mark.parametrize("module", ALL_MODULES)
    def test_decodes_stored_timestamp(self, mocker, module):
        key = {
            astro_mod: "astronauts_updated_at",
            sat_mod: "sat_data_updated_at",
            yt_mod: "youtube_livestream_id_updated_at",
        }[module]
        _redis_returning(mocker, module, {key: b"2024-05-01T10:00:00+00:00"})
        assert module.last_updated() == "2024-05-01T10:00:00+00:00"


class TestAstronauts:
    def test_returns_none_without_data_and_boot_disabled(self, mocker, monkeypatch):
        _redis_returning(mocker, astro_mod, {})
        monkeypatch.setattr(astro_mod, "astronauts_cache", None)
        monkeypatch.setattr(astro_mod, "astronauts_cache_updated_at", None)
        mocker.patch.object(astro_mod, "calculate_data_on_boot", return_value=False)
        assert astro_mod.astronauts() is None

    def test_loads_payload_from_redis(self, mocker, monkeypatch):
        payload = [{"name": "Jane Doe", "title": "Astronaut"}]
        _redis_returning(
            mocker,
            astro_mod,
            {
                "astronauts_updated_at": b"2030-01-01T00:00:00+00:00",
                "astronauts": pickle.dumps(payload),
            },
        )
        monkeypatch.setattr(astro_mod, "astronauts_cache", None)
        monkeypatch.setattr(astro_mod, "astronauts_cache_updated_at", None)
        assert astro_mod.astronauts() == payload


class TestSatData:
    def test_empty_result_without_data_and_boot_disabled(self, mocker, monkeypatch):
        _redis_returning(mocker, sat_mod, {})
        monkeypatch.setattr(sat_mod, "sat_data_not_interpolated_cache", None)
        monkeypatch.setattr(sat_mod, "shadow_intervals_cache", None)
        monkeypatch.setattr(sat_mod, "sat_data_cache_updated_at", None)
        mocker.patch.object(sat_mod, "calculate_data_on_boot", return_value=False)
        assert sat_mod.sat_data() == {"points": [], "shadow_intervals": []}

    def test_loads_points_and_shadow_intervals(self, mocker, monkeypatch):
        points = [{"date": "2024-01-01", "location": [1, 2, 3]}]
        intervals = [[100.0, 200.0]]
        _redis_returning(
            mocker,
            sat_mod,
            {
                "sat_data_updated_at": b"2030-01-01T00:00:00+00:00",
                "sat_data_not_interpolated": pickle.dumps(points),
                "shadow_intervals": pickle.dumps(intervals),
            },
        )
        monkeypatch.setattr(sat_mod, "sat_data_not_interpolated_cache", None)
        monkeypatch.setattr(sat_mod, "shadow_intervals_cache", None)
        monkeypatch.setattr(sat_mod, "sat_data_cache_updated_at", None)

        assert sat_mod.sat_data() == {
            "points": points,
            "shadow_intervals": intervals,
        }


class TestYoutube:
    def test_returns_none_without_data_and_boot_disabled(self, mocker, monkeypatch):
        _redis_returning(mocker, yt_mod, {})
        monkeypatch.setattr(yt_mod, "youtube_livestream_id_cache", None)
        monkeypatch.setattr(yt_mod, "youtube_livestream_id_cache_updated_at", None)
        mocker.patch.object(yt_mod, "calculate_data_on_boot", return_value=False)
        assert yt_mod.youtube_livestream_id() is None

    def test_loads_video_id_from_redis(self, mocker, monkeypatch):
        _redis_returning(
            mocker,
            yt_mod,
            {
                "youtube_livestream_id_updated_at": b"2030-01-01T00:00:00+00:00",
                "youtube_livestream_id": pickle.dumps("abc123"),
            },
        )
        monkeypatch.setattr(yt_mod, "youtube_livestream_id_cache", None)
        monkeypatch.setattr(yt_mod, "youtube_livestream_id_cache_updated_at", None)
        assert yt_mod.youtube_livestream_id() == "abc123"
