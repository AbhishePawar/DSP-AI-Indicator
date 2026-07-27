/**
 * In-memory session store for client reviews (no persistence).
 */

import type { ClientReview, ReviewActionStatus, ReviewChecklistItemId, ReviewTemplateId } from "./reviewTypes";
import { createReviewFromTemplate, seedReviews } from "./reviewModels";

let reviews: ClientReview[] = seedReviews.map((r) => ({
  ...r,
  checklist: r.checklist.map((c) => ({ ...c })),
  actions: r.actions.map((a) => ({ ...a })),
  envelopeIds: [...r.envelopeIds],
  clientQuestions: [...r.clientQuestions],
}));
let activeId: string =
  reviews.find((r) => r.status === "in_progress")?.id ?? reviews[0]?.id ?? "";
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

export function subscribeReviews(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getReviewSnapshot() {
  return { reviews, activeId };
}

export function setActiveReviewId(id: string) {
  activeId = id;
  emit();
}

export function getActiveReview() {
  return reviews.find((r) => r.id === activeId) ?? null;
}

export function createSessionReview(templateId: ReviewTemplateId, title?: string) {
  const next = createReviewFromTemplate(templateId, title);
  reviews = [next, ...reviews];
  activeId = next.id;
  emit();
  return next;
}

export function updateSessionReview(id: string, fn: (r: ClientReview) => ClientReview) {
  reviews = reviews.map((r) =>
    r.id === id ? { ...fn(r), updatedAt: new Date().toISOString() } : r,
  );
  emit();
}

export function toggleChecklistItem(reviewId: string, itemId: ReviewChecklistItemId) {
  updateSessionReview(reviewId, (r) => ({
    ...r,
    checklist: r.checklist.map((c) =>
      c.id === itemId ? { ...c, done: !c.done } : c,
    ),
  }));
}

export function setActionStatus(
  reviewId: string,
  actionId: string,
  status: ReviewActionStatus,
) {
  updateSessionReview(reviewId, (r) => ({
    ...r,
    actions: r.actions.map((a) => (a.id === actionId ? { ...a, status } : a)),
  }));
}

export function setReviewStatus(
  reviewId: string,
  status: ClientReview["status"],
) {
  updateSessionReview(reviewId, (r) => ({ ...r, status }));
}

export function archiveSessionReview(reviewId: string) {
  setReviewStatus(reviewId, "archived");
}
