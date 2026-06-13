// Plausible Analytics — sem cookies, GDPR-compliant
// Script injetado via __root.tsx head()
// Self-hosted em analytics.vectora.company

declare global {
  interface Window {
    plausible?: (
      event: string,
      options?: { props?: Record<string, string | number | boolean> },
    ) => void;
  }
}

type TrackableEvent =
  | "signup"
  | "trial_started"
  | "paid_conversion"
  | "cancel"
  | "gif_viewed"
  | "pricing_viewed"
  | "waitlist_join"
  | "token_revealed"
  | "token_rotated";

export function track(
  event: TrackableEvent,
  props?: Record<string, string | number | boolean>,
) {
  if (typeof window !== "undefined" && window.plausible) {
    window.plausible(event, props ? { props } : undefined);
  }
}
