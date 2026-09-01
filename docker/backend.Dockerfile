# Offline-first backend image. Build context is the repo root (pyproject.toml
# lives there, package source is ./backend/prahari). Build with network access to
# install deps and cache/download models ahead of time into ./models; runtime
# must not require network access.
FROM python:3.11-slim

WORKDIR /repo

COPY pyproject.toml /repo/pyproject.toml
COPY backend /repo/backend
RUN pip install --no-cache-dir -e /repo

ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /repo/backend

EXPOSE 8000

CMD ["uvicorn", "prahari.main:app", "--host", "0.0.0.0", "--port", "8000"]
