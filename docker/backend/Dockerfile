# DSP AI Indicator — Backend API (multi-stage, RC1)
FROM python:3.12-slim AS builder

WORKDIR /build
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY packages ./packages

# P7.3 — install runtime/API deps only (exclude black/mypy/pytest from image)
RUN python -m pip install --upgrade pip && \
    pip install ".[api]"

# Fail the image build if api_platform cannot be imported after install
RUN python -c "import api_platform; from api_platform.api.app import app; print('API IMPORT OK:', api_platform.__file__); print('APP OK:', app.title)"

# --- Runtime ---
FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=1 \
    DSP_ENVIRONMENT=production

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY scripts/start-api.sh /app/scripts/start-api.sh

RUN chmod +x /app/scripts/start-api.sh && \
    useradd --create-home --shell /bin/bash dsp && \
    chown -R dsp:dsp /app

USER dsp
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health/ready || exit 1

CMD ["/app/scripts/start-api.sh"]
