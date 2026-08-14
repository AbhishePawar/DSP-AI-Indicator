/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { usePortfolioIntelPrefsStore } from "@/lib/portfolio-intelligence";
import { BenchmarkSelector } from "./BenchmarkSelector";

describe("BenchmarkSelector", () => {
  beforeEach(() => {
    cleanup();
    usePortfolioIntelPrefsStore.setState({ benchmarkSymbol: null });
  });

  it("shows an honest 'no benchmark' state by default", () => {
    render(<BenchmarkSelector />);
    expect(screen.getByText(/select a benchmark to compute/i)).toBeTruthy();
  });

  it("reflects the selected benchmark from the store", () => {
    usePortfolioIntelPrefsStore.setState({ benchmarkSymbol: "SPY" });
    render(<BenchmarkSelector />);
    expect(
      screen.getByText(/beta\/alpha\/treynor\/tracking error\/information ratio computed vs\. spy/i),
    ).toBeTruthy();
  });

  it("clears the benchmark via the store setter (normalizes case/whitespace)", () => {
    usePortfolioIntelPrefsStore.getState().setBenchmarkSymbol(" qqq ");
    expect(usePortfolioIntelPrefsStore.getState().benchmarkSymbol).toBe("QQQ");

    usePortfolioIntelPrefsStore.getState().setBenchmarkSymbol(null);
    expect(usePortfolioIntelPrefsStore.getState().benchmarkSymbol).toBeNull();
  });

  it("applying a custom symbol updates the store", () => {
    usePortfolioIntelPrefsStore.setState({ benchmarkSymbol: "VTI" });
    render(<BenchmarkSelector />);
    const input = screen.getByLabelText(/custom benchmark symbol/i) as HTMLInputElement;
    expect(input.value).toBe("VTI");
    fireEvent.change(input, { target: { value: "VOO" } });
    fireEvent.submit(input.closest("form") as HTMLFormElement);
    expect(usePortfolioIntelPrefsStore.getState().benchmarkSymbol).toBe("VOO");
  });
});
