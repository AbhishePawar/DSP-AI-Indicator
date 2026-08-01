import type { Metadata } from "next";
import { Fraunces, Sora } from "next/font/google";

import { AppLayout } from "@/components/layout/AppLayout";
import { GlobalErrorBoundary } from "@/components/reliability/GlobalErrorBoundary";
import { OfflineBanner } from "@/components/reliability/OfflineBanner";
import { SessionRecoveryProvider } from "@/components/reliability/OfflineBanner";
import { AuthProvider } from "@/lib/auth/AuthProvider";
import { env } from "@/lib/env";
import { PortfolioProvider } from "@/lib/portfolio/PortfolioProvider";
import { MarketDataProvider } from "@/providers/MarketDataProvider";
import { AIProviderContextProvider } from "@/providers/AIProviderContext";
import { NotificationProvider } from "@/providers/NotificationProvider";
import { PersistenceProvider } from "@/providers/PersistenceProvider";
import { QueryProvider } from "@/providers/QueryProvider";
import { ThemeProvider } from "@/providers/ThemeProvider";
import { AppearanceApplicator } from "@/components/settings-workspace/AppearanceApplicator";

import "./globals.css";

const marketConfig = {
  cacheTtlMs: env.marketCacheTtlMs,
  autoRefreshMs: env.marketRefreshMs,
} as const;

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const body = Sora({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: env.appName,
  description: "DSP AI Indicator web client — backend-driven analysis only",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${display.variable} ${body.variable} antialiased`}>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-[var(--accent)] focus:px-3 focus:py-2 focus:text-[var(--accent-fg)]"
        >
          Skip to main content
        </a>
        <ThemeProvider>
          <AppearanceApplicator />
          <QueryProvider>
            <MarketDataProvider config={marketConfig}>
              <AIProviderContextProvider>
                <NotificationProvider>
                  <AuthProvider>
                    <PersistenceProvider>
                      <PortfolioProvider>
                        <SessionRecoveryProvider>
                          <GlobalErrorBoundary>
                            <OfflineBanner />
                            <AppLayout>{children}</AppLayout>
                          </GlobalErrorBoundary>
                        </SessionRecoveryProvider>
                      </PortfolioProvider>
                    </PersistenceProvider>
                  </AuthProvider>
                </NotificationProvider>
              </AIProviderContextProvider>
            </MarketDataProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

