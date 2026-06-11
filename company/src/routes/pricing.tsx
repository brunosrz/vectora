import { createFileRoute } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import PricingSection from "#/components/landing/PricingSection";
import FaqAccordion from "#/components/shared/FaqAccordion";
import WaitlistCta from "#/components/landing/WaitlistCta";

const PRICING_FAQS = [
  {
    question: "O trial de 30 dias exige cartão de crédito?",
    answer:
      "Não. O trial começa imediatamente após criar sua conta, sem necessidade de cartão.",
  },
  {
    question: "Posso trocar de plano durante o trial?",
    answer:
      "Sim. Você pode fazer upgrade ou downgrade a qualquer momento antes do trial terminar.",
  },
  {
    question: "Quais formas de pagamento são aceitas?",
    answer:
      "Brasil: PIX, Boleto e Cartão via Asaas. Internacional: Cartão via Stripe.",
  },
  {
    question: "O que acontece quando o trial termina?",
    answer:
      "Sua conta entra em modo inativo. Os dados são preservados por 30 dias para que você possa assinar.",
  },
  {
    question: "Posso cancelar a qualquer momento?",
    answer:
      "Sim. Não há fidelidade mínima. Cancele pelo painel e o acesso continua até o fim do período pago.",
  },
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
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <h2 className="mb-8 text-center text-2xl font-semibold text-foreground">
          Perguntas frequentes
        </h2>
        <FaqAccordion items={PRICING_FAQS} />
      </div>
      <WaitlistCta />
    </>
  );
}
