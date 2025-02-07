import os
from dotenv import load_dotenv
from rest.tasks import get_sat_data, get_astronauts, get_youtube_livestream_id

load_dotenv()

if __name__ == "__main__":
    get_sat_data()
    get_astronauts()
    get_youtube_livestream_id()
