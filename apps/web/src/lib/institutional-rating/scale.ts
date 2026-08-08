/**
 * ARCH-002 — Display-scale helpers.
 * Remap existing numeric stage scores to /10 and letter grades.
 * Not a scoring engine.
 */

export function isUnavailableDisplay(value: string | null | undefined): boolean {
  if (value == null) return true;
  const v = value.trim().toLowerCase();
  return (
    v === "" ||
    v === "unavailable" ||
    v === "data unavailable." ||
    v === "—" ||
    v === "n/a"
  );
}

/** Parse existing score text → 0–100 scale (handles 0–1 fractions). */
export function parseExistingScoreTo100(scoreText: string): number | null {
  if (isUnavailableDisplay(scoreText)) return null;
  const cleaned = scoreText.replace(/%/g, "").trim();
  let n = Number(cleaned);
  if (!Number.isFinite(n)) return null;
  if (n >= 0 && n <= 1) n = n * 100;
  return n;
}

export function letterGradeFromExistingScore(scoreText: string): string {
  const n = parseExistingScoreTo100(scoreText);
  if (n == null) {
    if (isUnavailableDisplay(scoreText)) return "Unavailable";
    return scoreText;
  }
  if (n >= 90) return "A+";
  if (n >= 80) return "A";
  if (n >= 70) return "B+";
  if (n >= 60) return "B";
  if (n >= 50) return "C";
  if (n >= 40) return "D";
  return "F";
}

/** Existing 0–100 (or 0–1) score → display "/10" with one decimal. */
export function scoreOutOf10FromExisting(scoreText: string): string {
  const n = parseExistingScoreTo100(scoreText);
  if (n == null) return "Unavailable";
  return `${(n / 10).toFixed(1)}/10`;
}

export function confidenceDisplay(confidenceText: string): string {
  if (isUnavailableDisplay(confidenceText)) return "Unavailable";
  if (confidenceText.includes("%")) return confidenceText;
  const n = Number(confidenceText.replace(/%/g, "").trim());
  if (!Number.isFinite(n)) return confidenceText;
  if (n >= 0 && n <= 1) return `${Math.round(n * 100)}%`;
  if (n > 1 && n <= 100) return `${Math.round(n)}%`;
  return confidenceText;
}

export function starsFromGrade(grade: string): number {
  switch (grade) {
    case "A+":
      return 5;
    case "A":
      return 5;
    case "B+":
      return 4;
    case "B":
      return 4;
    case "C":
      return 3;
    case "D":
      return 2;
    case "F":
      return 1;
    default:
      return 0;
  }
}

export function averageGradeFromExisting(grades: string[]): string {
  const map: Record<string, number> = {
    "A+": 97,
    A: 90,
    "B+": 77,
    B: 70,
    C: 55,
    D: 45,
    F: 20,
  };
  const nums = grades
    .map((g) => map[g])
    .filter((n): n is number => typeof n === "number");
  if (nums.length === 0) return "Unavailable";
  const avg = nums.reduce((a, b) => a + b, 0) / nums.length;
  return letterGradeFromExistingScore(String(avg));
}

export function averageScoreOutOf10(scores: string[]): string {
  const nums = scores
    .map((s) => {
      if (isUnavailableDisplay(s)) return null;
      const m = s.replace("/10", "").trim();
      const n = Number(m);
      return Number.isFinite(n) ? n : null;
    })
    .filter((n): n is number => n != null);
  if (nums.length === 0) return "Unavailable";
  const avg = nums.reduce((a, b) => a + b, 0) / nums.length;
  return `${avg.toFixed(1)}/10`;
}
