# DSP private market-data gateway. Build from the repository root:
# docker build -f docker/market-data-gateway.Dockerfile -t dsp-market-data-gateway:dev .
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY packages ./packages
RUN python -m pip install --upgrade pip && pip install ".[api]"

RUN useradd --create-home --shell /bin/bash gateway
USER gateway
EXPOSE 8081
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8081/health/ready || exit 1
CMD ["uvicorn", "data_engine.market_quote.gateway_app:app", "--host", "0.0.0.0", "--port", "8081"]
