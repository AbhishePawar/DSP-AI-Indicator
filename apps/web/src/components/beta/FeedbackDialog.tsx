"use client";

import { useEffect, useId, useState, type FormEvent } from "react";
import { usePathname } from "next/navigation";

import { useFeedback } from "@/components/beta/FeedbackContext";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import {
  APP_VERSION,
  FEEDBACK_CATEGORIES,
  SEVERITIES,
  collectBrowserInfo,
  collectDeviceInfo,
  submitFeedback,
  type FeedbackCategory,
  type FeedbackSeverity,
} from "@/lib/beta/betaModel";

export function FeedbackButton() {
  const { openFeedback } = useFeedback();
  return (
    <button
      type="button"
      className="fixed bottom-5 left-5 z-40 min-h-11 rounded-md border border-[var(--accent)] bg-[var(--surface)] px-4 py-2 text-sm font-medium shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] md:left-auto md:right-28"
      aria-haspopup="dialog"
      onClick={() => openFeedback()}
    >
      Feedback
    </button>
  );
}

export function FeedbackDialog() {
  const {
    dialogOpen,
    closeFeedback,
    sectionId,
    presetCategory,
    bumpRefresh,
  } = useFeedback();
  const pathname = usePathname();
  const titleId = useId();
  const [category, setCategory] = useState<FeedbackCategory>("ux_feedback");
  const [severity, setSeverity] = useState<FeedbackSeverity>("medium");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [satisfaction, setSatisfaction] = useState<number | "">("");
  const [screenshotNote, setScreenshotNote] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (dialogOpen && presetCategory) setCategory(presetCategory);
  }, [dialogOpen, presetCategory]);

  useEffect(() => {
    if (!dialogOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeFeedback();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dialogOpen, closeFeedback]);

  if (!dialogOpen) return null;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      setStatus("Title and description are required.");
      return;
    }
    submitFeedback({
      category,
      severity,
      title,
      description,
      pagePath: pathname,
      sectionId,
      satisfaction: satisfaction === "" ? null : Number(satisfaction),
      screenshotNote: screenshotNote || "Screenshot capture placeholder — paste not stored as image.",
    });
    setTitle("");
    setDescription("");
    setSatisfaction("");
    setScreenshotNote("");
    setStatus("Thanks — feedback saved locally on this device only.");
    bumpRefresh();
    window.setTimeout(() => {
      setStatus(null);
      closeFeedback();
    }, 900);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-3 sm:items-center"
      role="presentation"
      onClick={closeFeedback}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <Card className="border-0">
          <CardHeader
            title="Send feedback"
            description="Do not include research data, portfolio holdings, or secrets."
            action={
              <Button variant="ghost" size="sm" onClick={closeFeedback}>
                Close
              </Button>
            }
          />
          <CardBody>
            <h2 id={titleId} className="sr-only">
              Feedback form
            </h2>
            <form className="space-y-3" onSubmit={onSubmit}>
              <label className="block text-sm">
                Category
                <select
                  className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2"
                  value={category}
                  onChange={(e) => setCategory(e.target.value as FeedbackCategory)}
                >
                  {FEEDBACK_CATEGORIES.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                Severity
                <select
                  className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2"
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value as FeedbackSeverity)}
                >
                  {SEVERITIES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                Title
                <input
                  className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] px-3"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={160}
                  required
                />
              </label>
              <label className="block text-sm">
                Description
                <textarea
                  className="mt-1 min-h-24 w-full rounded-md border border-[var(--border)] px-3 py-2"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                />
              </label>
              <label className="block text-sm">
                Satisfaction (1–5, optional)
                <input
                  type="number"
                  min={1}
                  max={5}
                  className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] px-3"
                  value={satisfaction}
                  onChange={(e) =>
                    setSatisfaction(e.target.value === "" ? "" : Number(e.target.value))
                  }
                />
              </label>
              <label className="block text-sm">
                Screenshot placeholder note
                <input
                  className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] px-3"
                  value={screenshotNote}
                  onChange={(e) => setScreenshotNote(e.target.value)}
                  placeholder="Describe what a screenshot would show (no upload)"
                />
              </label>
              <div className="rounded-md border border-dashed border-[var(--border)] p-2 text-xs text-[var(--muted)]">
                <p>Page: {pathname}</p>
                <p>Section: {sectionId ?? "—"}</p>
                <p>App version: {APP_VERSION}</p>
                <p>Browser: {collectBrowserInfo()}</p>
                <p>Device: {collectDeviceInfo()}</p>
              </div>
              {status ? (
                <p className="text-sm" role="status">
                  {status}
                </p>
              ) : null}
              <Button type="submit" className="w-full">
                Submit feedback
              </Button>
            </form>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

export function FeedbackCard({
  title,
  meta,
}: {
  title: string;
  meta: string;
}) {
  return (
    <Card>
      <CardHeader title={title} />
      <CardBody className="text-sm text-[var(--muted)]">{meta}</CardBody>
    </Card>
  );
}
