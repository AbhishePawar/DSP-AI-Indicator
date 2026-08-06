/**
 * EPIC-017 — k6 load script (health/readiness surfaces only).
 *
 * Usage:
 *   k6 run -e BASE_URL=http://127.0.0.1:8000 -e VUS=100 -e DURATION=60s scripts/perf/k6_health_load.js
 *
 * Does NOT hit valuation/research engines — ops probes only.
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const failRate = new Rate("dsp_health_fail_rate");
const latency = new Trend("dsp_health_latency_ms");

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8000";
const VUS = Number(__ENV.VUS || 50);
const DURATION = __ENV.DURATION || "30s";

export const options = {
  vus: VUS,
  duration: DURATION,
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<1500", "p(99)<3000"],
    dsp_health_fail_rate: ["rate<0.05"],
  },
};

export default function () {
  const paths = ["/health/live", "/health/ready", "/metrics"];
  const path = paths[Math.floor(Math.random() * paths.length)];
  const res = http.get(`${BASE}${path}`, { tags: { path } });
  const ok = check(res, {
    "status is 200 or 503": (r) => r.status === 200 || r.status === 503,
  });
  failRate.add(!ok);
  latency.add(res.timings.duration);
  sleep(0.1);
}
