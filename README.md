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