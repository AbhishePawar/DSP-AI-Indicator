/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ThemeProvider } from "@/providers/ThemeProvider";

const forgotPasswordMock = vi.fn();
const resetPasswordOtpMock = vi.fn();

vi.mock("@/lib/api/enterpriseAuth", () => ({
  enterpriseAuthApi: {
    forgotPassword: (...args: unknown[]) => forgotPasswordMock(...args),
    resetPasswordOtp: (...args: unknown[]) => resetPasswordOtpMock(...args),
  },
}));

afterEach(() => cleanup());

describe("Forgot password page", () => {
  beforeEach(() => {
    forgotPasswordMock.mockReset();
    resetPasswordOtpMock.mockReset();
  });

  it("requests OTP for username or mobile", async () => {
    forgotPasswordMock.mockResolvedValue({
      ok: true,
      result: { challenge_id: "ch-reset", sms: { debug_code: "654321" } },
    });
    const { default: ForgotPasswordPage } = await import(
      "@/app/(auth)/forgot-password/page"
    );
    render(
      <ThemeProvider>
        <ForgotPasswordPage />
      </ThemeProvider>,
    );
    expect(screen.getByLabelText(/username, email or mobile number/i)).toBeTruthy();
    expect(screen.queryByLabelText(/work email/i)).toBeNull();
    expect(screen.queryByText(/demo mode/i)).toBeNull();
    fireEvent.change(screen.getByLabelText(/username, email or mobile number/i), {
      target: { value: "abhishek" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send otp/i }));
    await waitFor(() => expect(forgotPasswordMock).toHaveBeenCalledWith("abhishek"));
  });
  it("supports email reset links without revealing whether the account exists", async () => {
    forgotPasswordMock.mockResolvedValue({
      ok: true,
      result: { ok: true, message: "If an account exists, a reset token was issued." },
    });
    const { default: ForgotPasswordPage } = await import(
      "@/app/(auth)/forgot-password/page"
    );
    render(
      <ThemeProvider>
        <ForgotPasswordPage />
      </ThemeProvider>,
    );
    fireEvent.change(screen.getByLabelText(/username, email or mobile number/i), {
      target: { value: "person@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));
    await waitFor(() =>
      expect(forgotPasswordMock).toHaveBeenCalledWith("person@example.com"),
    );
    expect(
      await screen.findByText(/if an account with that email exists/i),
    ).toBeTruthy();
  });

  it("does not claim email recovery is available when delivery is unconfigured", async () => {
    forgotPasswordMock.mockResolvedValue({
      ok: true,
      result: {
        ok: true,
        recovery_available: false,
        message: "Password recovery is temporarily unavailable. Contact support.",
      },
    });
    const { default: ForgotPasswordPage } = await import(
      "@/app/(auth)/forgot-password/page"
    );
    render(
      <ThemeProvider>
        <ForgotPasswordPage />
      </ThemeProvider>,
    );
    fireEvent.change(screen.getByLabelText(/username, email or mobile number/i), {
      target: { value: "person@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));
    expect(
      await screen.findByText(/email password recovery is not configured/i),
    ).toBeTruthy();
    expect(screen.queryByText(/a password reset link has been sent/i)).toBeNull();
  });


});
