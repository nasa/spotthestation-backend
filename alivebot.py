import os
from datetime import UTC, datetime, timedelta

import requests
from dotenv import load_dotenv
from redis import Redis

from rest.sentry import init_sentry

load_dotenv()
init_sentry()

redis = Redis.from_url(os.getenv("REDIS_URL"))
slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
server_url = os.getenv("SERVER_URL", "http://localhost:5000")


def send_slack_message(message):
    global slack_webhook_url
    payload = {"text": message}
    response = requests.post(slack_webhook_url, json=payload)
    return response.status_code == 200


def set_status(value, details=None):
    status = redis.get("server_status")
    status = None if status is None else status.decode("ascii")

    status_updated_at = redis.get("server_status_updated_at")
    noon = datetime.now(tz=UTC).replace(hour=12, minute=0, second=0, microsecond=0)
    is_noon = status_updated_at is not None and datetime.fromisoformat(
        status_updated_at.decode("ascii")
    ) < noon <= datetime.now(tz=UTC)

    if value != status or is_noon:
        message = ""
        if value == "healthy":
            message = "✅ Server is healthy"
        elif value == "no_response":
            message = "❌ Server does not respond"
        elif value == "unexpected_status_code":
            message = (
                f"❌ Server returned an unexpected status code: {details.status_code}"
            )
        elif value == "invalid_response":
            message = f"❌ Server returned an invalid response: {details} is undefined"
        elif value == "stale_data_iss":
            message = f"❌ ISS trajectory data is stale. Last update: {details}"
        elif value == "stale_data_astronauts":
            message = f"❌ Astronauts data is stale. Last update: {details}"
        elif value == "stale_data_youtube_livestream_id":
            message = f"❌ Youtube livestream id is stale. Last update: {details}"

        redis.set("server_status_updated_at", datetime.now(tz=UTC).isoformat())
        send_slack_message("\nSTS Backend Report:\n" + message)

    redis.set("server_status", value)


def check_health():
    global server_url
    try:
        response = requests.get(f"{server_url}/health")
        if response.status_code == 200:
            data = response.json()
            sat_data_updated_at = data["sat_data_updated_at"]
            astronauts_updated_at = data["astronauts_updated_at"]
            youtube_livestream_id_updated_at = data["youtube_livestream_id_updated_at"]

            if data["health"] != "healthy":
                return set_status("invalid_response", "health")

            if sat_data_updated_at is None:
                return set_status("invalid_response", "sat_data_updated_at")

            if astronauts_updated_at is None:
                return set_status("invalid_response", "astronauts_updated_at")

            if youtube_livestream_id_updated_at is None:
                return set_status(
                    "invalid_response", "youtube_livestream_id_updated_at"
                )

            if datetime.now(tz=UTC) - timedelta(hours=3) > datetime.fromisoformat(
                sat_data_updated_at
            ):
                return set_status("stale_data_iss", sat_data_updated_at)

            if datetime.now(tz=UTC) - timedelta(hours=3) > datetime.fromisoformat(
                astronauts_updated_at
            ):
                return set_status("stale_data_astronauts", astronauts_updated_at)

            if datetime.now(tz=UTC) - timedelta(hours=3) > datetime.fromisoformat(
                youtube_livestream_id_updated_at
            ):
                return set_status(
                    "stale_data_youtube_livestream_id", youtube_livestream_id_updated_at
                )

            set_status("healthy")
        else:
            set_status("unexpected_status_code", response)
    except requests.ConnectionError:
        set_status("Unknown error: no_response")


if __name__ == "__main__":
    check_health()
