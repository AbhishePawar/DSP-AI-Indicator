/**
 * @vitest-environment jsdom
 *
 * Public /register — Google OAuth only.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { ThemeProvider } from "@/providers/ThemeProvider";

const oauthBeginMock = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/register",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

vi.mock("@/lib/api/enterpriseAuth", () => ({
  enterpriseAuthApi: {
    oauthBegin: (...args: unknown[]) => oauthBeginMock(...args),
  },
}));

afterEach(() => cleanup());

describe("Register page", () => {
  beforeEach(() => {
    oauthBeginMock.mockReset();
  });

  it("shows only Google sign-up", async () => {
    const { default: RegisterPage } = await import("@/app/(auth)/register/page");
    render(
      <ThemeProvider>
        <RegisterPage />
      </ThemeProvider>,
    );

    expect(
      screen.getByRole("heading", {
        name: /create your dsp ai indicator account/i,
      }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /continue with google/i })).toBeTruthy();
    expect(
      screen.getByText(/google is the only available sign-up method/i),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: /sign in/i })).toBeTruthy();
    expect(screen.queryByLabelText(/full name/i)).toBeNull();
    expect(screen.queryByLabelText(/mobile number/i)).toBeNull();
    expect(screen.queryByLabelText(/username/i)).toBeNull();
    expect(screen.queryByLabelText(/password/i)).toBeNull();
    expect(screen.queryByRole("button", { name: /verify mobile/i })).toBeNull();
  });
});
