import os
from dotenv import load_dotenv
from rest.tasks import get_sat_data

load_dotenv()

if __name__ == "__main__":
    get_sat_data()
