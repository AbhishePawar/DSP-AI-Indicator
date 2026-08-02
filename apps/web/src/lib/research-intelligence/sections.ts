/** Research Intelligence workspace sections (EPIC-011B). */

export const RI_WINDOWS = [3, 6, 12, 24, 36] as const;
export type RiWindowMonths = (typeof RI_WINDOWS)[number];

export const RI_SECTIONS = [
  {
    id: "performance",
    label: "Performance",
    description: "Overall research accuracy and coverage metrics",
  },
  {
    id: "timeline",
    label: "Timeline",
    description: "Immutable historical research snapshots",
  },
  {
    id: "calibration",
    label: "Calibration",
    description: "Confidence bucket accuracy and drift",
  },
  {
    id: "insights",
    label: "Intelligence",
    description: "Best/worst performers, gaps, and sector views",
  },
] as const;

export type RiSectionId = (typeof RI_SECTIONS)[number]["id"];

export function isRiSectionId(value: string | null | undefined): value is RiSectionId {
  return RI_SECTIONS.some((s) => s.id === value);
}

export function asRiSectionId(value: string | null | undefined): RiSectionId {
  return isRiSectionId(value) ? value : "performance";
}

export function asRiWindow(value: string | null | undefined): RiWindowMonths {
  const n = Number(value);
  return (RI_WINDOWS as readonly number[]).includes(n)
    ? (n as RiWindowMonths)
    : 12;
}
