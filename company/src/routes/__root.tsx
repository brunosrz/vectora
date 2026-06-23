import {
  HeadContent,
  Scripts,
  createRootRouteWithContext,
  useRouterState,
} from "@tanstack/react-router";
import { useEffect } from "react";
import { Toaster } from "sonner";
import Devtools from "#/components/shared/Devtools";
import { getLocale } from "#/paraglide/runtime";
import { m } from "#/paraglide/messages";
import { GA4_ID } from "#/lib/analytics/ga4";
import { initAuthListener } from "#/store/auth";
import { THEME_INIT_SCRIPT } from "#/lib/theme";
import Header from "#/components/shared/Header";
import Footer from "#/components/shared/Footer";
import appCss from "../styles.css?url";
import type { QueryClient } from "@tanstack/react-query";

interface MyRouterContext {
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<MyRouterContext>()({
  beforeLoad: async () => {
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("lang", getLocale());
    }
  },

  head: () => {
    const plausibleDomain =
      typeof import.meta !== "undefined"
        ? (import.meta.env.VITE_PLAUSIBLE_DOMAIN ?? "vectora.company")
        : "vectora.company";

    return {
      meta: [
        { charSet: "utf-8" },
        { name: "viewport", content: "width=device-width, initial-scale=1" },
        { title: m.site_title() },
        { name: "description", content: m.site_description() },
        { property: "og:site_name", content: "Vectora" },
        { property: "og:type", content: "website" },
        { name: "twitter:card", content: "summary_large_image" },
        ...(typeof import.meta !== "undefined" &&
        import.meta.env.VITE_GOOGLE_SITE_VERIFICATION
          ? [
              {
                name: "google-site-verification",
                content: import.meta.env.VITE_GOOGLE_SITE_VERIFICATION,
              },
            ]
          : []),
      ],
      links: [
        { rel: "stylesheet", href: appCss },
        { rel: "icon", href: "/favicon-32x32.png", sizes: "32x32" },
        { rel: "icon", href: "/favicon-16x16.png", sizes: "16x16" },
        {
          rel: "preload",
          href: "/fonts/aeonikmono-regular.otf",
          as: "font",
          type: "font/otf",
          crossOrigin: "anonymous",
        },
      ],
      scripts: [
        // Anti-FOUC: aplica .dark/.light antes do primeiro paint.
        { children: THEME_INIT_SCRIPT },
        {
          src: `https://plausible.io/js/script.js`,
          defer: true,
          "data-domain": plausibleDomain,
        },
        ...(GA4_ID
          ? [
              {
                src: `https://www.googletagmanager.com/gtag/js?id=${GA4_ID}`,
                async: true,
              },
              {
                children: `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag('js',new Date());gtag('config','${GA4_ID}');`,
              },
            ]
          : []),
      ],
    };
  },

  shellComponent: RootDocument,
});

function RootDocument({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const cleanup = initAuthListener();
    return cleanup;
  }, []);

  const { location } = useRouterState();
  const isDashboard = location.pathname.startsWith("/dashboard");

  return (
    // suppressHydrationWarning: a classe do tema (dark/light) é aplicada por
    // script inline antes da hidratação e nunca bate com o HTML do SSR.
    <html lang={getLocale()} suppressHydrationWarning>
      <head>
        <HeadContent />
      </head>
      <body>
        {!isDashboard && <Header />}
        {children}
        {!isDashboard && <Footer />}
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: "var(--card)",
              border: "1px solid var(--border)",
              color: "var(--card-foreground)",
            },
          }}
        />
        <Devtools />
        <Scripts />
      </body>
    </html>
  );
}
