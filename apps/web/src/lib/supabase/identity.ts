/**
 * Stable UUID v5 for a DSP subject.
 * Used as profiles.id so the same DSP user always maps to the same row.
 */

const UUID_URL_NAMESPACE = "6ba7b810-9dad-11d1-80b4-00c04fd430c8";

function hexToBytes(hex: string): Uint8Array {
  const clean = hex.replace(/-/g, "");
  const out = new Uint8Array(clean.length / 2);
  for (let i = 0; i < out.length; i += 1) {
    out[i] = Number.parseInt(clean.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

function bytesToUuid(bytes: Uint8Array): string {
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20, 32)}`;
}

async function sha1(data: Uint8Array): Promise<Uint8Array> {
  if (typeof globalThis.crypto?.subtle?.digest === "function") {
    const digest = await globalThis.crypto.subtle.digest("SHA-1", data);
    return new Uint8Array(digest);
  }
  const { createHash } = await import("node:crypto");
  return new Uint8Array(createHash("sha1").update(data).digest());
}

export async function dspSubjectToProfileId(subject: string): Promise<string> {
  const trimmed = subject.trim();
  if (!trimmed) {
    throw new Error("DSP subject is required");
  }
  const ns = hexToBytes(UUID_URL_NAMESPACE);
  const name = new TextEncoder().encode(`dsp-user:${trimmed}`);
  const joined = new Uint8Array(ns.length + name.length);
  joined.set(ns, 0);
  joined.set(name, ns.length);
  const hash = await sha1(joined);
  const bytes = hash.slice(0, 16);
  bytes[6] = (bytes[6]! & 0x0f) | 0x50;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  return bytesToUuid(bytes);
}

export function dspSubjectToProfileIdSync(subject: string): string {
  const trimmed = subject.trim();
  if (!trimmed) {
    throw new Error("DSP subject is required");
  }
  // Node-only synchronous path for Next.js route handlers.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { createHash } = require("node:crypto") as typeof import("node:crypto");
  const ns = hexToBytes(UUID_URL_NAMESPACE);
  const name = Buffer.from(`dsp-user:${trimmed}`, "utf8");
  const hash = createHash("sha1")
    .update(Buffer.concat([Buffer.from(ns), name]))
    .digest();
  const bytes = Uint8Array.from(hash.subarray(0, 16));
  bytes[6] = (bytes[6]! & 0x0f) | 0x50;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  return bytesToUuid(bytes);
}
