/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";

const push = vi.fn();
const searchSecuritiesMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    session: { accessToken: "tok" },
  }),
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    searchSecurities: (...args: unknown[]) => searchSecuritiesMock(...args),
  },
}));

import { CompanyResearchBar } from "@/components/securities/CompanyResearchBar";
import type { SecurityListingView } from "@/lib/securities/identity";

const infy: SecurityListingView = {
  company_name: "Infosys Limited",
  ticker: "INFY",
  isin: "INE009A01021",
  exchange: "NSE",
  mic: "XNSE",
  security_type: "equity",
  eligibility: true,
};

const tcs: SecurityListingView = {
  company_name: "Tata Consultancy Services Limited",
  ticker: "TCS",
  isin: "INE467B01029",
  exchange: "NSE",
  mic: "XNSE",
  security_type: "equity",
  eligibility: true,
};

describe("CompanyResearchBar", () => {
  beforeEach(() => {
    cleanup();
    push.mockReset();
    searchSecuritiesMock.mockReset();
    searchSecuritiesMock.mockResolvedValue({
      ok: true,
      status: "MATCHES",
      query: "INFY",
      results: [infy],
    });
  });

  it("renders the primary Company Research heading and labeled input", () => {
    render(<CompanyResearchBar />);
    expect(
      screen.getByRole("heading", { name: "Company Research" }),
    ).toBeTruthy();
    expect(screen.getByLabelText("Company search")).toBeTruthy();
  });

  it("does not fire a search for empty input", async () => {
    render(<CompanyResearchBar />);
    fireEvent.change(screen.getByLabelText("Company search"), {
      target: { value: "   " },
    });
    await new Promise((resolve) => setTimeout(resolve, 250));
    expect(searchSecuritiesMock).not.toHaveBeenCalled();
  });

  it("debounces input, shows identity fields, and selects into analysis", async () => {
    const onSelect = vi.fn();
    render(<CompanyResearchBar onSelect={onSelect} />);
    const input = screen.getByLabelText("Company search");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "INFY" } });
    await waitFor(() => expect(searchSecuritiesMock).toHaveBeenCalled());
    expect(searchSecuritiesMock.mock.calls[0]?.[0]).toBe("INFY");
    expect(searchSecuritiesMock.mock.calls[0]?.[1]).toMatchObject({
      token: "tok",
      limit: 8,
    });
    expect(await screen.findByText(/INE009A01021/)).toBeTruthy();
    expect(screen.getByText(/XNSE/)).toBeTruthy();
    fireEvent.click(screen.getByRole("option"));
    expect(onSelect).toHaveBeenCalledWith(infy);
  });

  it("shows a no-result state without inventing a security", async () => {
    searchSecuritiesMock.mockResolvedValue({
      ok: true,
      status: "UNKNOWN",
      query: "ZZZZZZ",
      results: [],
    });
    render(<CompanyResearchBar />);
    const input = screen.getByLabelText("Company search");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "ZZZZZZ" } });
    expect(
      await screen.findByText(/does not invent a security/i),
    ).toBeTruthy();
  });

  it("shows unsupported and recoverable error states", async () => {
    searchSecuritiesMock.mockResolvedValue({
      ok: true,
      status: "UNSUPPORTED",
      query: "NIFTYBEES",
      results: [],
    });
    const { unmount } = render(<CompanyResearchBar />);
    const input = screen.getByLabelText("Company search");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "NIFTYBEES" } });
    expect(await screen.findByText(/UNSUPPORTED/)).toBeTruthy();
    unmount();

    searchSecuritiesMock.mockRejectedValue(new Error("network"));
    render(<CompanyResearchBar />);
    const retry = screen.getByLabelText("Company search");
    fireEvent.focus(retry);
    fireEvent.change(retry, { target: { value: "WIPRO" } });
    expect(await screen.findByRole("alert")).toHaveTextContent(/Search failed/);
  });

  it("lists ambiguous candidates with identity instead of guessing", async () => {
    searchSecuritiesMock.mockResolvedValue({
      ok: true,
      status: "MATCHES",
      query: "HDFC",
      results: [infy, tcs],
    });
    render(<CompanyResearchBar />);
    const input = screen.getByLabelText("Company search");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "HDFC" } });
    const options = await screen.findAllByRole("option");
    expect(options).toHaveLength(2);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
  });

  it("navigates through the existing analysis identity path when no onSelect is given", async () => {
    render(<CompanyResearchBar />);
    const input = screen.getByLabelText("Company search");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "INFY" } });
    fireEvent.click(await screen.findByRole("option"));
    expect(push).toHaveBeenCalledWith(
      "/analysis?symbol=INFY&exchange=NSE&isin=INE009A01021&mic=XNSE",
    );
  });

  it("does not hard-code a ticker universe in the component", () => {
    const source = readFileSync(
      path.resolve(__dirname, "CompanyResearchBar.tsx"),
      "utf8",
    );
    for (const ticker of [
      "TCS",
      "INFY",
      "RELIANCE",
      "WIPRO",
      "20MICRONS",
      "21STCENMGM",
    ]) {
      expect(source).not.toContain(`"${ticker}"`);
    }
  });
});
