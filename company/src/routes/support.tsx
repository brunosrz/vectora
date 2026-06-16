import { createFileRoute, Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import {
  Mail,
  Bug,
  BookOpen,
  Users,
  MessageCircle,
  FileText,
} from "lucide-react";
import Container from "#/components/shared/Container";
import PageHeader from "#/components/shared/PageHeader";

export const Route = createFileRoute("/support")({
  head: () => ({
    meta: [
      { title: m.page_support_title() },
      {
        property: "og:image",
        content: `/api/og?title=${encodeURIComponent(m.page_support_title())}&desc=${encodeURIComponent("Email, GitHub Issues e documentação. Suporte rápido para seu Vectora.")}`,
      },
    ],
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "ContactPage",
          name: "Suporte — Vectora",
          url: "https://vectora.company/support",
          contactPoint: [
            {
              "@type": "ContactPoint",
              email: "support@vectora.company",
              contactType: "customer support",
            },
            {
              "@type": "ContactPoint",
              telephone: "+55-35-91017-9164",
              contactType: "technical support",
              contactOption: "WhatsApp",
            },
          ],
        }),
      },
    ],
  }),
  component: SupportPage,
});

const CHANNELS = [
  {
    icon: Mail,
    title: "Email",
    desc: "Resposta em até 48h (Plus) ou 24h (Pro)",
    action: {
      label: "support@vectora.company",
      href: "mailto:support@vectora.company",
    },
    sla: { plus: "48h", pro: "24h", trial: "Community" },
    badge: null as string | null,
  },
  {
    icon: Users,
    title: "Discord",
    desc: "Comunidade ativa de usuários. Tire dúvidas, compartilhe casos de uso e acompanhe novidades.",
    action: { label: "discord.gg/vectora", href: "https://discord.gg/vectora" },
    sla: null,
    badge: "Community",
  },
  {
    icon: MessageCircle,
    title: "WhatsApp",
    desc: "Contato direto com o fundador. Somente WhatsApp — sem chamadas de voz.",
    action: { label: "+55 35 91017-9164", href: "https://wa.me/5535910179164" },
    sla: null,
    badge: "WhatsApp only",
  },
  {
    icon: Bug,
    title: "GitHub Issues",
    desc: "Bugs, feature requests e discussões técnicas abertas",
    action: {
      label: "github.com/vectora-company/vectora",
      href: "https://github.com/vectora-company/vectora/issues",
    },
    sla: null,
    badge: null,
  },
  {
    icon: BookOpen,
    title: "Documentação",
    desc: "Guias de instalação, API reference e tutoriais",
    action: {
      label: "docs.vectora.company",
      href: "https://docs.vectora.company",
    },
    sla: null,
    badge: null,
  },
];

function SupportPage() {
  return (
    <Container size="prose" className="py-16">
      <PageHeader
        title={m.page_support_title()}
        subtitle={m.support_subtitle()}
      />

      <div className="mb-8 mt-10">
        <Link
          to="/issues"
          className="flex w-full items-center justify-between rounded-xl border border-primary/40 bg-primary/10 px-5 py-4 text-left transition-all hover:border-primary/60 hover:bg-primary/15"
        >
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/20 p-2">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="font-semibold text-foreground">
                Reportar bug ou sugerir feature
              </p>
              <p className="text-sm text-muted-foreground">
                Abra um issue diretamente pelo site — sem precisar de GitHub
              </p>
            </div>
          </div>
          <span className="ml-4 shrink-0 text-primary">→</span>
        </Link>
      </div>

      <div className="space-y-3">
        {CHANNELS.map((ch) => {
          const Icon = ch.icon;
          return (
            <div
              key={ch.title}
              className="flex items-start gap-4 rounded-xl border border-border bg-card/30 p-5"
            >
              <div className="mt-0.5 rounded-lg bg-primary/10 p-2.5">
                <Icon className="h-5 w-5 text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-foreground">{ch.title}</p>
                  {ch.badge && (
                    <span className="rounded border border-border bg-background px-2 py-0.5 text-xs text-muted-foreground">
                      {ch.badge}
                    </span>
                  )}
                </div>
                <p className="mb-2 text-sm text-muted-foreground">{ch.desc}</p>
                <a
                  href={ch.action.href}
                  target={
                    ch.action.href.startsWith("http") ? "_blank" : undefined
                  }
                  rel="noopener noreferrer"
                  className="break-all text-sm font-medium text-primary transition-colors hover:text-primary"
                >
                  {ch.action.label}
                </a>
                {ch.sla && (
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <span className="rounded border border-border bg-background px-2 py-0.5 text-muted-foreground">
                      Teste: {ch.sla.trial}
                    </span>
                    <span className="rounded border border-border bg-background px-2 py-0.5 text-muted-foreground">
                      Plus: {ch.sla.plus}
                    </span>
                    <span className="rounded border border-primary/30 bg-primary/10 px-2 py-0.5 text-primary">
                      Pro: {ch.sla.pro}
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </Container>
  );
}
