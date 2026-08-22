/**
 * @vitest-environment jsdom
 *
 * Public /register — Create account + Continue with Google only.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ThemeProvider } from "@/providers/ThemeProvider";

const registerMobileRequestMock = vi.fn();
const registerMobileCompleteMock = vi.fn();
const oauthBeginMock = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/register",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

vi.mock("@/lib/auth/useAuthProviders", () => ({
  useAuthProviders: () => ({
    loading: false,
    oauthAvailable: [{ provider: "GOOGLE", available: true, status: "available" }],
    oauthComingSoon: [],
    smsStatus: "available",
    smsMessage: null,
    magicLinkStatus: "coming_soon",
    magicLinkMessage: null,
    webauthnAvailable: false,
    webauthnMessage: null,
  }),
}));

vi.mock("@/lib/api/enterpriseAuth", () => ({
  enterpriseAuthApi: {
    registerMobileRequest: (...args: unknown[]) => registerMobileRequestMock(...args),
    registerMobileComplete: (...args: unknown[]) => registerMobileCompleteMock(...args),
    oauthBegin: (...args: unknown[]) => oauthBeginMock(...args),
  },
}));

afterEach(() => cleanup());

describe("Register page", () => {
  beforeEach(() => {
    registerMobileRequestMock.mockReset();
    registerMobileCompleteMock.mockReset();
    oauthBeginMock.mockReset();
  });

  it("shows only Create account and Continue with Google", async () => {
    const { default: RegisterPage } = await import("@/app/(auth)/register/page");
    render(
      <ThemeProvider>
        <RegisterPage />
      </ThemeProvider>,
    );
    expect(screen.getByRole("button", { name: /^create account$/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /continue with google/i })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /request access/i })).toBeNull();
    expect(screen.queryByText(/enterprise onboarding/i)).toBeNull();
    expect(screen.queryByText(/username \(optional\)/i)).toBeNull();
    expect(screen.queryByText(/demo mode/i)).toBeNull();
  });

  it("suggests username from mobile and keeps it editable", async () => {
    const { default: RegisterPage } = await import("@/app/(auth)/register/page");
    render(
      <ThemeProvider>
        <RegisterPage />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: /^create account$/i }));
    expect(document.getElementById("reg-name")).toBeTruthy();
    expect(document.getElementById("reg-mobile")).toBeTruthy();
    expect(document.getElementById("reg-username")).toBeTruthy();
    expect(document.getElementById("reg-email")).toBeTruthy();
    expect(document.getElementById("reg-password")).toBeTruthy();
    expect(document.getElementById("reg-confirm")).toBeTruthy();

    fireEvent.change(document.getElementById("reg-mobile")!, {
      target: { value: "9826912345" },
    });
    expect((document.getElementById("reg-username") as HTMLInputElement).value).toBe(
      "9826912345",
    );
    fireEvent.change(document.getElementById("reg-username")!, {
      target: { value: "abhishek" },
    });
    fireEvent.change(document.getElementById("reg-mobile")!, {
      target: { value: "9826912399" },
    });
    expect((document.getElementById("reg-username") as HTMLInputElement).value).toBe(
      "abhishek",
    );
  });

  it("requests mobile OTP then completes combined registration", async () => {
    registerMobileRequestMock.mockResolvedValue({
      ok: true,
      result: { challenge_id: "ch-reg", sms: { debug_code: "123456" } },
    });
    registerMobileCompleteMock.mockResolvedValue({
      ok: true,
      result: { message: "Account created." },
    });
    const { default: RegisterPage } = await import("@/app/(auth)/register/page");
    render(
      <ThemeProvider>
        <RegisterPage />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: /^create account$/i }));
    fireEvent.change(document.getElementById("reg-name")!, {
      target: { value: "Abhishek" },
    });
    fireEvent.change(document.getElementById("reg-mobile")!, {
      target: { value: "9826912345" },
    });
    fireEvent.change(document.getElementById("reg-username")!, {
      target: { value: "abhishek" },
    });
    fireEvent.change(document.getElementById("reg-email")!, {
      target: { value: "abhishek@gmail.com" },
    });
    fireEvent.change(document.getElementById("reg-password")!, {
      target: { value: "StrongPass1!" },
    });
    fireEvent.change(document.getElementById("reg-confirm")!, {
      target: { value: "StrongPass1!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /verify mobile/i }));
    await waitFor(() => expect(registerMobileRequestMock).toHaveBeenCalled());
    expect(registerMobileRequestMock.mock.calls[0][0]).toBe("+919826912345");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /^create account$/i })).toBeTruthy(),
    );
  });
});
