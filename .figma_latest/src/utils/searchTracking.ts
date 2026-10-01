const GLOBAL_KEY = 'dsp_search_log'
const MAX_ENTRIES = 500
const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000

interface SearchEntry {
  symbol: string
  ts: number
}

// ─── Storage helpers ──────────────────────────────────────────────────────────

function userKey(email: string) {
  // Namespace per authenticated user — different users never share a key
  return `dsp_search_user_${email.toLowerCase().trim()}`
}

function loadEntries(key: string): SearchEntry[] {
  try {
    return JSON.parse(localStorage.getItem(key) ?? '[]')
  } catch {
    return []
  }
}

function saveEntries(key: string, entries: SearchEntry[]) {
  localStorage.setItem(key, JSON.stringify(entries.slice(-MAX_ENTRIES)))
}

// ─── Write ────────────────────────────────────────────────────────────────────

/**
 * Record a search for the given symbol.
 * @param symbol  Stock ticker, e.g. "TCS"
 * @param userEmail  Authenticated user's email. If omitted, only global log is updated.
 */
export function recordSearch(symbol: string, userEmail?: string | null) {
  const clean = symbol.trim().toUpperCase()
  if (!clean) return

  const entry: SearchEntry = { symbol: clean, ts: Date.now() }

  // Always write to global trending log
  const global = loadEntries(GLOBAL_KEY)
  global.push(entry)
  saveEntries(GLOBAL_KEY, global)

  // Also write to per-user log when a user is authenticated
  if (userEmail) {
    const key = userKey(userEmail)
    const personal = loadEntries(key)
    personal.push(entry)
    saveEntries(key, personal)
  }
}

// ─── Read: Trending (global, last 7 days) ─────────────────────────────────────

export function getTrending(n = 5, fallback: string[] = []): string[] {
  const cutoff = Date.now() - SEVEN_DAYS_MS
  const recent = loadEntries(GLOBAL_KEY).filter(e => e.ts >= cutoff)
  if (recent.length < 3) return fallback.slice(0, n)
  return topN(recent, n)
}

// ─── Read: Personal history (per-user, all time, by frequency) ────────────────

/**
 * Returns symbols the given user has searched most, sorted by frequency.
 * Returns [] if the user has no history or is not logged in.
 * Scoped strictly to userEmail — never returns another user's data.
 */
export function getPersonalHistory(userEmail: string | null | undefined, n = 5): string[] {
  if (!userEmail) return []
  const entries = loadEntries(userKey(userEmail))
  if (entries.length === 0) return []
  return topN(entries, n)
}

// ─── Shared util ──────────────────────────────────────────────────────────────

function topN(entries: SearchEntry[], n: number): string[] {
  const counts: Record<string, number> = {}
  for (const e of entries) {
    counts[e.symbol] = (counts[e.symbol] ?? 0) + 1
  }
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([symbol]) => symbol)
}
