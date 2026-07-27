/** In-memory timing history for diagnostics — no external deps. */

export type TimingRecord = {
  label: string;
  durationMs: number;
  endedAt: string;
};

const timingHistory: TimingRecord[] = [];
const MAX_TIMING_HISTORY = 30;

export function recordTiming(label: string, durationMs: number): TimingRecord {
  const entry: TimingRecord = {
    label,
    durationMs,
    endedAt: new Date().toISOString(),
  };
  timingHistory.unshift(entry);
  if (timingHistory.length > MAX_TIMING_HISTORY) {
    timingHistory.pop();
  }
  return entry;
}

export function getRecentTimings(limit = 20): TimingRecord[] {
  return timingHistory.slice(0, limit);
}

export function _resetTimingsForTests(): void {
  timingHistory.length = 0;
}
