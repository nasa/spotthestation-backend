FROM python:3.10-slim

# Send Python outputs directly to the terminal
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP application

RUN apt update && apt install -y less nano curl procps

# Set the working directory to /fl-orchestrator
WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
COPY ./requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 80
CMD [ "python", "-m", "flask", "run", "--host=0.0.0.0", "--port=80"]
