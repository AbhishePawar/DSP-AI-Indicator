/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { GlobalErrorBoundary } from "@/components/reliability/GlobalErrorBoundary";
import { logger } from "@/lib/observability/logger";

function Boom(): never {
  throw new Error("render boom");
}

describe("GlobalErrorBoundary", () => {
  it("renders fallback when a child throws", () => {
    logger._resetForTests();
    render(
      <GlobalErrorBoundary>
        <Boom />
      </GlobalErrorBoundary>,
    );
    expect(screen.getByText(/Something went wrong/i)).toBeTruthy();
    expect(logger.getSessionErrors().length).toBeGreaterThan(0);
  });
});
