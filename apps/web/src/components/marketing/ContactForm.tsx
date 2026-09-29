"use client";

/**
 * Figma marketing `Contact.tsx` form — Name · Email · Message · "Send message"
 * → success card. Submits to the public `POST /api/v1/contact`; messages land
 * in the administrator inbox. Client-side validation mirrors the server rules.
 */

import { useState, type FormEvent } from "react";

import { api } from "@/lib/api/client";

const INPUT =
  "w-full rounded-[10px] border border-[var(--border)] bg-[var(--surface-2)] px-3.5 py-2.5 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]";
const LABEL = "mb-1.5 block font-mono text-xs uppercase tracking-[0.06em] text-[var(--muted)]";

export function validateContact(input: { name: string; email: string; message: string }): string | null {
  if (!input.name.trim()) return "Please enter your name.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.email.trim())) return "Please enter a valid email address.";
  if (input.message.trim().length < 10) return "Please write at least 10 characters.";
  if (input.message.trim().length > 4000) return "Message must be under 4,000 characters.";
  return null;
}

export function ContactForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [receipt, setReceipt] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const problem = validateContact({ name, email, message });
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    setState("sending");
    try {
      const res = await api.contactSubmit({
        name: name.trim(),
        email: email.trim(),
        message: message.trim(),
        source: "contact-page",
      });
      setReceipt(res.message_id);
      setState("sent");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send. Please try again.");
      setState("idle");
    }
  }

  if (state === "sent") {
    return (
      <div
        role="status"
        className="rounded-xl border border-[color-mix(in_srgb,var(--c-profit)_20%,transparent)] bg-[color-mix(in_srgb,var(--c-profit)_8%,transparent)] p-6 text-center"
      >
        <div className="mb-3 text-2xl text-[var(--c-profit)]" aria-hidden="true">✓</div>
        <p className="text-[15px] text-[var(--c-profit)]">Message sent</p>
        <p className="mt-2 text-[13px] text-[var(--muted)]">
          Your message has been received. We’ll get back to you within 1–2 business days.
        </p>
        {receipt ? (
          <p className="mt-3 font-mono text-[10px] text-[var(--muted)]">Reference {receipt}</p>
        ) : null}
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3.5" aria-label="Contact form" noValidate>
      <div>
        <label htmlFor="contact-name" className={LABEL}>Name</label>
        <input id="contact-name" className={INPUT} placeholder="Name" value={name} maxLength={120} autoComplete="name" onChange={(e) => setName(e.target.value)} required />
      </div>
      <div>
        <label htmlFor="contact-email" className={LABEL}>Email</label>
        <input id="contact-email" type="email" className={INPUT} placeholder="Email" value={email} maxLength={254} autoComplete="email" onChange={(e) => setEmail(e.target.value)} required />
      </div>
      <div>
        <label htmlFor="contact-message" className={LABEL}>Message</label>
        <textarea id="contact-message" rows={4} className={`${INPUT} resize-y`} placeholder="How can we help?" value={message} maxLength={4000} onChange={(e) => setMessage(e.target.value)} required />
      </div>
      {error ? (
        <p role="alert" className="text-xs text-[var(--danger-fg)]">{error}</p>
      ) : null}
      <button
        type="submit"
        disabled={state === "sending"}
        className="min-h-11 rounded-[10px] bg-[var(--c-dsp)] px-4 text-sm font-medium text-white transition-opacity disabled:opacity-60"
      >
        {state === "sending" ? "Sending…" : "Send message"}
      </button>
    </form>
  );
}
