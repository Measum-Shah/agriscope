# Multi-stage Dockerfile for AgriScope ML Service
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY agriscope_ml ./agriscope_ml
RUN pip install --no-cache-dir --user .

# Final runner stage
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/mluser/.local/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --home-dir /home/mluser --shell /bin/bash mluser

COPY --from=builder /root/.local /home/mluser/.local
COPY . /app

RUN chown -R mluser:mluser /app /home/mluser

USER mluser

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8001"]
