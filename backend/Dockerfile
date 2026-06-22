FROM python:3.11-slim

WORKDIR /app

# System deps for pdf/cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV PYTHONUNBUFFERED=1

# Render injects PORT at runtime — shell form required so $PORT expands
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
