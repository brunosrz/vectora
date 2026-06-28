import { createFileRoute } from "@tanstack/react-router";

const APP_URL = "https://vectora.company";
const LOCALES = ["pt", "en", "es", "fr", "it", "de", "ru"] as const;

const PUBLIC_ROUTES = [
  { path: "/", priority: "1.0", changefreq: "weekly" },
  { path: "/faq", priority: "0.7", changefreq: "monthly" },
  { path: "/support", priority: "0.6", changefreq: "monthly" },
  { path: "/issues", priority: "0.4", changefreq: "monthly" },
  { path: "/roadmap", priority: "0.5", changefreq: "monthly" },
  { path: "/privacy", priority: "0.3", changefreq: "monthly" },
  { path: "/terms", priority: "0.3", changefreq: "monthly" },
  { path: "/cookies", priority: "0.3", changefreq: "monthly" },
  { path: "/sla", priority: "0.3", changefreq: "monthly" },
  { path: "/dpa", priority: "0.3", changefreq: "monthly" },
];

function localeUrl(path: string, locale: string) {
  const base = locale === "pt" ? APP_URL : `${APP_URL}/${locale}`;
  return path === "/" ? base : `${base}${path}`;
}

function buildSitemap() {
  const lastmod = new Date().toISOString().split("T")[0];

  const urls = PUBLIC_ROUTES.flatMap(({ path, priority, changefreq }) =>
    LOCALES.map((locale) => {
      const loc = localeUrl(path, locale);
      const alternates = LOCALES.map(
        (l) => `
      <xhtml:link rel="alternate" hreflang="${l}" href="${localeUrl(path, l)}"/>`,
      ).join("");
      const defaultAlternate = `
      <xhtml:link rel="alternate" hreflang="x-default" href="${localeUrl(path, "pt")}"/>`;

      return `
  <url>
    <loc>${loc}</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>${changefreq}</changefreq>
    <priority>${priority}</priority>${alternates}${defaultAlternate}
  </url>`;
    }),
  ).join("");

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset
  xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
  xmlns:xhtml="http://www.w3.org/1999/xhtml">${urls}
</urlset>`;
}

export const Route = createFileRoute("/sitemap.xml")({
  // Served as a plain text/xml response via a loader
  loader: () => {
    return new Response(buildSitemap(), {
      headers: {
        "Content-Type": "application/xml; charset=utf-8",
        "Cache-Control": "public, max-age=86400",
      },
    });
  },
  component: () => null,
});
