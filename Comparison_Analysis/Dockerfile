# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies (cached layer) ──────────────
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# ── Playwright + Chromium (cached separately) ───────
RUN python -m playwright install --with-deps chromium \
    && rm -rf /root/.cache/pip

# ── App source (changes most frequently) ────────────
COPY . .

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
