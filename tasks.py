from celery import Celery
from dotenv import load_dotenv
import os
from rest.tasks import get_sat_data

load_dotenv()

app = Celery('tasks', broker=os.getenv('REDIS_URL'))
app.set_default()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(3600, get_sat_data, name='get_sat_data')
