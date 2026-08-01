"use client";

import { useEffect, useId, useState, type FormEvent } from "react";
import { usePathname, useSearchParams } from "next/navigation";

import { useFeedback } from "@/components/beta/FeedbackContext";
import {
  Button,
  Checkbox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ds";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { useAuth } from "@/lib/auth/AuthProvider";
import { betaApi } from "@/lib/beta/betaApi";
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
  const searchParams = useSearchParams();
  const { session } = useAuth();
  const titleId = useId();
  const [category, setCategory] = useState<FeedbackCategory>("general_comments");
  const [severity, setSeverity] = useState<FeedbackSeverity>("medium");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [satisfaction, setSatisfaction] = useState<number | "">("");
  const [screenshotNote, setScreenshotNote] = useState("");
  const [companyAnalysed, setCompanyAnalysed] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (dialogOpen && presetCategory) setCategory(presetCategory);
  }, [dialogOpen, presetCategory]);

  useEffect(() => {
    if (!dialogOpen) return;
    const symbol = searchParams.get("symbol") || searchParams.get("ticker") || "";
    if (symbol) setCompanyAnalysed(symbol.toUpperCase());
  }, [dialogOpen, searchParams]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      setStatus("Title and description are required.");
      return;
    }
    if (!acknowledged) {
      setStatus("Please acknowledge before submitting.");
      return;
    }
    const local = submitFeedback({
      category,
      severity,
      title,
      description,
      pagePath: pathname,
      sectionId,
      satisfaction: satisfaction === "" ? null : Number(satisfaction),
      screenshotNote:
        screenshotNote ||
        "Screenshot attachment optional — describe visual context; images are not uploaded.",
      companyAnalysed: companyAnalysed || null,
      acknowledgement: true,
    });

    try {
      await betaApi.submitFeedback(
        {
          category,
          severity,
          title: local.title,
          description: local.description,
          rating: local.satisfaction,
          screenshot_note: local.screenshotNote,
          app_version: local.appVersion,
          browser: local.browserInfo,
          company_analysed: local.companyAnalysed,
          page_path: local.pagePath,
          acknowledgement: true,
        },
        session?.accessToken,
      );
      setStatus("Thanks — feedback acknowledged and recorded.");
    } catch {
      setStatus("Thanks — feedback saved locally (server sync unavailable).");
    }

    setTitle("");
    setDescription("");
    setSatisfaction("");
    setScreenshotNote("");
    setAcknowledged(false);
    bumpRefresh();
    window.setTimeout(() => {
      setStatus(null);
      closeFeedback();
    }, 1100);
  };

  return (
    <Dialog
      open={dialogOpen}
      onOpenChange={(open) => {
        if (!open) closeFeedback();
      }}
    >
      <DialogContent
        className="max-h-[90vh] overflow-y-auto sm:max-w-lg"
        aria-labelledby={titleId}
      >
        <DialogHeader>
          <DialogTitle id={titleId}>Send feedback</DialogTitle>
          <DialogDescription>
            Do not include research data, portfolio holdings, or secrets.
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-3" onSubmit={(e) => void onSubmit(e)}>
          <label className="block text-sm">
            Category
            <select
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
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
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
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
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={160}
              required
            />
          </label>
          <label className="block text-sm">
            Description
            <textarea
              className="mt-1 min-h-24 w-full rounded-md border border-[var(--border)] px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm">
            Rating (1–5)
            <input
              type="number"
              min={1}
              max={5}
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              value={satisfaction}
              onChange={(e) =>
                setSatisfaction(e.target.value === "" ? "" : Number(e.target.value))
              }
            />
          </label>
          <label className="block text-sm">
            Company analysed (optional ticker)
            <input
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              value={companyAnalysed}
              onChange={(e) => setCompanyAnalysed(e.target.value.toUpperCase())}
              maxLength={16}
              placeholder="e.g. AAPL"
            />
          </label>
          <label className="block text-sm">
            Screenshot note (optional attachment substitute)
            <input
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              value={screenshotNote}
              onChange={(e) => setScreenshotNote(e.target.value)}
              placeholder="Describe visual context — images are not uploaded"
            />
          </label>
          <label className="flex items-start gap-2 text-sm">
            <Checkbox
              checked={acknowledged}
              onCheckedChange={(v) => setAcknowledged(v === true)}
              aria-label="Acknowledge feedback submission"
              className="mt-0.5"
            />
            <span>
              I acknowledge this feedback contains no secrets, holdings, or
              research envelopes, and may be reviewed by beta operators.
            </span>
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
          <Button type="submit" className="w-full" disabled={!acknowledged}>
            Submit feedback
          </Button>
        </form>
      </DialogContent>
    </Dialog>
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
