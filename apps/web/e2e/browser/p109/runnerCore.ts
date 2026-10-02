import { ChildProcess, execSync, spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const filename = fileURLToPath(import.meta.url);
const dirname = path.dirname(filename);
export const defaultWebDir = path.resolve(dirname, "../../..");
export const defaultRepoRoot = path.resolve(defaultWebDir, "../..");

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
    !isNaN(rawTimeout) && rawTimeout >= 1_000 && rawTimeout <= 120_000
      ? rawTimeout
      : 25_000;

  const intervalMs =
    !isNaN(rawInterval) && rawInterval >= 100 && rawInterval <= 10_000
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

export function parsePortFromUrl(rawUrl: string, defaultPort = 3000): number {
  try {
    const u = new URL(rawUrl);
    if (u.port) return parseInt(u.port, 10);
    return u.protocol === "https:" ? 443 : 80;
  } catch {
    return defaultPort;
  }
}

/**
 * Robust cross-platform path normalization for Windows and POSIX:
 * - Converts backslashes to forward slashes
 * - Strips duplicate and trailing slashes
 * - Lowercases for case-insensitive comparisons (Windows drive letters & paths)
 */
export function normalizePath(p?: string): string {
  if (!p) return "";
  let norm = p.trim().replace(/\\/g, "/");
  norm = norm.replace(/\/+/g, "/");
  if (norm.length > 3 && norm.endsWith("/")) {
    norm = norm.slice(0, -1);
  }
  return norm.toLowerCase();
}

/**
 * Checks if a candidate directory matches or is a subdirectory/parent of expected directory.
 */
export function isSameOrSubdirectory(candidate?: string, expected?: string): boolean {
  if (!candidate || !expected) return false;
  const c = normalizePath(candidate);
  const e = normalizePath(expected);
  if (!c || !e) return false;
  return c === e || c.startsWith(e + "/") || e.startsWith(c + "/");
}

export function commandLineContainsWorktree(commandLine?: string, expectedDir?: string): boolean {
  if (!commandLine || !expectedDir) return false;
  const normCmd = commandLine.toLowerCase().replace(/\\/g, "/");
  const normExpected = normalizePath(expectedDir);
  return normCmd.includes(normExpected);
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
        isCurrentWorktree = commandLineContainsWorktree(commandLine, expectedDir);
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
      if (workingDirectory) {
        isCurrentWorktree = isSameOrSubdirectory(workingDirectory, expectedDir);
      } else if (commandLine) {
        isCurrentWorktree = commandLineContainsWorktree(commandLine, expectedDir);
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

  track(child: ChildProcess, maxBufferLines = 40): void {
    this.managedChildren.add(child);
    const buffer: string[] = [];
    this.outputBuffers.set(child, buffer);

    const append = (data: Buffer | string) => {
      const lines = String(data).split(/\r?\n/).filter(Boolean);
      for (const line of lines) {
        buffer.push(line);
        if (buffer.length > maxBufferLines) buffer.shift();
      }
    };

    child.stdout?.on("data", append);
    child.stderr?.on("data", append);

    child.on("exit", () => {
      this.managedChildren.delete(child);
    });
  }

  getRecentOutput(child: ChildProcess): string[] {
    return this.outputBuffers.get(child) ?? [];
  }

  cleanup(): void {
    for (const child of this.managedChildren) {
      try {
        if (!child.killed) {
          child.kill("SIGTERM");
        }
      } catch {
        /* ignore */
      }
    }
    this.managedChildren.clear();
    this.outputBuffers.clear();
  }

  getManagedCount(): number {
    return this.managedChildren.size;
  }

  isManaged(child: ChildProcess): boolean {
    return this.managedChildren.has(child);
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
    const ok = await checkFn();
    if (ok) {
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
  autoFallbackPort?: boolean | number;
};

export type FrontendServiceResult = {
  ok: boolean;
  alreadyRunning: boolean;
  child?: ChildProcess;
  errorDiagnostic?: string;
  processInfo?: PortProcessInfo | null;
  effectiveBaseUrl: string;
  isolatedPort?: number;
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
      errorDiagnostic: `Failed to spawn backend process: ${err instanceof Error ? err.message : String(err)}`,
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
    const recentLines = tracker.getRecentOutput(child);
    const tail = recentLines.length > 0 ? `\n--- Output Tail ---\n${recentLines.join("\n")}` : "";
    return {
      ok: false,
      alreadyRunning: false,
      errorDiagnostic: `Backend process exited early with code ${child.exitCode}.${tail}`,
    };
  }

  if (pollResult.timedOut) {
    const recentLines = tracker.getRecentOutput(child);
    const tail = recentLines.length > 0 ? `\n--- Output Tail ---\n${recentLines.join("\n")}` : "";
    return {
      ok: false,
      alreadyRunning: false,
      errorDiagnostic: `Backend health check timed out after ${pollResult.elapsedMs}ms (configured limit: ${healthConfig.timeoutMs}ms).${tail}`,
    };
  }

  return { ok: true, alreadyRunning: false, child };
}

export async function ensureFrontendService(
  config: { baseUrl: string; apiBaseUrl: string },
  tracker: ManagedProcessTracker,
  healthConfig: HealthConfig = getHealthConfig(),
  options: ServiceStartupOptions = {},
): Promise<FrontendServiceResult> {
  const web = options.webDir ?? defaultWebDir;
  let targetUrl = config.baseUrl;
  let port = parsePortFromUrl(targetUrl);

  const inspector = options.inspectPortFn ?? inspectPortProcess;
  let processInfo = inspector(port, web);

  // If port is occupied by a foreign worktree:
  if (processInfo && processInfo.isCurrentWorktree === false) {
    // If autoFallbackPort is enabled, isolate to alternative port (default 3001)
    if (options.autoFallbackPort) {
      const fallbackPort = typeof options.autoFallbackPort === "number" ? options.autoFallbackPort : 3001;
      options.onProgress?.(`\n[PREFLIGHT] Port ${port} occupied by foreign worktree (${processInfo.workingDirectory || "PID " + processInfo.pid}). Isolating P1-09 frontend to port ${fallbackPort}...`);
      
      port = fallbackPort;
      targetUrl = `http://127.0.0.1:${fallbackPort}`;
      processInfo = inspector(port, web);
    } else {
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
        effectiveBaseUrl: targetUrl,
        errorDiagnostic: diag,
      };
    }
  }

  // 2. Perform bounded HTTP readiness check
  const checkUrl: HealthChecker =
    options.checkUrlFn ??
    (async (url, timeoutMs = 2500) => {
      const result = await boundedHttpCheck(url, timeoutMs);
      return result.ok;
    });

  const isUp = await checkUrl(targetUrl, 2500);
  if (isUp) {
    return { ok: true, alreadyRunning: true, processInfo, effectiveBaseUrl: targetUrl };
  }

  // If a process is listening on the port but failed the HTTP check, report responsive failure
  if (processInfo && processInfo.pid) {
    const tail = [
      "==================================================",
      "P1-09 FRONTEND PREFLIGHT — UNRESPONSIVE SERVER",
      `Target URL:         ${targetUrl}`,
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
      effectiveBaseUrl: targetUrl,
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
      effectiveBaseUrl: targetUrl,
      errorDiagnostic: `Failed to spawn frontend process: ${err instanceof Error ? err.message : String(err)}`,
    };
  }

  const pollResult = await pollServiceHealth(
    async () => {
      if (child.exitCode !== null) return false;
      return checkUrl(targetUrl, 2000);
    },
    `Frontend (${targetUrl})`,
    healthConfig,
    options.onProgress,
  );

  if (child.exitCode !== null) {
    const recentLines = tracker.getRecentOutput(child);
    const tail = recentLines.length > 0 ? `\n--- Output Tail ---\n${recentLines.join("\n")}` : "";
    return {
      ok: false,
      alreadyRunning: false,
      effectiveBaseUrl: targetUrl,
      errorDiagnostic: `Frontend process exited early with code ${child.exitCode}.${tail}`,
    };
  }

  if (pollResult.timedOut) {
    const recentLines = tracker.getRecentOutput(child);
    const tail = recentLines.length > 0 ? `\n--- Output Tail ---\n${recentLines.join("\n")}` : "";
    return {
      ok: false,
      alreadyRunning: false,
      effectiveBaseUrl: targetUrl,
      errorDiagnostic: `Frontend health check timed out after ${pollResult.elapsedMs}ms (configured limit: ${healthConfig.timeoutMs}ms).${tail}`,
    };
  }

  return { ok: true, alreadyRunning: false, child, processInfo, effectiveBaseUrl: targetUrl, isolatedPort: port };
}
