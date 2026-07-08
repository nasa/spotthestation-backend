from dotenv import load_dotenv

from rest.sentry import init_sentry
from rest.tasks import get_astronauts, get_sat_data, get_youtube_livestream_id

load_dotenv()
init_sentry()

if __name__ == "__main__":
    get_sat_data()
    get_astronauts()
    get_youtube_livestream_id()
