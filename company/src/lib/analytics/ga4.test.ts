import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

beforeEach(() => {
  delete (window as { gtag?: unknown }).gtag;
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("trackEvent", () => {
  it("chama window.gtag('event', ...) quando gtag existe", async () => {
    const { trackEvent } = await import("./ga4");
    const gtag = vi.fn();
    window.gtag = gtag;

    trackEvent("waitlist_join", { source: "landing" });

    expect(gtag).toHaveBeenCalledWith("event", "waitlist_join", {
      source: "landing",
    });
  });

  it("não lança e não faz nada quando window.gtag não existe (edge — bloqueador de ads)", async () => {
    const { trackEvent } = await import("./ga4");
    expect(() => trackEvent("waitlist_join")).not.toThrow();
  });

  it("funciona sem params opcionais", async () => {
    const { trackEvent } = await import("./ga4");
    const gtag = vi.fn();
    window.gtag = gtag;

    trackEvent("pricing_viewed");

    expect(gtag).toHaveBeenCalledWith("event", "pricing_viewed", undefined);
  });
});

describe("trackPageView", () => {
  it("chama gtag('config', GA4_ID, ...) quando GA4_ID está configurado", async () => {
    vi.stubEnv("VITE_GA4_MEASUREMENT_ID", "G-TEST123");
    vi.resetModules();
    const { trackPageView } = await import("./ga4");
    const gtag = vi.fn();
    window.gtag = gtag;

    trackPageView("/pricing");

    expect(gtag).toHaveBeenCalledWith("config", "G-TEST123", {
      page_path: "/pricing",
    });
  });

  it("não chama gtag quando GA4_ID não está configurado (edge)", async () => {
    vi.stubEnv("VITE_GA4_MEASUREMENT_ID", "");
    vi.resetModules();
    const { trackPageView } = await import("./ga4");
    const gtag = vi.fn();
    window.gtag = gtag;

    trackPageView("/pricing");

    expect(gtag).not.toHaveBeenCalled();
  });

  it("não lança quando gtag está ausente (edge)", async () => {
    const { trackPageView } = await import("./ga4");
    expect(() => trackPageView("/pricing")).not.toThrow();
  });
});
