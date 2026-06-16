import { createFileRoute } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import PricingSection from "#/components/landing/PricingSection";
import FaqAccordion from "#/components/shared/FaqAccordion";
import WaitlistCta from "#/components/landing/WaitlistCta";
import Container from "#/components/shared/Container";

// Mensagens i18n (paraglide) — avaliadas na renderização para refletir o locale.
const PRICING_FAQS = () => [
  { question: m.pricing_faq_q1(), answer: m.pricing_faq_a1() },
  { question: m.pricing_faq_q2(), answer: m.pricing_faq_a2() },
  { question: m.pricing_faq_q3(), answer: m.pricing_faq_a3() },
  { question: m.pricing_faq_q4(), answer: m.pricing_faq_a4() },
  { question: m.pricing_faq_q5(), answer: m.pricing_faq_a5() },
];

export const Route = createFileRoute("/pricing")({
  head: () => ({
    meta: [
      { title: m.page_pricing_title() },
      { name: "description", content: m.page_pricing_desc() },
      {
        property: "og:image",
        content: `/api/og?title=${encodeURIComponent(m.page_pricing_title())}&desc=${encodeURIComponent(m.page_pricing_desc())}`,
      },
    ],
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "Product",
          name: "Vectora",
          offers: [
            {
              "@type": "Offer",
              name: "Plus",
              priceCurrency: "BRL",
              price: "20.00",
              billingIncrement: "P1M",
            },
            {
              "@type": "Offer",
              name: "Pro",
              priceCurrency: "BRL",
              price: "55.00",
              billingIncrement: "P1M",
            },
          ],
        }),
      },
    ],
  }),
  component: PricingPage,
});

function PricingPage() {
  return (
    <>
      <PricingSection />
      <Container size="prose" className="py-10 sm:py-14">
        <h2 className="mb-8 text-center text-2xl font-semibold text-foreground">
          {m.pricing_faq_heading()}
        </h2>
        <FaqAccordion items={PRICING_FAQS()} />
      </Container>
      <WaitlistCta />
    </>
  );
}
