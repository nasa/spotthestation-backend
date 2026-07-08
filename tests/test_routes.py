"""Tests for the Flask blueprints.

``tokens`` and ``mailer`` import cleanly. ``tracking`` runs cache/Redis side
effects at import time, so it is imported lazily inside its test with those
side effects neutralised.
"""

from datetime import UTC, datetime

import pytest
from flask import Flask

from rest.routes import (
    mailer as mailer_route,
    tokens as tokens_route,
)


def _client(blueprint, **config):
    app = Flask(__name__)
    app.config.update(config)
    app.register_blueprint(blueprint)
    return app.test_client()


class TestTokensRoute:
    def test_returns_configured_tokens(self):
        client = _client(
            tokens_route.bp,
            MAPBOX_API_TOKEN="mapbox-token",
            GOOGLE_API_TOKEN="google-token",
            TIMEZONEDB_API_KEY="tz-key",
        )
        resp = client.get("/tokens")
        assert resp.status_code == 200
        assert resp.get_json() == {
            "MAPBOX_API_TOKEN": "mapbox-token",
            "GOOGLE_API_TOKEN": "google-token",
            "TIMEZONEDB_API_KEY": "tz-key",
        }


class TestMailerRoute:
    def test_sends_mail_to_parsed_recipients(self, mocker):
        mail_instance = mocker.MagicMock()
        mocker.patch.object(mailer_route, "Mail", return_value=mail_instance)

        client = _client(
            mailer_route.bp,
            MAIL_SENDER="from@example.com",
            MAIL_RECIPIENTS="a@example.com, b@example.com",
        )
        resp = client.post(
            "/mailer/send-mail", json={"subject": "Hello", "body": "World"}
        )

        assert resp.status_code == 200
        assert resp.data == b"Mail sent!"
        mail_instance.send.assert_called_once()

        sent_message = mail_instance.send.call_args.args[0]
        assert sent_message.subject == "Hello"
        assert sent_message.body == "World"
        assert sent_message.recipients == ["a@example.com", "b@example.com"]


class TestTrackingRoute:
    @pytest.fixture
    def tracking(self, mocker):
        # Neutralise import-time side effects before importing the module:
        # the top of tracking.py calls sat_data() and installs a disk cache.
        import rest.services.sat_data as sat_service

        mocker.patch.object(sat_service, "redis")
        sat_service.redis.get.return_value = None
        mocker.patch.object(sat_service, "calculate_data_on_boot", return_value=False)
        mocker.patch("requests_cache.install_cache")

        import importlib

        return importlib.import_module("rest.routes.tracking")

    def _points(self):
        return [
            {"date": datetime(2024, 1, 1, tzinfo=UTC), "idx": 0},
            {"date": datetime(2024, 1, 2, tzinfo=UTC), "idx": 1},
            {"date": datetime(2024, 1, 3, tzinfo=UTC), "idx": 2},
        ]

    def test_iss_data_filters_by_date_window(self, mocker, tracking):
        mocker.patch.object(
            tracking,
            "sat_data",
            return_value={
                "points": self._points(),
                "shadow_intervals": [[100.0, 200.0]],
            },
        )
        client = _client(tracking.bp)

        resp = client.post(
            "/tracking/iss-data",
            json={
                "from": "2024-01-01T12:00:00+00:00",
                "to": "2024-01-02T12:00:00+00:00",
            },
        )

        assert resp.status_code == 200
        body = resp.get_json()
        # Only the Jan 2 point falls inside the window.
        assert [p["idx"] for p in body["points"]] == [1]
        assert body["shadowIntervals"] == [[100.0, 200.0]]

    def test_iss_data_raw_without_bounds_returns_all(self, mocker, tracking):
        mocker.patch.object(
            tracking,
            "sat_data",
            return_value={
                "points": self._points(),
                "shadow_intervals": [],
            },
        )
        client = _client(tracking.bp)

        resp = client.post("/tracking/iss-data-raw", json={})

        assert resp.status_code == 200
        assert [p["idx"] for p in resp.get_json()] == [0, 1, 2]
