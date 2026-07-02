import { createFileRoute } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import Hero from "#/components/landing/Hero";
import ShowcaseGifs from "#/components/landing/ShowcaseGifs";
import AgenticFlowSection from "#/components/landing/AgenticFlowSection";
import RagFlowSection from "#/components/landing/RagFlowSection";
import TeamSetupSection from "#/components/landing/TeamSetupSection";
import WhySelfHosted from "#/components/landing/WhySelfHosted";
import PricingSection from "#/components/landing/PricingSection";
import WaitlistCta from "#/components/landing/WaitlistCta";

const HREFLANG_LOCALES = ["pt", "en", "es", "fr", "it", "de", "ru"] as const;
const APP_URL = "https://vectora.company";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: m.page_home_title() },
      { name: "description", content: m.page_home_desc() },
      { property: "og:title", content: m.page_home_title() },
      { property: "og:description", content: m.page_home_desc() },
      { property: "og:type", content: "website" },
      { property: "og:url", content: APP_URL },
      {
        property: "og:image",
        content: `${APP_URL}/api/og?title=${encodeURIComponent(m.page_home_title())}&desc=${encodeURIComponent(m.page_home_desc())}`,
      },
    ],
    links: [
      ...HREFLANG_LOCALES.map((lang) => ({
        rel: "alternate",
        hrefLang: lang,
        href: lang === "pt" ? APP_URL : `${APP_URL}/${lang}`,
      })),
      { rel: "alternate", hrefLang: "x-default", href: APP_URL },
    ],
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify({
          "@context": "https://schema.org",
          "@graph": [
            {
              "@type": "SoftwareApplication",
              name: "Vectora",
              applicationCategory: "DeveloperApplication",
              operatingSystem: "Linux",
              offers: [
                {
                  "@type": "Offer",
                  name: "Free",
                  price: "0.00",
                  priceCurrency: "BRL",
                },
                {
                  "@type": "Offer",
                  name: "Pro",
                  price: "24.00",
                  priceCurrency: "BRL",
                },
              ],
              description: m.site_description(),
              url: APP_URL,
            },
            {
              "@type": "Organization",
              name: "Vectora",
              url: APP_URL,
              logo: `${APP_URL}/logo.svg`,
              contactPoint: {
                "@type": "ContactPoint",
                email: "support@vectora.company",
                contactType: "customer support",
              },
            },
            {
              "@type": "WebSite",
              name: "Vectora",
              url: APP_URL,
              potentialAction: {
                "@type": "SearchAction",
                target: {
                  "@type": "EntryPoint",
                  urlTemplate: `${APP_URL}/faq?q={search_term_string}`,
                },
                "query-input": "required name=search_term_string",
              },
            },
          ],
        }),
      },
    ],
  }),
  component: LandingPage,
});

function LandingPage() {
  return (
    <>
      <Hero />
      <ShowcaseGifs />
      <AgenticFlowSection />
      <RagFlowSection />
      <TeamSetupSection />
      <WhySelfHosted />
      <PricingSection />
      <WaitlistCta />
    </>
  );
}
