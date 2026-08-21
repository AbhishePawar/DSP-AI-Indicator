"""Transactional email templates (plaintext + HTML) for the auth platform.

Pure rendering functions — no I/O, no provider coupling. Each function
returns ``(subject, text_body, html_body)`` so callers can pass the result
straight to :class:`auth.email_delivery.EmailProviderPort`. The ``TOKEN=``
marker line is preserved in the plaintext body for :class:`ConsoleEmailAdapter`
compatibility (local/dev debugging only).
"""

from __future__ import annotations

import html as _html

__all__ = [
    "render_magic_link_email",
    "render_email_verification_email",
    "render_password_reset_email",
    "render_invitation_email",
]

_BRAND = "DSP AI Indicator"


def _wrap_html(*, preheader: str, heading: str, body_html: str, cta_url: str, cta_label: str) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{_html.escape(heading)}</title>
  </head>
  <body style="margin:0;padding:0;background-color:#0b0f19;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
    <span style="display:none;max-height:0;overflow:hidden;">{_html.escape(preheader)}</span>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0b0f19;padding:32px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background-color:#111827;border-radius:12px;overflow:hidden;">
            <tr>
              <td style="padding:28px 32px 8px 32px;">
                <span style="color:#e5e7eb;font-size:14px;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;">{_BRAND}</span>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 32px 0 32px;">
                <h1 style="color:#f9fafb;font-size:20px;margin:0 0 12px 0;">{_html.escape(heading)}</h1>
                <div style="color:#9ca3af;font-size:14px;line-height:1.6;">{body_html}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 32px;">
                <a href="{_html.escape(cta_url)}" style="display:inline-block;background-color:#4f46e5;color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;padding:12px 20px;border-radius:8px;">{_html.escape(cta_label)}</a>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 28px 32px;">
                <p style="color:#6b7280;font-size:12px;line-height:1.5;word-break:break-all;">
                  If the button does not work, copy and paste this link into your browser:<br />
                  <a href="{_html.escape(cta_url)}" style="color:#818cf8;">{_html.escape(cta_url)}</a>
                </p>
              </td>
            </tr>
          </table>
          <p style="color:#4b5563;font-size:11px;margin-top:16px;">
            You received this email because it was requested for a {_BRAND} account.
            If this was not you, no action is required.
          </p>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def render_magic_link_email(*, link_url: str, token: str, expires_minutes: int) -> tuple[str, str, str]:
    subject = f"Your {_BRAND} sign-in link"
    text = (
        f"Sign in to {_BRAND}\n\n"
        f"Click the link below to sign in. It expires in {expires_minutes} minutes "
        "and can only be used once.\n\n"
        f"{link_url}\n\n"
        f"TOKEN={token}\n\n"
        "If you did not request this, you can safely ignore this email."
    )
    html_body = (
        f"<p>Click the button below to sign in to {_html.escape(_BRAND)}. "
        f"This link expires in <strong>{expires_minutes} minutes</strong> and can only be used once.</p>"
        "<p>If you did not request this, you can safely ignore this email.</p>"
    )
    html = _wrap_html(
        preheader=f"Your secure sign-in link ({expires_minutes} min)",
        heading="Sign in to your account",
        body_html=html_body,
        cta_url=link_url,
        cta_label="Sign in",
    )
    return subject, text, html


def render_email_verification_email(
    *, link_url: str, token: str, expires_hours: int
) -> tuple[str, str, str]:
    subject = f"Verify your {_BRAND} email address"
    text = (
        f"Welcome to {_BRAND}\n\n"
        f"Please verify your email address. This link expires in {expires_hours} hours.\n\n"
        f"{link_url}\n\n"
        f"TOKEN={token}\n\n"
        "If you did not create this account, you can safely ignore this email."
    )
    html_body = (
        f"<p>Welcome to {_html.escape(_BRAND)}. Please confirm your email address to activate "
        f"your account. This link expires in <strong>{expires_hours} hours</strong>.</p>"
        "<p>If you did not create this account, you can safely ignore this email.</p>"
    )
    html = _wrap_html(
        preheader="Confirm your email address to activate your account",
        heading="Verify your email address",
        body_html=html_body,
        cta_url=link_url,
        cta_label="Verify email",
    )
    return subject, text, html


def render_password_reset_email(
    *, link_url: str, token: str, expires_minutes: int
) -> tuple[str, str, str]:
    subject = f"Reset your {_BRAND} password"
    text = (
        f"Reset your {_BRAND} password\n\n"
        f"This link expires in {expires_minutes} minutes and can only be used once.\n\n"
        f"{link_url}\n\n"
        f"TOKEN={token}\n\n"
        "If you did not request a password reset, you can safely ignore this email — "
        "your password will not be changed."
    )
    html_body = (
        f"<p>We received a request to reset your {_html.escape(_BRAND)} password. "
        f"This link expires in <strong>{expires_minutes} minutes</strong> and can only be used once.</p>"
        "<p>If you did not request a password reset, you can safely ignore this email — "
        "your password will not be changed.</p>"
    )
    html = _wrap_html(
        preheader="Reset your password — link expires shortly",
        heading="Reset your password",
        body_html=html_body,
        cta_url=link_url,
        cta_label="Reset password",
    )
    return subject, text, html


def render_invitation_email(
    *, link_url: str, token: str, org_name: str | None, role: str, expires_hours: int
) -> tuple[str, str, str]:
    org_line = f" to join {org_name}" if org_name else ""
    subject = f"You're invited to {_BRAND}"
    text = (
        f"You've been invited{org_line} on {_BRAND} as {role}.\n\n"
        f"This invitation expires in {expires_hours} hours.\n\n"
        f"{link_url}\n\n"
        f"TOKEN={token}\n"
    )
    html_body = (
        f"<p>You've been invited{_html.escape(org_line)} on {_html.escape(_BRAND)} "
        f"with the role <strong>{_html.escape(role)}</strong>.</p>"
        f"<p>This invitation expires in <strong>{expires_hours} hours</strong>.</p>"
    )
    html = _wrap_html(
        preheader=f"You've been invited{org_line}",
        heading="You're invited",
        body_html=html_body,
        cta_url=link_url,
        cta_label="Accept invitation",
    )
    return subject, text, html
