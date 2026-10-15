# syntax=docker/dockerfile:1
# Build context is the REPO ROOT (see docker-compose.yml), because this file
# needs the root requirements.txt and the frontend/ SPA directory.
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps: build tools for bcrypt/psycopg wheels if needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Backend package, alembic migrations and config land in /app.
COPY backend/ .

# The SPA lives outside /app; app.main resolves it as os.path.join(dirname(__file__), "..", "..", "frontend")
# which from /app/app/main.py resolves to /frontend — mount it there so "/" serves the UI.
COPY frontend/ /frontend/

# Run as a non-root user.
RUN useradd -m appuser && chown -R appuser /app /frontend
USER appuser

EXPOSE 8000

# Default command runs the API. Migrations are applied via docker-compose
# (see the `migrate` one-shot service) or manually before first start.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
