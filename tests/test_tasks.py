"""Tests for the data-fetching tasks in ``rest.tasks``.

Only the parsing/selection logic is exercised; the network (``requests``)
and Redis are mocked so no external calls are made.
"""

import pickle

import pytest

from rest import tasks


def _stored(redis_mock):
    """Collapse ``redis.set(key, value)`` calls into a ``{key: value}`` dict."""
    return {call.args[0]: call.args[1] for call in redis_mock.set.call_args_list}


class TestGetYoutubeLivestreamId:
    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("YT_API_TOKEN", "key")
        monkeypatch.setenv("YT_CHANNEL_ID", "channel")

    def _response(self, mocker, status, json_data=None):
        resp = mocker.MagicMock()
        resp.status_code = status
        resp.json.return_value = json_data
        return resp

    def test_prefers_iss_titled_stream(self, mocker):
        redis_mock = mocker.patch.object(tasks, "redis")
        items = [
            {
                "id": {"videoId": "iss-vid"},
                "snippet": {"title": "Live from the International Space Station"},
            },
            {"id": {"videoId": "other-vid"}, "snippet": {"title": "Some clip"}},
        ]
        mocker.patch.object(
            tasks.requests,
            "get",
            return_value=self._response(mocker, 200, {"items": items}),
        )

        assert tasks.get_youtube_livestream_id() is True
        assert pickle.loads(_stored(redis_mock)["youtube_livestream_id"]) == "iss-vid"

    def test_falls_back_to_first_when_no_iss_match(self, mocker):
        redis_mock = mocker.patch.object(tasks, "redis")
        # reversed() makes the last item the default pick.
        items = [
            {"id": {"videoId": "first"}, "snippet": {"title": "Clip A"}},
            {"id": {"videoId": "last"}, "snippet": {"title": "Clip B"}},
        ]
        mocker.patch.object(
            tasks.requests,
            "get",
            return_value=self._response(mocker, 200, {"items": items}),
        )

        assert tasks.get_youtube_livestream_id() is True
        assert pickle.loads(_stored(redis_mock)["youtube_livestream_id"]) == "last"

    def test_empty_items_stores_empty_id(self, mocker):
        redis_mock = mocker.patch.object(tasks, "redis")
        mocker.patch.object(
            tasks.requests,
            "get",
            return_value=self._response(mocker, 200, {"items": []}),
        )

        assert tasks.get_youtube_livestream_id() is True
        assert pickle.loads(_stored(redis_mock)["youtube_livestream_id"]) == ""

    def test_non_200_returns_false_and_stores_nothing(self, mocker):
        redis_mock = mocker.patch.object(tasks, "redis")
        mocker.patch.object(
            tasks.requests, "get", return_value=self._response(mocker, 503)
        )

        assert tasks.get_youtube_livestream_id() is False
        redis_mock.set.assert_not_called()

    def test_request_exception_returns_false(self, mocker):
        redis_mock = mocker.patch.object(tasks, "redis")
        mocker.patch.object(tasks.requests, "get", side_effect=RuntimeError("boom"))

        assert tasks.get_youtube_livestream_id() is False
        redis_mock.set.assert_not_called()


class TestGetAstronauts:
    HTML = """
    <html><body>
      <div class="hds-meet-the">
        <div class="hds-meet-the-card">
          <img src="https://images.example.com/jane.jpg?fm=jpg" />
          <h3>Jane Doe</h3>
          <p>Flight Engineer</p>
          <a href="https://nasa.gov/people/jane"></a>
        </div>
      </div>
    </body></html>
    """

    def test_parses_cards_and_resizes_image(self, mocker):
        redis_mock = mocker.patch.object(tasks, "redis")
        resp = mocker.MagicMock(status_code=200, content=self.HTML.encode())
        mocker.patch.object(tasks.requests, "get", return_value=resp)

        tasks.get_astronauts()

        stored = pickle.loads(_stored(redis_mock)["astronauts"])
        assert len(stored) == 1
        card = stored[0]
        assert card["name"] == "Jane Doe"
        assert card["title"] == "Flight Engineer"
        assert card["link"] == "https://nasa.gov/people/jane"
        # Original query kept, resize params appended.
        assert "fm=jpg" in card["image"]
        assert "w=700" in card["image"]
        assert "h=700" in card["image"]

    def test_non_200_stores_nothing(self, mocker):
        redis_mock = mocker.patch.object(tasks, "redis")
        resp = mocker.MagicMock(status_code=404, content=b"")
        mocker.patch.object(tasks.requests, "get", return_value=resp)

        tasks.get_astronauts()

        redis_mock.set.assert_not_called()
