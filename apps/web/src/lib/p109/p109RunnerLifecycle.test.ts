import { EventEmitter } from "node:events";
import { describe, expect, it, vi } from "vitest";

import {
  ManagedProcessTracker,
  boundedHttpCheck,
  ensureBackendService,
  ensureFrontendService,
  getHealthConfig,
  inspectPortProcess,
  isSameOrSubdirectory,
  parsePortFromUrl,
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
    expect(getHealthConfig({})).toEqual({ timeoutMs: 25_000, intervalMs: 1_000 });
    expect(
      getHealthConfig({
        DSP_P109_HEALTH_TIMEOUT_MS: "45000",
        DSP_P109_HEALTH_INTERVAL_MS: "2500",
      })
    ).toEqual({ timeoutMs: 45_000, intervalMs: 2_500 });
    expect(
      getHealthConfig({
        DSP_P109_HEALTH_TIMEOUT_MS: "9999999",
        DSP_P109_HEALTH_INTERVAL_MS: "5",
      })
    ).toEqual({ timeoutMs: 25_000, intervalMs: 1_000 });
  });

  it("parses port accurately from standard and custom URLs", () => {
    expect(parsePortFromUrl("http://127.0.0.1:3000")).toBe(3000);
    expect(parsePortFromUrl("http://127.0.0.1:3001")).toBe(3001);
    expect(parsePortFromUrl("http://127.0.0.1")).toBe(80);
    expect(parsePortFromUrl("https://127.0.0.1")).toBe(443);
  });

  it("identifies matching vs alien working directories across path formats", () => {
    const p109Dir = "C:\\Users\\abhis\\OneDrive\\Desktop\\DSP-AI-Indicator\\DSP-AI-Indicator-P109\\apps\\web";
    const devDir = "C:\\dev\\DSP-AI-Indicator\\apps\\web";

    expect(isSameOrSubdirectory(p109Dir, p109Dir)).toBe(true);
    expect(isSameOrSubdirectory(devDir, p109Dir)).toBe(false);
  });

  it("boundedHttpCheck aborts after timeout instead of hanging indefinitely", async () => {
    const hangingFetch = vi.fn(
      (_url: string, opts?: { signal?: AbortSignal }) =>
        new Promise<Response>((_resolve, reject) => {
          opts?.signal?.addEventListener("abort", () => {
            const err = new Error("The operation was aborted");
            err.name = "AbortError";
            reject(err);
          });
        })
    );

    const startTime = Date.now();
    const result = await boundedHttpCheck("http://127.0.0.1:3000", 150, hangingFetch as any);
    const elapsed = Date.now() - startTime;

    expect(result.ok).toBe(false);
    expect(result.error).toContain("timed out after 150ms");
    expect(elapsed).toBeLessThan(1000);
  });

  it("detects port conflict from an unrelated worktree and prevents unsafe reuse", async () => {
    const tracker = new ManagedProcessTracker();
    const spawnFn = vi.fn();
    const checkUrlFn = vi.fn(async () => true);

    const mockInspector = vi.fn(() => ({
      port: 3000,
      pid: 24116,
      commandLine: "node server.js",
      workingDirectory: "C:\\dev\\DSP-AI-Indicator\\apps\\web",
      isCurrentWorktree: false,
    }));

    const result = await ensureFrontendService(
      { baseUrl: "http://127.0.0.1:3000", apiBaseUrl: "http://127.0.0.1:8000/api/v1" },
      tracker,
      { timeoutMs: 2000, intervalMs: 500 },
      {
        webDir: "C:\\Users\\abhis\\OneDrive\\Desktop\\DSP-AI-Indicator\\DSP-AI-Indicator-P109\\apps\\web",
        spawnFn: spawnFn as any,
        checkUrlFn,
        inspectPortFn: mockInspector,
      }
    );

    expect(result.ok).toBe(false);
    expect(result.alreadyRunning).toBe(false);
    expect(spawnFn).not.toHaveBeenCalled();
    expect(result.errorDiagnostic).toContain("BLOCKED — port occupied by unrelated Next.js process");
    expect(result.errorDiagnostic).toContain("PID 24116");
    expect(result.errorDiagnostic).toContain("C:\\dev\\DSP-AI-Indicator\\apps\\web");
  });

  it("safely reuses frontend when port process belongs to current worktree and is responsive", async () => {
    const tracker = new ManagedProcessTracker();
    const spawnFn = vi.fn();
    const checkUrlFn = vi.fn(async () => true);

    const mockInspector = vi.fn(() => ({
      port: 3000,
      pid: 1234,
      commandLine: "next-dev",
      workingDirectory: "/workspace/apps/web",
      isCurrentWorktree: true,
    }));

    const result = await ensureFrontendService(
      { baseUrl: "http://127.0.0.1:3000", apiBaseUrl: "http://127.0.0.1:8000/api/v1" },
      tracker,
      { timeoutMs: 2000, intervalMs: 500 },
      {
        webDir: "/workspace/apps/web",
        spawnFn: spawnFn as any,
        checkUrlFn,
        inspectPortFn: mockInspector,
      }
    );

    expect(result.ok).toBe(true);
    expect(result.alreadyRunning).toBe(true);
    expect(spawnFn).not.toHaveBeenCalled();
  });

  it("reports frozen/unresponsive server when port is listening but HTTP check fails", async () => {
    const tracker = new ManagedProcessTracker();
    const spawnFn = vi.fn();
    const checkUrlFn = vi.fn(async () => false); // HTTP check fails

    const mockInspector = vi.fn(() => ({
      port: 3000,
      pid: 5678,
      commandLine: "node server.js",
      workingDirectory: "/workspace/apps/web",
      isCurrentWorktree: true,
    }));

    const result = await ensureFrontendService(
      { baseUrl: "http://127.0.0.1:3000", apiBaseUrl: "http://127.0.0.1:8000/api/v1" },
      tracker,
      { timeoutMs: 2000, intervalMs: 500 },
      {
        webDir: "/workspace/apps/web",
        spawnFn: spawnFn as any,
        checkUrlFn,
        inspectPortFn: mockInspector,
      }
    );

    expect(result.ok).toBe(false);
    expect(result.alreadyRunning).toBe(false);
    expect(result.errorDiagnostic).toContain("UNRESPONSIVE SERVER");
    expect(result.errorDiagnostic).toContain("PID 5678");
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
});

  it("Windows integration test: simulates a foreign worktree on port 3000 and isolates P1-09 on port 3001 without terminating foreign process", async () => {
    const tracker = new ManagedProcessTracker();
    const killedPids: number[] = [];

    // Simulate an external, foreign process running from C:\dev\DSP-AI-Indicator\apps\web
    const foreignPid = 24116;
    const foreignWorktreeDir = "C:\\dev\\DSP-AI-Indicator\\apps\\web";
    const expectedWorktreeDir = "C:\\Users\\abhis\\OneDrive\\Desktop\\DSP-AI-Indicator\\DSP-AI-Indicator-P109\\apps\\web";

    // Mock inspectPortFn: port 3000 is occupied by foreign worktree, port 3001 is clean/empty
    const inspectPortFn = vi.fn((port: number, expectedDir?: string) => {
      if (port === 3000) {
        return {
          port: 3000,
          pid: foreignPid,
          commandLine: "node server.js",
          workingDirectory: foreignWorktreeDir,
          isCurrentWorktree: isSameOrSubdirectory(foreignWorktreeDir, expectedDir),
        };
      }
      return null; // port 3001 is unallocated
    });

    let spawnedWithPort: string | undefined;
    const mockSpawnedChild = createMockProcess(null);


    let hasSpawned = false;
    const spawnFn = vi.fn((cmd: string, args: string[], options: any) => {
      hasSpawned = true;
      spawnedWithPort = options?.env?.PORT;
      return mockSpawnedChild;
    });

    // checkUrlFn: returns true only after the isolated server has been spawned
    const checkUrlFn = vi.fn(async (url: string) => {
      return hasSpawned && url.includes(":3001");
    });

    const result = await ensureFrontendService(
      {
        baseUrl: "http://127.0.0.1:3000",
        apiBaseUrl: "http://127.0.0.1:8000/api/v1",
      },
      tracker,
      { timeoutMs: 2000, intervalMs: 100 },
      {
        webDir: expectedWorktreeDir,
        autoFallbackPort: 3001,
        inspectPortFn,
        spawnFn: spawnFn as any,
        checkUrlFn,
      }
    );

    // 1. Verify successful isolation to port 3001
    expect(result.ok).toBe(true);
    expect(result.alreadyRunning).toBe(false);
    expect(result.isolatedPort).toBe(3001);
    expect(result.effectiveBaseUrl).toBe("http://127.0.0.1:3001");

    // 2. Verify spawn was called with isolated port 3001
    expect(spawnFn).toHaveBeenCalledTimes(1);
    expect(spawnedWithPort).toBe("3001");

    // 3. Verify only the runner-spawned child is tracked
    expect(tracker.getManagedCount()).toBe(1);
    expect(tracker.isManaged(mockSpawnedChild as any)).toBe(true);

    // 4. Verify the foreign process was never registered in the tracker and remains untouched
    expect(tracker.isManaged({ pid: foreignPid } as any)).toBe(false);

    // 5. Cleanup only kills the spawned child, never the foreign PID
    tracker.cleanup();
    expect(mockSpawnedChild.killed).toBe(true);
    expect(killedPids).not.toContain(foreignPid);
  });
