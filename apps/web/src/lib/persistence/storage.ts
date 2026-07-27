import type { UserDataBundle } from "./types";

const STORAGE_PREFIX = "dsp.userData.v1";

let memoryCache = new Map<string, UserDataBundle>();

function storageKey(subject: string): string {
  return `${STORAGE_PREFIX}.${subject}`;
}

export function readUserData(subject: string): UserDataBundle | null {
  if (!subject) return null;

  const cached = memoryCache.get(subject);
  if (cached) return structuredClone(cached);

  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(storageKey(subject));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as UserDataBundle;
    if (!parsed?.version || parsed.subject !== subject) return null;
    memoryCache.set(subject, parsed);
    return structuredClone(parsed);
  } catch {
    return null;
  }
}

export function writeUserData(bundle: UserDataBundle): void {
  memoryCache.set(bundle.subject, structuredClone(bundle));
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      storageKey(bundle.subject),
      JSON.stringify(bundle),
    );
  } catch {
    /* quota */
  }
}

export function clearMemoryUserData(subject?: string): void {
  if (subject) {
    memoryCache.delete(subject);
    return;
  }
  memoryCache.clear();
}

/** Test helper */
export function _resetPersistenceStorage(): void {
  memoryCache.clear();
  if (typeof window === "undefined") return;
  for (let i = window.localStorage.length - 1; i >= 0; i -= 1) {
    const key = window.localStorage.key(i);
    if (key?.startsWith(STORAGE_PREFIX)) {
      window.localStorage.removeItem(key);
    }
  }
}
