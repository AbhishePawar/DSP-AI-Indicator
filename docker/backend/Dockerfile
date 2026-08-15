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
# Root [api] is the authoritative production dependency set and must include
# psycopg[binary]. Nested package optional-extras are not used by this image.
RUN python -m pip install --upgrade pip && \
    pip install ".[api]"

# Prove the PostgreSQL driver is installed AND importable (distribution + pq impl).
# api_platform import alone is insufficient: create_app() only loads psycopg under
# DSP_ENVIRONMENT=production, which cannot run at image-build time without secrets.
RUN python -m pip show psycopg psycopg-binary && \
    python -c "import psycopg, psycopg.pq; print('BUILDER PSYCOPG OK:', psycopg.__version__, psycopg.__file__); print('BUILDER PQ IMPL:', psycopg.pq.__impl__); print('BUILDER PQ VERSION:', psycopg.pq.version())"

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

# Prove driver + API survive builder→runtime /usr/local copy (before USER dsp).
RUN python -m pip show psycopg psycopg-binary && \
    python -c "import sys, psycopg, psycopg.pq; print('RUNTIME PSYCOPG OK:', psycopg.__version__, psycopg.__file__); print('RUNTIME PQ IMPL:', psycopg.pq.__impl__); print('RUNTIME PQ VERSION:', psycopg.pq.version()); print('RUNTIME PYTHON:', sys.executable)"
# Development override: create_app() must not require Cloud SQL/secrets at build time.
RUN DSP_ENVIRONMENT=development python -c "import sys, api_platform; from api_platform.api.app import app; print('RUNTIME API IMPORT OK:', api_platform.__file__); print('RUNTIME APP OK:', app.title); print('RUNTIME PYTHON:', sys.executable)"
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
