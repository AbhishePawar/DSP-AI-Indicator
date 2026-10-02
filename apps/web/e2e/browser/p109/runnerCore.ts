import { ChildProcess, execSync, spawn } from "node:child_process";
import fs from "node:fs";
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

export function getHealthConfig(
  env: Partial<NodeJS.ProcessEnv> | Record<string, string | undefined> = process.env,
): HealthConfig {
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

export type PortProcessInfo = {
  port: number;
  pid?: number;
  commandLine?: string;
  workingDirectory?: string;
  isCurrentWorktree?: boolean;
};

export function parsePortFromUrl(rawUrl: string): number {
  try {
    const u = new URL(rawUrl);
    if (u.port) return parseInt(u.port, 10);
    return u.protocol === "https:" ? 443 : 80;
  } catch {
    return 3000;
  }
}

function normalizePath(p?: string): string {
  return p ? path.resolve(p).replace(/\\/g, "/").toLowerCase() : "";
}

export function isSameOrSubdirectory(candidate?: string, expected?: string): boolean | undefined {
  if (!candidate || !expected) return undefined;
  const c = normalizePath(candidate);
  const e = normalizePath(expected);
  return c === e || c.startsWith(e + "/") || e.startsWith(c + "/");
}

export function inspectPortProcess(
  port: number,
  expectedDir?: string,
  platform = process.platform,
): PortProcessInfo | null {
  if (platform === "win32") {
    return inspectPortProcessWin32(port, expectedDir);
  }
  return inspectPortProcessPosix(port, expectedDir);
}

function inspectPortProcessPosix(port: number, expectedDir?: string): PortProcessInfo | null {
  try {
    let pid: number | undefined;
    try {
      const out = execSync(`lsof -i :${port} -sTCP:LISTEN -t`, {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
        timeout: 3000,
      });
      const candidate = parseInt(out.trim().split(/\s+/)[0], 10);
      if (!isNaN(candidate) && candidate > 0) pid = candidate;
    } catch {
      try {
        const out = execSync(`ss -tulpn "sport = :${port}"`, {
          encoding: "utf8",
          stdio: ["ignore", "pipe", "ignore"],
          timeout: 3000,
        });
        const match = out.match(/pid=(\d+)/);
        if (match) pid = parseInt(match[1], 10);
      } catch {
        /* ignore */
      }
    }

    if (!pid) return null;

    let commandLine = "";
    let workingDirectory = "";

    try {
      if (fs.existsSync(`/proc/${pid}/cwd`)) {
        workingDirectory = fs.readlinkSync(`/proc/${pid}/cwd`);
      }
    } catch {
      /* ignore */
    }

    try {
      if (fs.existsSync(`/proc/${pid}/cmdline`)) {
        commandLine = fs.readFileSync(`/proc/${pid}/cmdline`, "utf8").replace(/\0/g, " ").trim();
      }
    } catch {
      /* ignore */
    }

    let isCurrentWorktree: boolean | undefined;
    if (expectedDir) {
      if (workingDirectory) {
        isCurrentWorktree = isSameOrSubdirectory(workingDirectory, expectedDir);
      } else if (commandLine) {
        const normCmd = commandLine.toLowerCase().replace(/\\/g, "/");
        const normExpected = normalizePath(expectedDir);
        isCurrentWorktree = normCmd.includes(normExpected);
      }
    }

    return {
      port,
      pid,
      commandLine,
      workingDirectory,
      isCurrentWorktree,
    };
  } catch {
    return null;
  }
}

function inspectPortProcessWin32(port: number, expectedDir?: string): PortProcessInfo | null {
  try {
    const netstatOut = execSync("netstat -ano -p tcp", {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 4000,
    });

    let pid: number | undefined;
    for (const line of netstatOut.split(/\r?\n/)) {
      if (line.includes(`:${port}`) && line.includes("LISTENING")) {
        const parts = line.trim().split(/\s+/);
        const candidate = parseInt(parts[parts.length - 1], 10);
        if (!isNaN(candidate) && candidate > 0) {
          pid = candidate;
          break;
        }
      }
    }

    if (!pid) return null;

    let commandLine = "";
    let workingDirectory = "";

    try {
      const psCmd = `powershell -NoProfile -NonInteractive -Command "Get-CimInstance Win32_Process -Filter \\"ProcessId = ${pid}\\" | Select-Object -Property CommandLine, ExecutablePath | ConvertTo-Json"`;
      const psOut = execSync(psCmd, {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
        timeout: 4000,
      });
      const parsed = JSON.parse(psOut);
      commandLine = parsed.CommandLine || "";
    } catch {
      try {
        const wmicOut = execSync(`wmic process where processid=${pid} get commandline /format:list`, {
          encoding: "utf8",
          stdio: ["ignore", "pipe", "ignore"],
          timeout: 3000,
        });
        const match = wmicOut.match(/CommandLine=(.*)/i);
        if (match) commandLine = match[1].trim();
      } catch {
        /* ignore */
      }
    }

    let isCurrentWorktree: boolean | undefined;
    if (expectedDir) {
      const normExpected = normalizePath(expectedDir);
      if (commandLine) {
        const normCmd = commandLine.toLowerCase().replace(/\\/g, "/");
        isCurrentWorktree = normCmd.includes(normExpected);
      }
    }

    return {
      port,
      pid,
      commandLine,
      workingDirectory,
      isCurrentWorktree,
    };
  } catch {
    return null;
  }
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

export async function boundedHttpCheck(
  url: string,
  timeoutMs = 2500,
  fetchFn = fetch,
): Promise<{ ok: boolean; status?: number; error?: string }> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const res = await fetchFn(url, { signal: controller.signal });
    clearTimeout(timer);
    return { ok: res.status >= 200 && res.status < 500, status: res.status };
  } catch (err: any) {
    const isTimeout = err?.name === "AbortError" || String(err).includes("aborted");
    return {
      ok: false,
      error: isTimeout
        ? `Request timed out after ${timeoutMs}ms (server accepted TCP connection but returned no HTTP response)`
        : err?.message || String(err),
    };
  }
}

