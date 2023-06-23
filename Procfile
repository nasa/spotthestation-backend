web: gunicorn --bind :8000 --workers 1 --threads 2 --timeout 600 application:application
worker: celery -A tasks worker --loglevel INFO
