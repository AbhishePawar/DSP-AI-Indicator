import { ChildProcess, spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const filename = fileURLToPath(import.meta.url);
const dirname = path.dirname(filename);
const defaultWebDir = path.resolve(dirname, "../../..");
const defaultRepoRoot = path.resolve(defaultWebDir, "../..");

export type HealthConfig = {
  timeoutMs: number;
  intervalMs: number;
};

export function getHealthConfig(env: NodeJS.ProcessEnv = process.env): HealthConfig {
  const rawTimeout = Number(env.DSP_P109_HEALTH_TIMEOUT_MS);
  const rawInterval = Number(env.DSP_P109_HEALTH_INTERVAL_MS);

  const timeoutMs =
    Number.isFinite(rawTimeout) && rawTimeout >= 1000 && rawTimeout <= 120_000
      ? rawTimeout
      : 25_000;

  const intervalMs =
    Number.isFinite(rawInterval) && rawInterval >= 100 && rawInterval <= 10_000
      ? rawInterval
      : 1_000;

  return { timeoutMs, intervalMs };
}

export class ManagedProcessTracker {
  private readonly managedChildren = new Set<ChildProcess>();
  private readonly outputBuffers = new Map<ChildProcess, string[]>();

  track(child: ChildProcess, maxBufferLines = 20): void {
    this.managedChildren.add(child);
    const buffer: string[] = [];
    this.outputBuffers.set(child, buffer);

    const append = (data: Buffer | string) => {
      const text = data.toString();
      const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
      for (const line of lines) {
        buffer.push(line);
        if (buffer.length > maxBufferLines) buffer.shift();
      }
    };

    child.stdout?.on("data", append);
    child.stderr?.on("data", append);

    child.on("close", () => {
      // Retain buffer for diagnostics
    });
  }

  isManaged(child: ChildProcess): boolean {
    return this.managedChildren.has(child);
  }

  getOutputTail(child: ChildProcess): string[] {
    return this.outputBuffers.get(child) ?? [];
  }

  getManagedCount(): number {
    return this.managedChildren.size;
  }

  cleanup(): void {
    for (const child of this.managedChildren) {
      if (child && !child.killed) {
        try {
          child.kill("SIGTERM");
        } catch {
          /* ignore */
        }
      }
    }
  }
}

export type HealthChecker = (url: string, timeoutMs?: number) => Promise<boolean>;

export async function pollServiceHealth(
  checkFn: () => Promise<boolean>,
  description: string,
  config: HealthConfig,
  onProgress?: (dot: string) => void
): Promise<{ ok: boolean; elapsedMs: number; timedOut: boolean }> {
  const maxAttempts = Math.max(1, Math.ceil(config.timeoutMs / config.intervalMs));
  const startTime = Date.now();

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const isHealthy = await checkFn();
    if (isHealthy) {
      return { ok: true, elapsedMs: Date.now() - startTime, timedOut: false };
    }
    onProgress?.(".");
    if (attempt < maxAttempts) {
      await new Promise((r) => setTimeout(r, config.intervalMs));
    }
  }

  return { ok: false, elapsedMs: Date.now() - startTime, timedOut: true };
}

export type ServiceStartupOptions = {
  webDir?: string;
  repoRoot?: string;
  spawnFn?: typeof spawn;
  checkUrlFn?: HealthChecker;
  onProgress?: (msg: string) => void;
};

