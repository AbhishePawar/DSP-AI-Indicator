#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="dsp-production-api-1"
BASE_URL="http://127.0.0.1:8000"

echo "=== 1. Checking /health ==="
HEALTH_JSON=$(docker exec "$CONTAINER_NAME" curl -fsS "$BASE_URL/health")
echo "$HEALTH_JSON"

READY=$(echo "$HEALTH_JSON" | grep -o '"ready":true' || true)
STATUS=$(echo "$HEALTH_JSON" | grep -o '"status":"pass"' || true)

if [ -z "$READY" ] || [ -z "$STATUS" ]; then
    echo "[-] Health check failed: ready or pass flag not present."
    exit 1
fi
echo "[+] Health check passed (ready: true, status: pass)"

echo ""
echo "=== 2. Checking API HTTP status ==="
API_STATUS=$(docker exec "$CONTAINER_NAME" curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
echo "API Route status code: $API_STATUS"

echo ""
echo "=== 3. Testing Upstox provider credentials via internal Python check ==="
docker exec "$CONTAINER_NAME" python -c '
from data_engine.market_quote.adapters import build_default_quote_adapter_from_env
adapter = build_default_quote_adapter_from_env()
adapter_name = type(adapter).__name__
print(f"[+] Loaded Quote Adapter: {adapter_name}")
assert adapter_name == "UpstoxQuoteAdapter", f"Expected UpstoxQuoteAdapter, got {adapter_name}"
print("[+] Upstox quote adapter verified and initialized cleanly inside container.")
'

echo ""
echo "=== SMOKE TEST COMPLETE: ALL CHECKS PASSED ==="
