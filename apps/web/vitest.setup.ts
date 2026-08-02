import "@testing-library/jest-dom/vitest";
import { expect } from "vitest";
import * as axeMatchers from "vitest-axe/matchers";

/** EPIC-010 / GA-003 — axe matchers for accessibility automation. */
expect.extend(axeMatchers);

/** EPIC-F011 — jsdom matchMedia polyfill for responsive hooks. */
if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

/** EPIC-F011 — ResizeObserver polyfill for Radix layout measurements in jsdom. */
if (typeof window !== "undefined" && typeof window.ResizeObserver !== "function") {
  class ResizeObserverStub {
    observe() {
      return undefined;
    }
    unobserve() {
      return undefined;
    }
    disconnect() {
      return undefined;
    }
  }
  Object.defineProperty(window, "ResizeObserver", {
    writable: true,
    configurable: true,
    value: ResizeObserverStub,
  });
}
