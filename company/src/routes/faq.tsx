import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { m } from "#/paraglide/messages";
import FaqAccordion from "#/components/shared/FaqAccordion";
import Container from "#/components/shared/Container";
import PageHeader from "#/components/shared/PageHeader";

function getFaqData() {
  return {
    [m.faq_cat_geral()]: [
      { question: m.faq_geral_1_question(), answer: m.faq_geral_1_answer() },
      { question: m.faq_geral_2_question(), answer: m.faq_geral_2_answer() },
      { question: m.faq_geral_3_question(), answer: m.faq_geral_3_answer() },
    ],
    [m.faq_cat_instalacao()]: [
      {
        question: m.faq_instalacao_1_question(),
        answer: m.faq_instalacao_1_answer(),
      },
      {
        question: m.faq_instalacao_2_question(),
        answer: m.faq_instalacao_2_answer(),
      },
      {
        question: m.faq_instalacao_3_question(),
        answer: m.faq_instalacao_3_answer(),
      },
    ],
    [m.faq_cat_planos()]: [
      {
        question: m.faq_planos_1_question(),
        answer: m.faq_planos_1_answer(),
      },
      {
        question: m.faq_planos_2_question(),
        answer: m.faq_planos_2_answer(),
      },
      {
        question: m.faq_planos_3_question(),
        answer: m.faq_planos_3_answer(),
      },
    ],
    [m.faq_cat_seguranca()]: [
      {
        question: m.faq_seguranca_1_question(),
        answer: m.faq_seguranca_1_answer(),
      },
      {
        question: m.faq_seguranca_2_question(),
        answer: m.faq_seguranca_2_answer(),
      },
      {
        question: m.faq_seguranca_3_question(),
        answer: m.faq_seguranca_3_answer(),
      },
    ],
    [m.faq_cat_tecnico()]: [
      {
        question: m.faq_tecnico_1_question(),
        answer: m.faq_tecnico_1_answer(),
      },
      {
        question: m.faq_tecnico_2_question(),
        answer: m.faq_tecnico_2_answer(),
      },
      {
        question: m.faq_tecnico_3_question(),
        answer: m.faq_tecnico_3_answer(),
      },
    ],
  };
}

export const Route = createFileRoute("/faq")({
  head: () => ({
    meta: [
      { title: m.page_faq_title() },
      { name: "description", content: m.page_faq_desc() },
      {
        property: "og:image",
        content: `/api/og?title=${encodeURIComponent(m.page_faq_title())}&desc=${encodeURIComponent(m.page_faq_desc())}`,
      },
    ],
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "FAQPage",
          mainEntity: Object.values(getFaqData())
            .flat()
            .map((item) => ({
              "@type": "Question",
              name: item.question,
              acceptedAnswer: { "@type": "Answer", text: item.answer },
            })),
        }),
      },
    ],
  }),
  component: FaqPage,
});

function FaqPage() {
  const [search, setSearch] = useState("");
  const categories = Object.entries(getFaqData());

  const filtered = categories
    .map(([cat, items]) => ({
      cat,
      items: items.filter(
        (i) =>
          !search ||
          i.question.toLowerCase().includes(search.toLowerCase()) ||
          i.answer.toLowerCase().includes(search.toLowerCase()),
      ),
    }))
    .filter((c) => c.items.length > 0);

  return (
    <Container size="prose" className="py-16">
      <PageHeader title={m.page_faq_title()}>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={m.faq_search_placeholder()}
          className="mt-4 w-full max-w-sm rounded-xl border border-border bg-card/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary transition-colors"
        />
      </PageHeader>

      <div className="mt-10 space-y-10">
        {filtered.map(({ cat, items }) => (
          <div key={cat}>
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              {cat}
            </h2>
            <FaqAccordion items={items} />
          </div>
        ))}
      </div>
    </Container>
  );
}
