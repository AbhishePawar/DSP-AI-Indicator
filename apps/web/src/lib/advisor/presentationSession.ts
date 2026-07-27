/**
 * In-memory session store for advisor presentations (no persistence).
 */

import type { AdvisorPresentation, PresentationTemplateId } from "./presentationTypes";
import {
  clonePresentation,
  createPresentationFromTemplate,
  seedPresentations,
} from "./presentationModels";

let presentations: AdvisorPresentation[] = seedPresentations.map((p) => ({
  ...p,
  sections: p.sections.map((s) => ({ ...s })),
  envelopeIds: [...p.envelopeIds],
}));
let activeId: string = presentations[0]?.id ?? "";
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

export function subscribePresentations(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getPresentationSnapshot() {
  return { presentations, activeId };
}

export function setActivePresentationId(id: string) {
  activeId = id;
  emit();
}

export function listSessionPresentations() {
  return presentations;
}

export function getActivePresentation() {
  return presentations.find((p) => p.id === activeId) ?? null;
}

export function createSessionPresentation(templateId: PresentationTemplateId, title?: string) {
  const next = createPresentationFromTemplate(templateId, title);
  presentations = [next, ...presentations];
  activeId = next.id;
  emit();
  return next;
}

export function duplicateSessionPresentation(id: string) {
  const src = presentations.find((p) => p.id === id);
  if (!src) return null;
  const copy = clonePresentation(src);
  presentations = [copy, ...presentations];
  activeId = copy.id;
  emit();
  return copy;
}

export function renameSessionPresentation(id: string, title: string) {
  presentations = presentations.map((p) =>
    p.id === id
      ? { ...p, title: title.trim() || p.title, updatedAt: new Date().toISOString() }
      : p,
  );
  emit();
}

export function archiveSessionPresentation(id: string) {
  presentations = presentations.map((p) =>
    p.id === id ? { ...p, lifecycle: "archived", updatedAt: new Date().toISOString() } : p,
  );
  emit();
}

export function updateSessionPresentation(
  id: string,
  fn: (p: AdvisorPresentation) => AdvisorPresentation,
) {
  presentations = presentations.map((p) =>
    p.id === id ? { ...fn(p), updatedAt: new Date().toISOString() } : p,
  );
  emit();
}
