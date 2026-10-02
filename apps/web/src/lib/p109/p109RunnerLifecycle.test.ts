import { EventEmitter } from "node:events";
import { describe, expect, it, vi } from "vitest";

import {
  ManagedProcessTracker,
  ensureBackendService,
  ensureFrontendService,
  getHealthConfig,
  pollServiceHealth,
} from "../../../e2e/browser/p109/runnerCore";

function createMockProcess(exitCode: number | null = null) {
  const proc = new EventEmitter() as any;
  proc.exitCode = exitCode;
  proc.killed = false;
  proc.stdout = new EventEmitter();
  proc.stderr = new EventEmitter();
  proc.kill = vi.fn((sig?: string) => {
    proc.killed = true;
    proc.emit("close", 0);
  });
  return proc;
}

describe("P1-09 runner lifecycle & health configuration", () => {
  it("validates configurable health timeout and interval with bounds", () => {
    // Defaults
    expect(getHealthConfig({})).toEqual({ timeoutMs: 25_000, intervalMs: 1_000 });

    // Custom valid values
    expect(
      getHealthConfig({
        DSP_P109_HEALTH_TIMEOUT_MS: "45000",
        DSP_P109_HEALTH_INTERVAL_MS: "2500",
      })
    ).toEqual({ timeoutMs: 45_000, intervalMs: 2_500 });

    // Out of bounds / invalid fallback to defaults
    expect(
      getHealthConfig({
        DSP_P109_HEALTH_TIMEOUT_MS: "9999999",
        DSP_P109_HEALTH_INTERVAL_MS: "5",
      })
    ).toEqual({ timeoutMs: 25_000, intervalMs: 1_000 });
  });

  it("reuses already-running backend service without spawning child processes", async () => {
    const tracker = new ManagedProcessTracker();
    const spawnFn = vi.fn();
    const checkUrlFn = vi.fn(async () => true);

    const result = await ensureBackendService(
      { apiBaseUrl: "http://127.0.0.1:8000/api/v1" },
      tracker,
      { timeoutMs: 2000, intervalMs: 500 },
      { spawnFn: spawnFn as any, checkUrlFn }
    );

    expect(result.ok).toBe(true);
    expect(result.alreadyRunning).toBe(true);
    expect(spawnFn).not.toHaveBeenCalled();
    expect(tracker.getManagedCount()).toBe(0);
  });

  it("reuses already-running frontend service without spawning child processes", async () => {
    const tracker = new ManagedProcessTracker();
    const spawnFn = vi.fn();
    const checkUrlFn = vi.fn(async () => true);

    const result = await ensureFrontendService(
      { baseUrl: "http://127.0.0.1:3000", apiBaseUrl: "http://127.0.0.1:8000/api/v1" },
      tracker,
      { timeoutMs: 2000, intervalMs: 500 },
      { spawnFn: spawnFn as any, checkUrlFn }
    );

    expect(result.ok).toBe(true);
    expect(result.alreadyRunning).toBe(true);
    expect(spawnFn).not.toHaveBeenCalled();
    expect(tracker.getManagedCount()).toBe(0);
  });

  it("cleans up only its own managed child processes, leaving external processes untouched", () => {
    const tracker = new ManagedProcessTracker();
    const managedChild = createMockProcess();
    const externalChild = createMockProcess();

    tracker.track(managedChild);
    expect(tracker.isManaged(managedChild)).toBe(true);
    expect(tracker.isManaged(externalChild)).toBe(false);

    tracker.cleanup();
    expect(managedChild.kill).toHaveBeenCalledWith("SIGTERM");
    expect(externalChild.kill).not.toHaveBeenCalled();
  });

  it("retries health checks until service becomes ready", async () => {
    let calls = 0;
    const checkFn = vi.fn(async () => {
      calls++;
      return calls >= 3;
    });

    const dots: string[] = [];
    const result = await pollServiceHealth(
      checkFn,
      "Test Service",
      { timeoutMs: 3000, intervalMs: 50 },
      (d) => dots.push(d)
    );

    expect(result.ok).toBe(true);
    expect(result.timedOut).toBe(false);
    expect(calls).toBe(3);
    expect(dots.length).toBe(2);
  });

  it("captures output tail and provides actionable diagnostics on early service exit", async () => {
    const tracker = new ManagedProcessTracker();
    const mockChild = createMockProcess(1);
    const spawnFn = vi.fn(() => {
      // Simulate stdout/stderr lines
      setTimeout(() => {
        mockChild.stderr.emit("data", Buffer.from("ModuleNotFoundError: No module named 'uvicorn'\n"));
        mockChild.stderr.emit("data", Buffer.from("Failed to bind port 8000\n"));
      }, 5);
      return mockChild;
    });

    const checkUrlFn = vi.fn(async () => false);

    const result = await ensureBackendService(
      { apiBaseUrl: "http://127.0.0.1:8000/api/v1" },
      tracker,
      { timeoutMs: 500, intervalMs: 50 },
      { spawnFn: spawnFn as any, checkUrlFn }
    );

    expect(result.ok).toBe(false);
    expect(result.alreadyRunning).toBe(false);
    expect(result.errorDiagnostic).toContain("Backend process exited early with code 1");
    expect(result.errorDiagnostic).toContain("ModuleNotFoundError: No module named 'uvicorn'");
  });

  it("reports clear timeout metrics when health check times out", async () => {
    const tracker = new ManagedProcessTracker();
    const mockChild = createMockProcess(null); // still alive
    const spawnFn = vi.fn(() => mockChild);
    const checkUrlFn = vi.fn(async () => false);

    const result = await ensureFrontendService(
      { baseUrl: "http://127.0.0.1:3000", apiBaseUrl: "http://127.0.0.1:8000/api/v1" },
      tracker,
      { timeoutMs: 200, intervalMs: 50 },
      { spawnFn: spawnFn as any, checkUrlFn }
    );

    expect(result.ok).toBe(false);
    expect(result.errorDiagnostic).toContain("Frontend health check timed out");
    expect(result.errorDiagnostic).toContain("configured limit: 200ms");
  });
});
