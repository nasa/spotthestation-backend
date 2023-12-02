# Welcome to the STSApp Backend

This is a Python web application built using the Flask framework. This README will guide you through the setup, usage, and structure of this project.

## Getting Started

### Prerequisites

Before you begin, ensure you have the following prerequisites installed on your system:

- [Python 3.x](https://www.python.org/downloads/)
- pip (Python Package Manager): You should have pip installed with Python by default.
- [Redis](https://redis.io/)
### Installation

1. Create a virtual environment to isolate project dependencies:
   ```
   python -m venv venv
   ```
2. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```
3. Copy sample env file:
    ```
    cp .env.example .env
    ```
5. Install project dependencies:
    ```
    pip install -r requirements.txt
    ```
### Starting server
Run the following command:
```
python application.py
```
Note that it can take a few minutes to start server for the first time. This is because it needs to download and process ISS trajectory data. 

Optionally, you can start periodic job that will update ISS trajectory data every hour:
```
celery -A tasks worker -B
```

## Project Structure
The project structure is organized as follows:
```   
nasa-iss-backend/
│
├── rest/
│   ├── __init__.py
│   ├── routes
│   ├── services
│   └── tasks.py
│
├── venv/  (Virtual Environment)
│
├── .env
├── README.md
├── requirements.txt
├── alivebot.py
├── application.py
└── tasks.py
```   

**rest/routes**
 This is where Flask route handlers live.

**rest/services**
This is where various helpers live.

**rest/tasks.py**
This is where definitions of periodic tasks live.

**alivebot.py**
This is a script that checks current server status and reports it to Slack channel

**application.py**
This is an entrypoint of the Flask application.

**tasks.py**
This is a script that configures periodic task execution.

## Spinning up Nominatim instance
1. Create RDS user
    ```
    CREATE ROLE nominatim WITH PASSWORD 'qaIACxO6wMR3' CREATEDB CREATEROLE LOGIN;
    GRANT rds_superuser TO nominatim;
    ```
2. Import and start Nominatim server (requires at least 64GB of RAM + 64GB swap, 140GB of free space, 200GB of free space on RDS)
    ```
    sudo docker run -it \
    -d \
    -e PBF_URL=https://ftpmirror.your.org/pub/openstreetmap/pbf/planet-latest.osm.pbf \
    -e NOMINATIM_DATABASE_DSN="pgsql:dbname=nominatim;host=osm-nominatim-db.cidzi6gdqymv.us-east-1.rds.amazonaws.com;user=nominatim;password=qaIACxO6wMR3" \
    -e PGHOST=osm-nominatim-db.cidzi6gdqymv.us-east-1.rds.amazonaws.com \
    -e PGDATABASE=nominatim \
    -e PGUSER=nominatim \
    -e PGPASSWORD=qaIACxO6wMR3 \
    -e FREEZE=true \
    -e IMPORT_STYLE=admin \
    -e NOMINATIM_TOKENIZER=icu \
    -e IMPORT_WIKIPEDIA=true \
    -p 8080:8080 \
    --name nominatim \
    mediagis/nominatim:4.3
    ```
   This step takes about 1.5 days to finish.
3. To start Nominatim server without recreating database:
    ```
   touch import-finished
    sudo docker run -it \
    -d \
    -e PBF_URL=https://ftpmirror.your.org/pub/openstreetmap/pbf/planet-latest.osm.pbf \
    -e NOMINATIM_DATABASE_DSN="pgsql:dbname=nominatim;host=osm-nominatim-db.cidzi6gdqymv.us-east-1.rds.amazonaws.com;user=nominatim;password=qaIACxO6wMR3" \
    -e PGHOST=osm-nominatim-db.cidzi6gdqymv.us-east-1.rds.amazonaws.com \
    -e PGDATABASE=nominatim \
    -e PGUSER=nominatim \
    -e PGPASSWORD=qaIACxO6wMR3 \
    -e FREEZE=true \
    -e IMPORT_STYLE=admin \
    -e NOMINATIM_TOKENIZER=icu \
    -e IMPORT_WIKIPEDIA=true \
    -p 8080:8080 \
    -v ./import-finished:/var/lib/postgresql/14/main/import-finished \
    --name nominatim \
    mediagis/nominatim:4.3
   ```
   Nominatim warms up database caches upon startup, which takes about 3 minutes. The service is not accessible during this process.
