// Google Analytics 4 — complementa Plausible com dados de funil e Search Console
// Script injetado via __root.tsx head()

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
    dataLayer?: unknown[];
  }
}

export const GA4_ID = import.meta.env.VITE_GA4_MEASUREMENT_ID as
  string | undefined;

export function trackEvent(
  eventName: string,
  params?: Record<string, string | number | boolean>,
) {
  if (typeof window !== "undefined" && window.gtag) {
    window.gtag("event", eventName, params);
  }
}

export function trackPageView(url: string) {
  if (typeof window !== "undefined" && window.gtag && GA4_ID) {
    window.gtag("config", GA4_ID, { page_path: url });
  }
}
