/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthPermissionGate } from "@/components/auth/AuthPermissionGate";
import { useAuth } from "@/lib/auth/AuthProvider";

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AuthPermissionGate", () => {
  it("renders children when permission present", () => {
    vi.mocked(useAuth).mockReturnValue({
      session: { accessToken: "t" },
      user: {
        permissions: ["manage_users"],
        roles: ["administrator"],
        role: "administrator",
      },
    } as ReturnType<typeof useAuth>);

    render(
      <AuthPermissionGate permission="manage_users">
        <span>Allowed</span>
      </AuthPermissionGate>,
    );
    expect(screen.getByText("Allowed")).toBeInTheDocument();
  });

  it("renders fallback when permission missing", () => {
    vi.mocked(useAuth).mockReturnValue({
      session: { accessToken: "t" },
      user: {
        permissions: ["read_research"],
        roles: ["read_only"],
        role: "read_only",
      },
    } as ReturnType<typeof useAuth>);

    render(
      <AuthPermissionGate
        permission="manage_users"
        fallback={<span>Denied</span>}
      >
        <span>Secret</span>
      </AuthPermissionGate>,
    );
    expect(screen.getByText("Denied")).toBeInTheDocument();
    expect(screen.queryByText("Secret")).not.toBeInTheDocument();
  });
});
