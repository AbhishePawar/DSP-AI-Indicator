/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({ session: { accessToken: "tok" } }),
}));

const researchObjectMock = vi.fn();
const researchReportMock = vi.fn();
const researchExportMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  api: {
    researchObject: (...args: unknown[]) => researchObjectMock(...args),
    researchReport: (...args: unknown[]) => researchReportMock(...args),
    researchExport: (...args: unknown[]) => researchExportMock(...args),
  },
}));

import { buildDemoAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import { mapResearchView } from "@/lib/research/mapResearchView";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import { ExportSection } from "./WorkspaceSections";

const sampleResponse: AnalyseResponse = {
  ok: true,
  capability: "analyse",
  limitations: [],
  errors: [],
  api_version: "v1",
  platform_version: "1.0.0",
  pipeline_version: "1.0.0",
  correlation_id: "corr-1",
  analysis_id: "analysis-p112-1",
  audit_reference: "analysis-p112-1",
  provenance_persisted: true,
  payload: {
    ok: true,
    analysis_id: "analysis-p112-1",
    stage_summaries: [],
  },
};

function buildView() {
  const request = buildDemoAnalyseRequest("AAPL", {
    company: "Apple",
    exchange: "NASDAQ",
  });
  return {
    view: mapResearchView(sampleResponse, request, "2026-07-28T12:00:00.000Z"),
    request,
  };
}

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

let createObjectURLSpy: ReturnType<typeof vi.fn>;
let revokeObjectURLSpy: ReturnType<typeof vi.fn>;

let anchorClickSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  researchObjectMock.mockReset();
  researchReportMock.mockReset();
  researchExportMock.mockReset();
  createObjectURLSpy = vi.fn(() => "blob:mock-url");
  revokeObjectURLSpy = vi.fn();
  vi.stubGlobal("URL", {
    ...URL,
    createObjectURL: createObjectURLSpy,
    revokeObjectURL: revokeObjectURLSpy,
  });
  // jsdom doesn't support the `download` attribute's no-navigate semantics.
  anchorClickSpy = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(() => {});
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  anchorClickSpy.mockRestore();
});

describe("ExportSection — institutional DOCX/PPTX export", () => {
  it("disables Word/PowerPoint export until an analysis has been run", () => {
    const { view } = buildView();
    wrap(<ExportSection view={view} analyseRequest={null} analyseResponse={null} />);
    expect(
      screen.getByRole("button", { name: "Export Word (.docx)" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Export PowerPoint (.pptx)" }),
    ).toBeDisabled();
  });

  it("runs research object → report → export pipeline and downloads the file", async () => {
    researchObjectMock.mockResolvedValue({
      ok: true,
      research_object: { symbol: "AAPL" },
    });
    researchReportMock.mockResolvedValue({
      ok: true,
      report: { symbol: "AAPL", sections: [] },
    });
    researchExportMock.mockResolvedValue({
      ok: true,
      export: {
        metadata: { filename: "aapl-research.docx", content_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" },
        content_base64: "UEs=",
      },
    });

    const { view, request } = buildView();
    wrap(
      <ExportSection
        view={view}
        analyseRequest={request}
        analyseResponse={sampleResponse}
      />,
    );

    screen.getByRole("button", { name: "Export Word (.docx)" }).click();

    await waitFor(() => expect(researchExportMock).toHaveBeenCalled());
    expect(researchObjectMock).toHaveBeenCalledWith(
      expect.objectContaining({
        symbol: "AAPL",
        analysis_id: "analysis-p112-1",
      }),
      expect.anything(),
    );
    expect(researchReportMock).toHaveBeenCalledWith(
      {
        research_object: { symbol: "AAPL" },
        analysis_id: "analysis-p112-1",
      },
      expect.anything(),
    );
    expect(researchExportMock).toHaveBeenCalledWith(
      {
        report: { symbol: "AAPL", sections: [] },
        analysis_id: "analysis-p112-1",
        format: "docx",
      },
      expect.anything(),
    );
    await waitFor(() => expect(createObjectURLSpy).toHaveBeenCalled());
    expect(await screen.findByText("Word export downloaded.")).toBeTruthy();
  });

  it("surfaces a friendly error when export fails", async () => {
    researchObjectMock.mockResolvedValue({
      ok: false,
      message: "Data unavailable.",
    });
    const { view, request } = buildView();
    wrap(
      <ExportSection
        view={view}
        analyseRequest={request}
        analyseResponse={sampleResponse}
      />,
    );
    screen.getByRole("button", { name: "Export PowerPoint (.pptx)" }).click();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Data unavailable.",
    );
  });
});
