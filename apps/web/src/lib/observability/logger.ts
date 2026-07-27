/**
 * Frontend logging abstraction — session-scoped, swappable for external telemetry later.
 * No external services in EPIC-007.
 */

export type LogLevel = "debug" | "info" | "warn" | "error";

export type LogEntry = {
  id: string;
  level: LogLevel;
  message: string;
  context?: Record<string, unknown>;
  timestamp: string;
};

export type ClientErrorSource =
  | "global-error-boundary"
  | "section-error-boundary"
  | "route-error"
  | "global-route-error"
  | "api"
  | "research"
  | "unknown";

export type ClientErrorEntry = {
  id: string;
  message: string;
  source: ClientErrorSource;
  stack?: string;
  digest?: string;
  timestamp: string;
};

const MAX_LOG_ENTRIES = 200;
const MAX_ERROR_ENTRIES = 50;

let logBuffer: LogEntry[] = [];
let errorBuffer: ClientErrorEntry[] = [];

function createId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function pushLog(level: LogLevel, message: string, context?: Record<string, unknown>): LogEntry {
  const entry: LogEntry = {
    id: createId("log"),
    level,
    message,
    context,
    timestamp: new Date().toISOString(),
  };
  logBuffer = [entry, ...logBuffer].slice(0, MAX_LOG_ENTRIES);

  const prefix = `[DSP ${level.toUpperCase()}]`;
  if (level === "error") {
    console.error(prefix, message, context ?? "");
  } else if (level === "warn") {
    console.warn(prefix, message, context ?? "");
  } else if (level === "debug") {
    console.debug(prefix, message, context ?? "");
  } else {
    console.info(prefix, message, context ?? "");
  }

  return entry;
}

export const logger = {
  debug(message: string, context?: Record<string, unknown>): LogEntry {
    return pushLog("debug", message, context);
  },

  info(message: string, context?: Record<string, unknown>): LogEntry {
    return pushLog("info", message, context);
  },

  warn(message: string, context?: Record<string, unknown>): LogEntry {
    return pushLog("warn", message, context);
  },

  error(message: string, context?: Record<string, unknown>): LogEntry {
    return pushLog("error", message, context);
  },

  recordClientError(
    error: Error | string,
    source: ClientErrorSource,
    options?: { digest?: string },
  ): ClientErrorEntry {
    const message = typeof error === "string" ? error : error.message;
    const entry: ClientErrorEntry = {
      id: createId("err"),
      message,
      source,
      stack: typeof error === "string" ? undefined : error.stack,
      digest: options?.digest,
      timestamp: new Date().toISOString(),
    };
    errorBuffer = [entry, ...errorBuffer].slice(0, MAX_ERROR_ENTRIES);
    pushLog("error", message, { source, digest: options?.digest });
    return entry;
  },

  getRecentLogs(limit = 50): LogEntry[] {
    return logBuffer.slice(0, limit);
  },

  getSessionErrors(limit = 25): ClientErrorEntry[] {
    return errorBuffer.slice(0, limit);
  },

  /** Test helper — reset in-memory buffers. */
  _resetForTests(): void {
    logBuffer = [];
    errorBuffer = [];
  },
};
