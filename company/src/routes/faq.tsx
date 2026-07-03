import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { m } from "#/paraglide/messages";
import FaqAccordion from "#/components/shared/FaqAccordion";
import Container from "#/components/shared/Container";
import PageHeader from "#/components/shared/PageHeader";

const FAQ_DATA = {
  Geral: [
    {
      question: "O que é o Vectora?",
      answer:
        "Vectora é uma plataforma self-hosted de agentes de IA com RAG avançado para times de engenharia.",
    },
    {
      question: "Como funciona o self-hosting?",
      answer:
        "Você instala o Vectora no seu próprio servidor com um único comando Docker. Seus dados nunca saem da sua infra.",
    },
    {
      question: "Preciso de GPU para rodar?",
      answer:
        "Não. Vectora usa a API Cohere para embeddings e LLMs externos. Uma VPS com 2 vCPUs e 4 GB RAM é suficiente.",
    },
  ],
  Instalação: [
    {
      question: "Quais sistemas operacionais são suportados?",
      answer: "Qualquer VPS Linux com Docker. Ubuntu 22.04+ é recomendado.",
    },
    {
      question: "Quais provedores de cloud funcionam?",
      answer:
        "AWS, GCP, Hetzner, DigitalOcean, Linode ou qualquer servidor com Docker e acesso à internet.",
    },
    {
      question: "Quanto tempo leva a instalação?",
      answer:
        "Menos de 5 minutos. Um único arquivo docker-compose.yml sobe toda a stack.",
    },
  ],
  Planos: [
    {
      question: "Qual a diferença entre Free e Pro?",
      answer:
        "Free é grátis pra sempre e não exige conta: CLI, MCP, Desktop e RAG local ilimitado, tudo rodando na sua máquina. Pro (R$24/mês) exige conta e adiciona o que só faz sentido em time: chat web multi-usuário, convites de membro ilimitados, SSO/SAML, storage escalável (Postgres/Qdrant/Redis), webhooks, rate limit maior na REST API e suporte prioritário.",
    },
    {
      question: "Preciso criar conta para usar o Vectora?",
      answer:
        "Não, se for uso local/solo. O plano Free funciona 100% sem login. Conta só é necessária para os recursos de time do Pro.",
    },
    {
      question: "Posso cancelar a qualquer momento?",
      answer:
        "Sim. Sem fidelidade mínima. Cancele pelo painel a qualquer momento — sua conta volta para o plano Free automaticamente.",
    },
  ],
  Segurança: [
    {
      question: "Meus dados são enviados para a Vectora?",
      answer:
        "Não. Tudo fica no seu servidor. A Vectora não tem acesso a documentos, conversas ou código.",
    },
    {
      question: "O Vectora é compatível com LGPD e GDPR?",
      answer:
        "Sim. Como os dados ficam na sua infra, você mantém controle total sobre conformidade.",
    },
    {
      question: "Como funciona a autenticação?",
      answer:
        "No Free, uso local sem login. Para o Pro (conta obrigatória), autenticação própria da Vectora com suporte a email/senha e magic link.",
    },
  ],
  Técnico: [
    {
      question: "Quais LLMs são suportados?",
      answer:
        "Anthropic, OpenAI, Cohere, Ollama (local) e qualquer provedor compatível com OpenAI API.",
    },
    {
      question: "Como funciona o RAG?",
      answer:
        "Hybrid RAG com embeddings Cohere, LanceDB como vector store, BM25 + dense retrieval com RRF merge e reranker Cohere.",
    },
    {
      question: "Existe API pública?",
      answer:
        "Sim. REST API /v1 com limites por plano (10 req/min no Free, 100 req/min no Pro). Docs em docs.vectora.company.",
    },
  ],
};

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
          mainEntity: Object.values(FAQ_DATA)
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
  const categories = Object.entries(FAQ_DATA);

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
          placeholder="Buscar pergunta..."
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
