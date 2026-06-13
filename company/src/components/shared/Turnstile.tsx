import { useEffect, useRef } from "react";
import { TURNSTILE_SITE_KEY } from "#/lib/turnstile";

interface TurnstileProps {
  onSuccess: (token: string) => void;
  onError?: () => void;
  onExpire?: () => void;
}

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement,
        options: {
          sitekey: string;
          callback: (token: string) => void;
          "error-callback"?: () => void;
          "expired-callback"?: () => void;
          theme?: "light" | "dark" | "auto";
          size?: "normal" | "compact" | "flexible";
        },
      ) => string;
      remove: (widgetId: string) => void;
      reset: (widgetId: string) => void;
    };
  }
}

export default function Turnstile({
  onSuccess,
  onError,
  onExpire,
}: TurnstileProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!TURNSTILE_SITE_KEY || !containerRef.current) return;

    const scriptId = "cf-turnstile-script";
    const render = () => {
      if (!containerRef.current) return;
      widgetIdRef.current = window.turnstile!.render(containerRef.current, {
        sitekey: TURNSTILE_SITE_KEY!,
        callback: onSuccess,
        "error-callback": onError,
        "expired-callback": onExpire,
        theme: "dark",
        size: "flexible",
      });
    };

    if (window.turnstile) {
      render();
    } else if (!document.getElementById(scriptId)) {
      const script = document.createElement("script");
      script.id = scriptId;
      script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
      script.async = true;
      script.onload = render;
      document.head.appendChild(script);
    } else {
      const interval = setInterval(() => {
        if (window.turnstile) {
          clearInterval(interval);
          render();
        }
      }, 100);
    }

    return () => {
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
      }
    };
  }, [onSuccess, onError, onExpire]);

  if (!TURNSTILE_SITE_KEY) return null;

  return <div ref={containerRef} className="mt-2" />;
}
