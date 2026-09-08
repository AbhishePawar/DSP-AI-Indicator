/**
 * Client-side rate limiter using a sliding-window token-bucket approach.
 * Prevents accidental API hammering from the browser.
 *
 * Usage:
 *   const limiter = createRateLimiter({ maxRequests: 10, windowMs: 60_000 });
 *   if (!limiter.tryConsume()) throw new Error("Rate limit exceeded");
 */

export interface RateLimiterOptions {
  /** Maximum number of requests allowed within the window. */
  maxRequests: number;
  /** Window duration in milliseconds. */
  windowMs: number;
}

export interface RateLimiter {
  /** Returns true if the request is allowed; false if rate-limited. */
  tryConsume(): boolean;
  /** Remaining requests in the current window. */
  remaining(): number;
  /** Milliseconds until the oldest request expires. */
  resetInMs(): number;
  /** Reset the limiter state. */
  reset(): void;
}

/**
 * Create a sliding-window rate limiter scoped to a single call site.
 */
export function createRateLimiter(options: RateLimiterOptions): RateLimiter {
  const { maxRequests, windowMs } = options;
  let timestamps: number[] = [];

  function prune(now: number): void {
    const cutoff = now - windowMs;
    timestamps = timestamps.filter((t) => t > cutoff);
  }

  return {
    tryConsume(): boolean {
      const now = Date.now();
      prune(now);
      if (timestamps.length >= maxRequests) return false;
      timestamps.push(now);
      return true;
    },

    remaining(): number {
      prune(Date.now());
      return Math.max(0, maxRequests - timestamps.length);
    },

    resetInMs(): number {
      if (timestamps.length === 0) return 0;
      const oldest = timestamps[0];
      return Math.max(0, oldest + windowMs - Date.now());
    },

    reset(): void {
      timestamps = [];
    },
  };
}

/**
 * Pre-built limiters for common DSP call sites.
 * Import and call `.tryConsume()` before firing the request.
 */
export const analysisRateLimiter = createRateLimiter({
  maxRequests: 5,
  windowMs: 60_000, // 5 analyses per minute
});

export const searchRateLimiter = createRateLimiter({
  maxRequests: 30,
  windowMs: 60_000, // 30 searches per minute
});

export const copilotRateLimiter = createRateLimiter({
  maxRequests: 20,
  windowMs: 60_000, // 20 copilot messages per minute
});
