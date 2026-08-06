"use client";

import { useState } from "react";
import Link from "next/link";

import {
  Button,
  Checkbox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ds";
import {
  DISCLAIMER_ACK_BULLETS,
  LEGAL_ROUTES,
  acknowledgeResearchDisclaimer,
} from "@/lib/legal";

export type ResearchDisclaimerGateProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called after the user checks the box and confirms. */
  onAcknowledged: () => void;
};

/**
 * Blocks first report generation until the user acknowledges the research disclaimer.
 */
export function ResearchDisclaimerGate({
  open,
  onOpenChange,
  onAcknowledged,
}: ResearchDisclaimerGateProps) {
  const [checked, setChecked] = useState(false);

  function handleConfirm() {
    if (!checked) return;
    acknowledgeResearchDisclaimer();
    setChecked(false);
    onOpenChange(false);
    onAcknowledged();
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setChecked(false);
        onOpenChange(next);
      }}
    >
      <DialogContent
        className="max-w-lg"
        aria-describedby="research-disclaimer-desc"
      >
        <DialogHeader>
          <DialogTitle>Investment research disclaimer</DialogTitle>
          <DialogDescription id="research-disclaimer-desc">
            Before generating a research report, confirm you understand how DSP
            outputs may be used.
          </DialogDescription>
        </DialogHeader>

        <ul className="list-disc space-y-2 pl-5 text-sm text-[var(--muted)]">
          {DISCLAIMER_ACK_BULLETS.map((bullet) => (
            <li key={bullet}>{bullet}</li>
          ))}
        </ul>

        <p className="text-xs text-[var(--muted)]">
          Full text:{" "}
          <Link
            className="text-[var(--accent)] underline"
            href={LEGAL_ROUTES.disclaimer}
          >
            Investment Research Disclaimer
          </Link>
          {" · "}
          <Link
            className="text-[var(--accent)] underline"
            href={LEGAL_ROUTES.risk}
          >
            Risk Disclosure
          </Link>
        </p>

        <label className="flex items-start gap-2 text-sm text-[var(--fg)]">
          <Checkbox
            checked={checked}
            onCheckedChange={(v) => setChecked(v === true)}
            aria-label="I understand the investment research disclaimer"
            className="mt-0.5"
          />
          <span>
            I have read and understand that DSP reports are for research and
            education, not personalised investment advice.
          </span>
        </label>

        <DialogFooter>
          <Button
            type="button"
            variant="secondary"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            type="button"
            disabled={!checked}
            onClick={handleConfirm}
            aria-disabled={!checked}
          >
            Acknowledge and continue
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
