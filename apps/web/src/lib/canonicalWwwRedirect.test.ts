import { describe, expect, it } from "vitest";

import { oauthRedirectUri } from "@/components/auth/authValidation";

import {
  CANONICAL_PRODUCTION_ORIGIN,
  canonicalWwwRedirectLocation,
  productionWwwRedirect,
  WWW_PRODUCTION_HOST,
} from "./canonicalWwwRedirect";

function headers(init: Record<string, string>) {
  const normalized = Object.fromEntries(
    Object.entries(init).map(([key, value]) => [key.toLowerCase(), value]),
  );
  return {
    get(name: string): string | null {
      return normalized[name.toLowerCase()] ?? null;
    },
  };
}

describe("production www canonical redirect", () => {
  it("permanently redirects exact www host to the hardcoded canonical origin", () => {
    const result = productionWwwRedirect(
      headers({ host: WWW_PRODUCTION_HOST }),
      "/",
    );
    expect(result).toEqual({
      status: 301,
      location: "https://dspaiindicator.com/",
    });
  });

  it("preserves pathname on the canonical origin", () => {
    expect(
      canonicalWwwRedirectLocation(WWW_PRODUCTION_HOST, "/login", ""),
    ).toBe("https://dspaiindicator.com/login");
  });

  it("preserves query string", () => {
    const result = productionWwwRedirect(
      headers({ host: "www.dspaiindicator.com" }),
      "/login",
      "?test=1",
    );
    expect(result?.location).toBe("https://dspaiindicator.com/login?test=1");
  });

  it("redirects the root path", () => {
    expect(
      productionWwwRedirect(headers({ host: WWW_PRODUCTION_HOST }), "/"),
    ).toEqual({
      status: 301,
      location: "https://dspaiindicator.com/",
    });
  });

  it("redirects /login so www never serves the login page", () => {
    const result = productionWwwRedirect(
      headers({ host: WWW_PRODUCTION_HOST }),
      "/login",
    );
    expect(result?.status).toBe(301);
    expect(result?.location).toBe("https://dspaiindicator.com/login");
    expect(result?.location).not.toContain("www.dspaiindicator.com");
  });

  it("redirects /register", () => {
    expect(
      productionWwwRedirect(headers({ host: WWW_PRODUCTION_HOST }), "/register")
        ?.location,
    ).toBe("https://dspaiindicator.com/register");
  });

  it("does not redirect the canonical apex host", () => {
    expect(
      productionWwwRedirect(headers({ host: "dspaiindicator.com" }), "/login"),
    ).toBeNull();
  });

  it("does not redirect localhost", () => {
    expect(
      productionWwwRedirect(headers({ host: "localhost:3000" }), "/login"),
    ).toBeNull();
    expect(
      productionWwwRedirect(
        headers({
          host: "localhost:3000",
          "x-forwarded-host": WWW_PRODUCTION_HOST,
        }),
        "/login",
      ),
    ).toBeNull();
  });

  it("does not redirect 127.0.0.1", () => {
    expect(
      productionWwwRedirect(headers({ host: "127.0.0.1:3000" }), "/"),
    ).toBeNull();
  });

  it("does not redirect Cloud Run *.run.app hosts", () => {
    expect(
      productionWwwRedirect(
        headers({
          host: "dsp-ai-indicator-web-6uxsluxowq-el.a.run.app",
        }),
        "/",
      ),
    ).toBeNull();
  });

  it("does not redirect arbitrary or non-production hosts", () => {
    for (const host of [
      "evil.example",
      "staging.dspaiindicator.com",
      "www.dspaindicator.com",
      "dspaindicator.com",
    ]) {
      expect(
        productionWwwRedirect(headers({ host }), "/login"),
        host,
      ).toBeNull();
    }
  });

  it("does not create an open redirect from forwarded or host values", () => {
    const result = productionWwwRedirect(
      headers({
        host: WWW_PRODUCTION_HOST,
        "x-forwarded-host": "evil.example",
      }),
      "/login?next=https://evil.example",
    );
    expect(result?.location).toBe(
      "https://dspaiindicator.com/login?next=https://evil.example",
    );
    expect(result?.location.startsWith(CANONICAL_PRODUCTION_ORIGIN)).toBe(true);
  });

  it("uses X-Forwarded-Host only to detect exact production www behind Cloud Run", () => {
    const result = productionWwwRedirect(
      headers({
        host: "dsp-ai-indicator-web-6uxsluxowq-el.a.run.app",
        "x-forwarded-host": WWW_PRODUCTION_HOST,
      }),
      "/register?x=1",
    );
    expect(result).toEqual({
      status: 301,
      location: "https://dspaiindicator.com/register?x=1",
    });
  });

  it("never redirects to a host taken from request headers", () => {
    const location = canonicalWwwRedirectLocation(
      WWW_PRODUCTION_HOST,
      "/oauth/callback",
      "?code=1",
    );
    expect(location).toBe(
      "https://dspaiindicator.com/oauth/callback?code=1",
    );
    expect(location).not.toContain("://www.");
  });
});

describe("production OAuth callback after www canonicalization", () => {
  it("keeps the exact canonical Google callback", () => {
    expect(oauthRedirectUri(CANONICAL_PRODUCTION_ORIGIN)).toBe(
      "https://dspaiindicator.com/oauth/callback",
    );
    expect(oauthRedirectUri(CANONICAL_PRODUCTION_ORIGIN)).not.toBe(
      "https://www.dspaiindicator.com/oauth/callback",
    );
  });

  it("canonicalizes www /login before OAuth so production never starts Google on www", () => {
    const loginRedirect = productionWwwRedirect(
      headers({ host: WWW_PRODUCTION_HOST }),
      "/login",
    );
    expect(loginRedirect?.location).toBe("https://dspaiindicator.com/login");
    expect(oauthRedirectUri(CANONICAL_PRODUCTION_ORIGIN)).toBe(
      "https://dspaiindicator.com/oauth/callback",
    );
    expect(oauthRedirectUri(CANONICAL_PRODUCTION_ORIGIN)).not.toContain(
      "www.dspaiindicator.com",
    );
  });
});
