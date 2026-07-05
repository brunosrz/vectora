import { createFileRoute } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import { CheckCircle2, Construction, MapPin } from "lucide-react";
import Container from "#/components/shared/Container";
import PageHeader from "#/components/shared/PageHeader";

export const Route = createFileRoute("/roadmap")({
  head: () => ({
    meta: [
      { title: m.page_roadmap_title() },
      { name: "description", content: m.page_roadmap_desc() },
      {
        property: "og:image",
        content: `/api/og?title=${encodeURIComponent(m.page_roadmap_title())}&desc=${encodeURIComponent(m.page_roadmap_desc())}`,
      },
    ],
  }),
  component: RoadmapPage,
});

const SHIPPED = [
  { label: "Desktop app — Windows, macOS, Linux (Electron + backend Nuitka)" },
  {
    label: "Agente principal — arquitetura deep-agent (LangGraph + deepagents)",
  },
  { label: "Coder Agent + Search Agent — arquivos, terminal, git, web, RAG" },
  { label: "RAG híbrido — Cohere Embed + LanceDB + BM25/denso + reranker" },
  { label: "MCP server sempre-ativo — Claude Code, Claude Desktop e outros" },
  { label: "Chat web multi-usuário (plano Pro)" },
  { label: "docs.vectora.company — documentação completa" },
  { label: "vectora.company — site institucional e dashboard de licença" },
  { label: "Autenticação + billing (Stripe INTL + Asaas BR)" },
  { label: "VECTORA_TOKEN — recuperável a qualquer momento, com rotação" },
  { label: "REST API /v1 — classify, extract, jobs + API keys com escopos" },
  { label: "Suporte multi-idioma — 7 locales (pt, en, es, fr, it, de, ru)" },
  { label: "Sistema de issues e feedback pelo site" },
  { label: "Webhooks de billing com Stripe e Asaas" },
  { label: "GDPR — exportação de dados e exclusão de conta em 30 dias" },
];

const BUILDING = [
  { label: "Context Graph nativo — tree-sitter + extração por LLM (beta)" },
  { label: "IDE mode — layout de editor no workbench (beta)" },
];

const PLANNED = [
  {
    label:
      "REST API pública completa — auth, threads/chat, workspaces, git, terminal, RAG, tasks, webhooks e settings via API (hoje só classify/extract/jobs são públicos)",
  },
  { label: "Integração nativa com VS Code e JetBrains via ACP" },
  {
    label:
      "Ollama gateway — modelos locais custom (inclusive remotos) registrados pelo usuário",
  },
  {
    label: "OpenRouter gateway — modelos custom via API key própria do usuário",
  },
  { label: "SDK Python — pacote PyPI oficial (plugins/extensões do Vectora)" },
  { label: "SDK TypeScript/Node — pacote NPM oficial (plugins/extensões)" },
  { label: "GitHub Actions integration — run Vectora directly from CI" },
  { label: "n8n workflow nodes" },
  { label: "Kubernetes helm chart" },
  { label: "Audit log completo — todas as ações de usuários e agentes" },
  { label: "Conformidade SOC 2 Type I" },
  { label: "SAML SSO para plano Enterprise" },
];

type Section = {
  id: string;
  label: string;
  icon: typeof CheckCircle2;
  iconClass: string;
  borderClass: string;
  badgeClass: string;
  items: { label: string }[];
};

const SECTIONS: Section[] = [
  {
    id: "shipped",
    label: "Lançado",
    icon: CheckCircle2,
    iconClass: "text-accent-green",
    borderClass: "border-accent-green/20",
    badgeClass: "bg-accent-green/10 text-accent-green border-accent-green/30",
    items: SHIPPED,
  },
  {
    id: "building",
    label: "Em desenvolvimento",
    icon: Construction,
    iconClass: "text-accent-amber",
    borderClass: "border-accent-amber/20",
    badgeClass: "bg-accent-amber/10 text-accent-amber border-accent-amber/30",
    items: BUILDING,
  },
  {
    id: "planned",
    label: "Planejado",
    icon: MapPin,
    iconClass: "text-primary",
    borderClass: "border-primary/20",
    badgeClass: "bg-primary/10 text-primary border-primary/30",
    items: PLANNED,
  },
];

function RoadmapPage() {
  return (
    <Container className="py-16">
      <div className="mb-14">
        <PageHeader
          title={m.page_roadmap_title()}
          subtitle={m.page_roadmap_desc()}
        />
      </div>

      <div className="grid gap-8 md:grid-cols-3">
        {SECTIONS.map((section) => {
          const Icon = section.icon;
          return (
            <div
              key={section.id}
              className={`rounded-2xl border ${section.borderClass} bg-background/40 p-5`}
            >
              <div className="mb-5 flex items-center gap-2">
                <Icon className={`h-5 w-5 ${section.iconClass}`} />
                <span
                  className={`rounded border ${section.badgeClass} px-2.5 py-0.5 text-sm font-medium`}
                >
                  {section.label}
                </span>
              </div>
              <ul className="space-y-2.5">
                {section.items.map((item, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-foreground/90"
                  >
                    <span
                      className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${section.iconClass} bg-current opacity-60`}
                    />
                    {item.label}
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      <p className="mt-10 text-center text-xs text-muted-foreground/80">
        Última atualização: julho 2026 · Roadmap sujeito a alterações
      </p>
    </Container>
  );
}