export async function ensureBackendService(
  config: { apiBaseUrl: string; adminPassword?: string },
  tracker: ManagedProcessTracker,
  healthConfig: HealthConfig = getHealthConfig(),
  options: ServiceStartupOptions = {}
): Promise<{ ok: boolean; alreadyRunning: boolean; child?: ChildProcess; errorDiagnostic?: string }> {
  const checkUrl = options.checkUrlFn ?? (async (url) => {
    try {
      const res = await fetch(url).catch(() => null);
      return res !== null && res.ok;
    } catch {
      return false;
    }
  });

  const apiRoot = config.apiBaseUrl.replace(/\/api\/v1\/?$/, "");
  const isLive = await checkUrl(`${apiRoot}/health/live`, 1000);
  const isReady = await checkUrl(`${apiRoot}/health/ready`, 1000);

  if (isLive && isReady) {
    return { ok: true, alreadyRunning: true };
  }

  const spawner = options.spawnFn ?? spawn;
  const root = options.repoRoot ?? defaultRepoRoot;

  let child: ChildProcess;
  try {
    child = spawner(
      "python",
      ["-m", "uvicorn", "api_platform.api.app:app", "--host", "127.0.0.1", "--port", "8000"],
      {
        cwd: root,
        env: {
          ...process.env,
          DSP_ENVIRONMENT: "development",
          DSP_INFRA_OFFLINE: "0",
          DSP_MARKET_QUOTE_MEMORY: "1",
          DSP_FINANCIAL_STATEMENT_MEMORY: "1",
          DSP_P109_E2E_FIXTURE: "1",
          DSP_SEED_ADMIN_PASSWORD: config.adminPassword,
          DSP_COOKIE_AUTH: "true",
          DSP_ENABLE_SECURITY: "false",
          PYTHONUNBUFFERED: "1",
          NEXT_PUBLIC_API_BASE_URL: config.apiBaseUrl,
        },
        stdio: ["ignore", "pipe", "pipe"],
      }
    );
    tracker.track(child);
  } catch (err) {
    return {
      ok: false,
      alreadyRunning: false,
      errorDiagnostic: `Failed to spawn Python process: ${(err as Error).message}`,
    };
  }

  const pollResult = await pollServiceHealth(
    async () => {
      if (child.exitCode !== null) return false;
      const l = await checkUrl(`${apiRoot}/health/live`, 1000);
      const r = await checkUrl(`${apiRoot}/health/ready`, 1000);
      return l && r;
    },
    `Backend (${apiRoot})`,
    healthConfig,
    options.onProgress
  );

  if (child.exitCode !== null) {
    const tail = tracker.getOutputTail(child);
    return {
      ok: false,
      alreadyRunning: false,
      child,
      errorDiagnostic: [
        `Backend process exited early with code ${child.exitCode}.`,
        tail.length > 0 ? "Output tail:\n  " + tail.join("\n  ") : "No output captured.",
      ].join("\n"),
    };
  }

  if (pollResult.timedOut) {
    const tail = tracker.getOutputTail(child);
    return {
      ok: false,
      alreadyRunning: false,
      child,
      errorDiagnostic: [
        `Backend health check timed out after ${pollResult.elapsedMs}ms (configured limit: ${healthConfig.timeoutMs}ms).`,
        tail.length > 0 ? "Output tail:\n  " + tail.join("\n  ") : "No output captured.",
      ].join("\n"),
    };
  }

  return { ok: true, alreadyRunning: false, child };
}

export async function ensureFrontendService(
  config: { baseUrl: string; apiBaseUrl: string },
  tracker: ManagedProcessTracker,
  healthConfig: HealthConfig = getHealthConfig(),
  options: ServiceStartupOptions = {}
): Promise<{ ok: boolean; alreadyRunning: boolean; child?: ChildProcess; errorDiagnostic?: string }> {
  const checkUrl = options.checkUrlFn ?? (async (url) => {
    try {
      const res = await fetch(url).catch(() => null);
      return res !== null && res.ok;
    } catch {
      return false;
    }
  });

  const isUp = await checkUrl(config.baseUrl, 1000);
  if (isUp) {
    return { ok: true, alreadyRunning: true };
  }

  const spawner = options.spawnFn ?? spawn;
  const web = options.webDir ?? defaultWebDir;

  let child: ChildProcess;
  try {
    child = spawner("npm", ["run", "dev", "--", "-p", "3000"], {
      cwd: web,
      env: {
        ...process.env,
        PORT: "3000",
        HOSTNAME: "127.0.0.1",
        NEXT_PUBLIC_API_BASE_URL: config.apiBaseUrl,
      },
      stdio: ["ignore", "pipe", "pipe"],
    });
    tracker.track(child);
  } catch (err) {
    return {
      ok: false,
      alreadyRunning: false,
      errorDiagnostic: `Failed to spawn npm process: ${(err as Error).message}`,
    };
  }

  const pollResult = await pollServiceHealth(
    async () => {
      if (child.exitCode !== null) return false;
      return checkUrl(config.baseUrl, 1000);
    },
    `Frontend (${config.baseUrl})`,
    healthConfig,
    options.onProgress
  );

  if (child.exitCode !== null) {
    const tail = tracker.getOutputTail(child);
    return {
      ok: false,
      alreadyRunning: false,
      child,
      errorDiagnostic: [
        `Frontend process exited early with code ${child.exitCode}.`,
        tail.length > 0 ? "Output tail:\n  " + tail.join("\n  ") : "No output captured.",
      ].join("\n"),
    };
  }

  if (pollResult.timedOut) {
    const tail = tracker.getOutputTail(child);
    return {
      ok: false,
      alreadyRunning: false,
      child,
      errorDiagnostic: [
        `Frontend health check timed out after ${pollResult.elapsedMs}ms (configured limit: ${healthConfig.timeoutMs}ms).`,
        tail.length > 0 ? "Output tail:\n  " + tail.join("\n  ") : "No output captured.",
      ].join("\n"),
    };
  }

  return { ok: true, alreadyRunning: false, child };
}
