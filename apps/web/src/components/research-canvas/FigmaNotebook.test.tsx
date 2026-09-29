/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";

const canvasesMock = vi.fn();
const saveMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  api: {
    workspaceCanvases: (...args: unknown[]) => canvasesMock(...args),
    workspaceCanvasSave: (...args: unknown[]) => saveMock(...args),
  },
}));

import { FigmaNotebook } from "./FigmaNotebook";

function wrap(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("FigmaNotebook (Research Canvas)", () => {
  beforeEach(() => {
    cleanup();
    canvasesMock.mockReset();
    saveMock.mockReset();
  });

  it("renders real canvas blocks from the workspace API with the Figma outline panel", async () => {
    canvasesMock.mockResolvedValue({
      ok: true,
      count: 1,
      items: [
        {
          canvas_id: "c1",
          title: "Thesis draft",
          updated_at: "2026-09-01T10:00:00.000Z",
          blocks: [
            { id: "b1", type: "heading", content: "Moat" },
            { id: "b2", type: "text", content: "Pricing power holds." },
          ],
        },
      ],
    });
    wrap(<FigmaNotebook />);
    expect(await screen.findByDisplayValue("Thesis draft")).toBeTruthy();
    expect(screen.getByDisplayValue("Moat")).toBeTruthy();
    expect(screen.getByLabelText("Canvas outline")).toBeTruthy();
    expect(screen.getByText("✓ Saved")).toBeTruthy();
    expect(screen.getByRole("button", { name: "+ metric" })).toBeTruthy();
  });

  it("starts empty (no Figma demo thesis) and saves through the API", async () => {
    canvasesMock.mockResolvedValue({ ok: true, count: 0, items: [] });
    saveMock.mockResolvedValue({
      item: {
        canvas_id: "c9",
        title: "Untitled canvas",
        updated_at: "2026-09-01T10:00:00.000Z",
        blocks: [{ id: "s1", type: "text", content: "" }],
      },
    });
    wrap(<FigmaNotebook />);
    expect(await screen.findByText(/No blocks yet/i)).toBeTruthy();
    expect(screen.getByText("New canvas")).toBeTruthy();
    expect(screen.queryByText(/Tata Consultancy/i)).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "+ text" }));
    expect(screen.getByText("Unsaved changes")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Save canvas/i }));
    await waitFor(() => expect(saveMock).toHaveBeenCalledTimes(1));
    const payload = saveMock.mock.calls[0][0] as { blocks: Array<{ type: string }> };
    expect(payload.blocks.map((b) => b.type)).toEqual(["text"]);
    expect(await screen.findByText("✓ Saved")).toBeTruthy();
  });

  it("shows an honest error state when the canvas API is unavailable", async () => {
    canvasesMock.mockRejectedValue(new Error("boom"));
    wrap(<FigmaNotebook />);
    expect(await screen.findByText("Research canvas unavailable")).toBeTruthy();
  });
});
