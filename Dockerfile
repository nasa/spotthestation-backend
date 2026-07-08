FROM python:3.11-slim-bookworm AS base-image

# Upgrading Base Image
RUN apt-get update -y && apt-get upgrade -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y less nano curl procps \
    && rm -rf /var/lib/apt/lists/*

# Send Python outputs directly to the terminal
ENV PYTHONUNBUFFERED=1

WORKDIR /app

FROM base-image AS build-image

RUN apt update && apt install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.10.0 /uv /bin/uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project --extra dev

FROM base-image AS run-image

ENV VIRTUAL_ENV=/app/.venv
COPY --from=build-image /app/.venv ./.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

ENV PYTHONPATH=.

COPY . .

EXPOSE 80

CMD ["gunicorn", \
    "--workers", "2", \
    "--threads", "4", \
    "--bind", "0.0.0.0:80", \
    "--timeout", "300", \
    "rest:app"]
