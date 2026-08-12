/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

import { ProductionOpsPanel } from "@/components/ops-portal/ProductionOpsPanel";

vi.mock("@/lib/api/client", () => ({
  api: {
    opsDashboard: vi.fn(async () => ({
      ok: true,
      result: {
        version: {
          application_version: "1.0.0",
          git_sha: "abc123",
          environment: "test",
          release_channel: "ga-candidate",
        },
        health: {
          live: { status: "alive" },
          ready: { ready: true, status: "pass" },
          dependencies: {
            components: [
              {
                name: "platform",
                status: "pass",
                message: "ok",
              },
            ],
          },
        },
        metrics: {
          scrape_path: "/metrics",
          sample_series_count: 3,
          note: "Full exposition at GET /metrics",
        },
        observability: {
          opentelemetry: {
            available: false,
            message: "OpenTelemetry exporter unavailable.",
          },
        },
        backup: {
          available: false,
          message: "Backup provider unavailable.",
          note: "Use scripts/ops/backup_postgres.sh",
        },
      },
    })),
  },
}));

describe("ProductionOpsPanel", () => {
  beforeEach(() => {
    cleanup();
  });

  it("renders production ops health and version", async () => {
    render(<ProductionOpsPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("production-ops-panel")).toBeTruthy();
    });
    expect(screen.getByTestId("production-ops-panel").textContent).toMatch(
      /1\.0\.0/,
    );
    expect(screen.getByTestId("production-ops-panel").textContent).toMatch(
      /Backup provider unavailable/i,
    );
    expect(screen.getByTestId("production-ops-panel").textContent).toMatch(
      /platform/,
    );
  });
});
