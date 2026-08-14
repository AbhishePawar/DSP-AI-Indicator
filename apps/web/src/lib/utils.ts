import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** shadcn-compatible className merger (EPIC-F001). */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
