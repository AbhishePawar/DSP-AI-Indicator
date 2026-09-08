"use client";

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";

declare global {
  interface Window {
    dataLayer: unknown[];
    gtag: (...args: unknown[]) => void;
  }
}

/**
 * GoogleAnalytics — GA4 page-view tracker.
 * Only fires in production when NEXT_PUBLIC_GA_MEASUREMENT_ID is set.
 * Wrap in <Suspense> in layout because useSearchParams requires it.
 */
export function GoogleAnalytics() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    const measurementId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;
    if (!measurementId) return;

    // Bootstrap gtag once
    if (!window.dataLayer) {
      const script = document.createElement("script");
      script.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
      script.async = true;
      document.head.appendChild(script);

      window.dataLayer = [];
      window.gtag = function (...args: unknown[]) {
        window.dataLayer.push(args);
      };
      window.gtag("js", new Date());
      window.gtag("config", measurementId, { send_page_view: false });
    }

    // Track page view on route change
    const url =
      pathname + (searchParams.toString() ? `?${searchParams.toString()}` : "");
    window.gtag("event", "page_view", {
      page_path: url,
      page_title: document.title,
    });
  }, [pathname, searchParams]);

  return null;
}

/**
 * Track a custom GA4 event.
 * Safe to call in any client component — no-ops in dev or when GA is absent.
 */
export function trackEvent(
  eventName: string,
  eventParams: Record<string, unknown> = {}
): void {
  if (
    process.env.NODE_ENV === "production" &&
    typeof window !== "undefined" &&
    window.gtag
  ) {
    window.gtag("event", eventName, eventParams);
  }
}