export async function pollServiceHealth(
  checkFn: () => Promise<boolean>,
  description: string,
  config: HealthConfig,
  onProgress?: (dot: string) => void,
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
  inspectPortFn?: (port: number, expectedDir?: string) => PortProcessInfo | null;
  onProgress?: (msg: string) => void;
};

export async function ensureBackendService(
  config: { apiBaseUrl: string; adminPassword?: string },
  tracker: ManagedProcessTracker,
  healthConfig: HealthConfig = getHealthConfig(),
  options: ServiceStartupOptions = {},
): Promise<{ ok: boolean; alreadyRunning: boolean; child?: ChildProcess; errorDiagnostic?: string }> {
  const checkUrl: HealthChecker =
    options.checkUrlFn ??
    (async (url, timeoutMs = 2000) => {
      const result = await boundedHttpCheck(url, timeoutMs);
      return result.ok;
    });

  const apiRoot = config.apiBaseUrl.replace(/\/api\/v1\/?$/, "");
  const isLive = await checkUrl(`${apiRoot}/health/live`, 2000);
  const isReady = await checkUrl(`${apiRoot}/health/ready`, 2000);

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
      },
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
      const l = await checkUrl(`${apiRoot}/health/live`, 1500);
      const r = await checkUrl(`${apiRoot}/health/ready`, 1500);
      return l && r;
    },
    `Backend (${apiRoot})`,
    healthConfig,
    options.onProgress,
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
  options: ServiceStartupOptions = {},
): Promise<{
  ok: boolean;
  alreadyRunning: boolean;
  child?: ChildProcess;
  errorDiagnostic?: string;
  processInfo?: PortProcessInfo | null;
}> {
  const web = options.webDir ?? defaultWebDir;
  const port = parsePortFromUrl(config.baseUrl);

  // 1. Inspect port process ownership
  const inspector = options.inspectPortFn ?? inspectPortProcess;
  const processInfo = inspector(port, web);

  // If port is occupied by a process belonging to a DIFFERENT worktree, block reuse
  if (processInfo && processInfo.isCurrentWorktree === false) {
    const diag = [
      "==================================================",
      "P1-09 FRONTEND PREFLIGHT",
      `Expected URL:       ${config.baseUrl}`,
      `Port:               ${port}`,
      `Occupying Process:  PID ${processInfo.pid ?? "unknown"}`,
      `Process Command:    ${processInfo.commandLine || "unknown"}`,
      `Working Directory:  ${processInfo.workingDirectory || "unknown"}`,
      `Expected Directory: ${web}`,
      "Status:             BLOCKED — port occupied by unrelated Next.js process",
      "",
      "Safe Remediation:",
      `  1. Stop the external process occupying port ${port} from the other repository:`,
      `     ${processInfo.workingDirectory || processInfo.commandLine || "PID " + processInfo.pid}`,
      `  2. Or run P1-09 on a dedicated isolated port:`,
      `     PORT=3001 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3001 pnpm test:p109`,
      "==================================================",
    ].join("\n");

    return {
      ok: false,
      alreadyRunning: false,
      processInfo,
      errorDiagnostic: diag,
    };
  }

  // 2. Perform bounded HTTP readiness check
  const checkUrl: HealthChecker =
    options.checkUrlFn ??
    (async (url, timeoutMs = 2500) => {
      const result = await boundedHttpCheck(url, timeoutMs);
      return result.ok;
    });

  const isUp = await checkUrl(config.baseUrl, 2500);
  if (isUp) {
    return { ok: true, alreadyRunning: true, processInfo };
  }

  // If a process is listening on the port but failed the HTTP check, report responsive failure
  if (processInfo && processInfo.pid) {
    const tail = [
      "==================================================",
      "P1-09 FRONTEND PREFLIGHT — UNRESPONSIVE SERVER",
      `Target URL:         ${config.baseUrl}`,
      `Port:               ${port} is listening (PID ${processInfo.pid})`,
      `HTTP Check:         FAILED — server did not return a valid HTTP response within 2500ms`,
      `Command:            ${processInfo.commandLine || "unknown"}`,
      `Working Directory:  ${processInfo.workingDirectory || "unknown"}`,
      "Remediation:",
      `  The process on port ${port} is frozen or not responding to HTTP requests.`,
      `  Terminate PID ${processInfo.pid} before restarting the runner.`,
      "==================================================",
    ].join("\n");

    return {
      ok: false,
      alreadyRunning: false,
      processInfo,
      errorDiagnostic: tail,
    };
  }

  // 3. Port is free, spawn managed frontend
  const spawner = options.spawnFn ?? spawn;

  let child: ChildProcess;
  try {
    child = spawner("npm", ["run", "dev", "--", "-p", String(port)], {
      cwd: web,
      env: {
        ...process.env,
        PORT: String(port),
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
      return checkUrl(config.baseUrl, 2000);
    },
    `Frontend (${config.baseUrl})`,
    healthConfig,
    options.onProgress,
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

  return { ok: true, alreadyRunning: false, child, processInfo };
}
