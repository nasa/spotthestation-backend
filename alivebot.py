import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from redis import Redis

load_dotenv()

redis = Redis.from_url(os.getenv('REDIS_URL'))
slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
server_url = os.getenv("SERVER_URL", "http://localhost:5000")


def send_slack_message(message):
    global slack_webhook_url
    payload = {
        "text": message
    }
    response = requests.post(slack_webhook_url, json=payload)
    return response.status_code == 200


def set_status(value, details=None):
    status = redis.get('server_status')
    status = None if status is None else status.decode('ascii')

    status_updated_at = redis.get('server_status_updated_at')
    noon = datetime.now(tz=timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    is_noon = (
        status_updated_at is not None
        and datetime.fromisoformat(status_updated_at.decode('ascii')) < noon <= datetime.now(tz=timezone.utc)
    )

    if value != status or is_noon:
        message = ""
        if value == "healthy":
            message = "✅ Server is healthy"
        elif value == "no_response":
            message = "❌ Server does not respond"
        elif value == "unexpected_status_code":
            message = f"❌ Server returned an unexpected status code: {details.status_code}"
        elif value == "invalid_response":
            message = f"❌ Server returned an invalid response: {details} is undefined"
        elif value == "stale_data":
            message = f"❌ ISS trajectory data is stale. Last update: {details}"

        redis.set('server_status_updated_at', datetime.now(tz=timezone.utc).isoformat())
        send_slack_message("\nSTS Backend Report:\n" + message)

    redis.set('server_status', value)


def check_health():
    global server_url
    try:
        response = requests.get(f"{server_url}/health")
        if response.status_code == 200:
            data = response.json()
            sat_data_updated_at = data['sat_data_updated_at']

            if data['health'] != 'healthy':
                return set_status("invalid_response", "health")

            if sat_data_updated_at is None:
                return set_status("invalid_response", "sat_data_updated_at")

            if datetime.now(tz=timezone.utc) - timedelta(hours=2) > datetime.fromisoformat(sat_data_updated_at):
                return set_status("stale_data", sat_data_updated_at)

            set_status("healthy")
        else:
            set_status("unexpected_status_code", response)
    except requests.ConnectionError:
        set_status("Unknown error: no_response")


if __name__ == "__main__":
  check_health()
