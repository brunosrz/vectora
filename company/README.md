# vectora.company

Site institucional + infra de billing da Vectora.

**Status**: Em desenvolvimento — pré-lançamento.

---

## Desenvolvimento

```bash
# Instalar dependências
bun install

# Configurar variáveis de ambiente
cp .env.example .env.local
# Preencher .env.local com as chaves do Supabase, Sentry, etc.

# Dev server
bun dev                  # http://localhost:3000

# Build de produção
bun run build

# Gerar tipos Supabase (após configurar projeto no Supabase)
bun supabase:types
```

**Pré-requisitos**: Bun ≥ 1.1 · Projeto Supabase criado · Node 20+ (para o Nitro)

---

## Stack (atual)

| Camada         | Tecnologia                                                 | Motivo                                                                                |
| -------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Framework      | **TanStack Start** (SSR via Nitro)                         | SSR nativo = SEO real sem prerender; mesma DX do Vite                                 |
| Roteamento     | **TanStack Router** (file-based, type-safe)                | Type-safe params/search, integrado ao TanStack Query                                  |
| Data fetching  | **TanStack Query**                                         | Cache, stale-while-revalidate, mutations                                              |
| React          | **React 19**                                               | Ecossistema, server components-ready                                                  |
| Estilos        | **Tailwind CSS v4**                                        | Utilitário, tree-shaking nativo, paleta custom da marca                               |
| Backend/Auth   | **Supabase** (Auth + Postgres + Edge Functions + Realtime) | Auth SSR, realtime para status da licença, Stripe/Asaas via Edge                      |
| ORM/Tipos      | **Supabase JS client** (`@supabase/ssr`) — sem Prisma      | Cliente oficial com RLS, tipos gerados pelo CLI                                       |
| Deploy         | **Vercel** (Nitro preset `vercel`)                         | CDN global, preview deployments por branch                                            |
| Email          | **Resend** (`resend`)                                      | Templates transacionais — templates React Email em `emails/`                          |
| Analytics      | **Plausible** (self-hosted) + **GA4**                      | Plausible: sem cookies, GDPR; GA4: funil + Search Console                             |
| Bot protection | **Cloudflare Turnstile**                                   | Proteção anti-bot sem fricção em signup/login                                         |
| i18n           | **Paraglide JS** (`@inlang/paraglide-js`)                  | Compile-time, type-safe, zero runtime; 7 idiomas: pt (padrão), en, es, fr, it, de, ru |
| Observability  | **Sentry** (`@sentry/tanstackstart-react`)                 | Erros + traces com instrumentação de server functions                                 |
| Qualidade      | **TypeScript strict + ESLint + Prettier + Vitest**         | Padrão de engenharia vinculante                                                       |
| Package mgr    | **Bun**                                                    | Install rápido, script runner nativo                                                  |

> **Nota arquitetural**: este projeto usa TanStack Start (SSR via Nitro) — HTML renderizado no servidor, sem prerender necessário. Supabase JS client substitui Prisma; Paraglide substitui i18next; TanStack Query substitui qualquer `fetch` nu.

---

## Estrutura do repositório

```
vectora-company/
├── app.config.ts                    (TanStack Start config — SSR, Vite plugins, adapter)
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── vercel.json
├── public/
│   ├── favicon-*.png, vectora.svg
│   ├── fonts/aeonikmono-*.otf
│   ├── robots.txt
│   ├── gifs/
│   │   ├── showcase-chat.gif        [PLACEHOLDER durante dev]
│   │   ├── showcase-rag.gif         [PLACEHOLDER durante dev]
│   │   ├── showcase-code.gif        [PLACEHOLDER durante dev]
│   │   ├── showcase-plan.gif        [PLACEHOLDER durante dev]
│   │   ├── setup-root.gif           [PLACEHOLDER durante dev]
│   │   ├── setup-invite.gif         [PLACEHOLDER durante dev]
│   │   └── setup-project.gif        [PLACEHOLDER durante dev]
│   └── diagrams/
│       ├── agentic-flow.svg
│       └── rag-flow.svg
├── messages/                        ← Paraglide JS (7 idiomas — compile-time)
│   └── pt.json  en.json  es.json  fr.json  it.json  de.json  ru.json
├── project.inlang/                  (Paraglide config)
├── src/
│   ├── router.tsx
│   ├── styles.css
│   ├── routes/
│   │   ├── __root.tsx               (shell HTML + Head meta + analytics + locale)
│   │   ├── index.tsx                (landing — P1, SSR)
│   │   ├── pricing.tsx
│   │   ├── faq.tsx
│   │   ├── issues.tsx
│   │   ├── support.tsx
│   │   ├── privacy.tsx
│   │   ├── terms.tsx
│   │   ├── cookies.tsx
│   │   ├── sla.tsx
│   │   ├── dpa.tsx
│   │   ├── login.tsx
│   │   ├── signup.tsx
│   │   └── dashboard/
│   │       ├── route.tsx            ← beforeLoad: auth guard; Realtime license_status
│   │       ├── index.tsx            (token reveal — default)
│   │       ├── license.tsx          (status da licença + histórico)
│   │       ├── billing.tsx
│   │       ├── api-keys.tsx
│   │       └── account.tsx
│   ├── components/
│   │   ├── landing/
│   │   │   ├── Hero.tsx
│   │   │   ├── ShowcaseGifs.tsx
│   │   │   ├── AgenticFlowSection.tsx
│   │   │   ├── RagFlowSection.tsx
│   │   │   ├── TeamSetupSection.tsx
│   │   │   ├── WhySelfHosted.tsx
│   │   │   ├── PricingSection.tsx
│   │   │   └── WaitlistCta.tsx
│   │   ├── dashboard/
│   │   │   ├── TokenReveal.tsx
│   │   │   ├── LicenseStatus.tsx
│   │   │   ├── BillingSection.tsx
│   │   │   ├── ApiKeysList.tsx
│   │   │   └── AccountSection.tsx
│   │   └── shared/
│   │       ├── Header.tsx
│   │       ├── Footer.tsx
│   │       ├── LocaleSwitcher.tsx
│   │       └── Turnstile.tsx
│   ├── server/
│   │   └── fns/                     ← createServerFn() — server-only
│   │       ├── auth.ts
│   │       ├── token.ts
│   │       ├── subscription.ts
│   │       ├── api-keys.ts
│   │       ├── gdpr.ts
│   │       └── issues.ts
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts            (browser)
│   │   │   ├── server.ts            (SSR com cookies)
│   │   │   ├── admin.ts             (service role — server fns only)
│   │   │   └── types.ts             (gerado via supabase gen types)
│   │   ├── analytics/
│   │   │   ├── plausible.ts
│   │   │   └── ga4.ts
│   │   ├── email/
│   │   │   └── resend.ts
│   │   ├── turnstile.ts
│   │   └── leads.ts                 (waitlist — já implementado)
│   ├── store/
│   │   └── auth.ts                  (Zustand — session espelhada do Supabase listener)
│   ├── hooks/
│   │   ├── use-session.ts
│   │   ├── use-subscription.ts
│   │   └── use-api-keys.ts
│   └── integrations/
│       └── tanstack-query/
│           └── root-provider.tsx
├── emails/                          (React Email templates)
│   ├── welcome.tsx
│   ├── trial-ending-7d.tsx
│   ├── trial-ending-1d.tsx
│   ├── invoice-paid.tsx
│   ├── invoice-failed.tsx
│   ├── magic-link.tsx
│   ├── account-deleted.tsx
│   └── waitlist-confirmation.tsx
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   └── functions/
│       ├── on-signup/
│       ├── validate-license/
│       ├── rotate-token/
│       ├── create-checkout/
│       ├── create-portal/
│       ├── webhooks/
│       └── cron-hard-delete/
└── tests/
    ├── unit/                        (Vitest)
    └── e2e/                         (Playwright)
```

---

## Padrões de engenharia (Company-specific)

Os padrões gerais do Vectora se aplicam integralmente. Adicionalmente:

1. **TanStack Query é a camada de dados** — nenhum `fetch` nu em componentes. Toda chamada de rede vive em um `useQuery` ou `useMutation` em `src/hooks/`.
2. **Zustand apenas para estado de UI** — dados do servidor ficam no cache do TanStack Query. Zustand armazena session de auth (espelhada do Supabase listener), locale e preferências de tema.
3. **Radix sem override de estilos de terceiros** — customização 100% via `className` + Tailwind. Sem `!important`.
4. **Rotas type-safe** — TanStack Router gera tipos para params/search; usar `Link` tipado, nunca string hardcoded de URL.
5. **Auth guard no layout do dashboard** — `dashboard/route.tsx` redireciona para `/login` se não houver session. Sem lógica de auth em componentes folha.
6. **Realtime Supabase apenas no dashboard** — o canal `license_status` fica ativo enquanto o dashboard está montado e é cancelado no unmount.

---

## BLOCO O — Identidade & Legal

> Pré-requisito de tudo. Sem CNPJ ativo e termos publicados, Stripe e Asaas não operam em produção.

### O1 — Estrutura jurídica

- Abrir MEI via `gov.br/mei` (CNAE 6201-5/01 principal + 6202-3/00 secundário).
- Conta bancária PJ: Nubank PJ, Inter PJ ou C6 PJ (zero tarifa, abertura digital).
- Inscrição municipal para emissão de NFS-e se exigida pela prefeitura.
- Documentar passo a passo em `ops/setup-mei.md`.

### O2 — Marca e domínios

**Domínio principal adquirido**: `vectora.company`.

**Subdomínios**:

| Subdomínio                  | Uso                        |
| --------------------------- | -------------------------- |
| `vectora.company`           | Site institucional (P)     |
| `docs.vectora.company`      | Documentação pública (Q)   |
| `api.vectora.company`       | REST API pública (J)       |
| `status.vectora.company`    | Status page (R6)           |
| `updates.vectora.company`   | Channel server auto-update |
| `analytics.vectora.company` | Plausible self-hosted      |

**Domínios adicionais (defesa de marca)**: `vectora.dev`, `vectora.com.br`, variantes typo.

**Identidade visual**: pássaro Vectora navy + azul claro, Aeonik Mono (já em `public/fonts/`), paleta `#0a0e1a` / `#3b82f6`. Assets centralizados em `brand/`: SVG vetorial, PNGs multi-res, dark/light variants, favicon kit, OG cards 1200×630.

**Registro INPI**: Classe 9 + Classe 42. Recomendado após 6 meses do lançamento.

### O3 — Termos legais (LGPD + GDPR-ready)

**Política de Privacidade** (`/privacy`): dados coletados (email, nome, logs de token, pagamento via gateway — cartão nunca armazenado, IP + user_agent no audit log); dados que não coletamos (conversas, arquivos, embeddings — self-hosted); base legal LGPD Art. 7º I e V; retenção (conta: enquanto ativa + 30d; logs: 90d; dados fiscais: 5 anos); DPO `dpo@vectora.company`.

**Termos de Uso / EULA** (`/terms`): licença não exclusiva e não transferível; trial 30 dias sem cartão; cancelamento a qualquer momento; limitação de responsabilidade (software "as is"); reembolso em 14 dias após primeira cobrança; foro São João Batista do Glória/MG.

**Cookies Policy** (`/cookies`): apenas 3 cookies essenciais (`vectora_access`, `vectora_refresh`, `vectora_lang`); sem tracking; botão "Limpar cookies" funcional.

**SLA** (`/sla`): uptime ≥ 99.5% mensal para validação de licença; latência p95 < 500ms; crédito de 10% por 0.5% abaixo do target. Apenas para clientes Pro/Enterprise.

**DPA** (`/dpa`): template EU DPA padrão ICC para clientes Enterprise.

Todos os documentos: linguagem clara, "tldr" no topo, versionados. Revisão por advogado SaaS antes do lançamento (estimativa R$2.000–R$5.000).

### O4 — Email e comunicação

**Provedor**: Google Workspace Business Starter (~R$30/mês por caixa).

| Endereço                   | Uso                                  |
| -------------------------- | ------------------------------------ |
| `bruno@vectora.company`    | Principal                            |
| `support@vectora.company`  | Suporte (alias R2)                   |
| `billing@vectora.company`  | Notificações fiscais Stripe/Asaas    |
| `security@vectora.company` | CVE reports / responsible disclosure |
| `dpo@vectora.company`      | LGPD/GDPR                            |
| `press@vectora.company`    | Imprensa                             |
| `legal@vectora.company`    | Questões contratuais                 |
| `noreply@vectora.company`  | Outbound transacional                |

**Outbound transacional**: Resend ou Postmark. Templates React Email em `emails/`. DKIM/SPF/DMARC configurados.

**WhatsApp Business**: número BR dedicado, auto-resposta fora do horário (seg–sex 9h–18h BRT), link `wa.me/55...` em todo site/footer.

**GitHub Organization** `vectora-company`: repos públicos (`docs`, `examples`, `issues`, `homebrew-tap`, `mcp-server-vectora`); repos privados (`vectora`, `site`, `supabase`, `brand`, `ops`). 2FA obrigatório, branch protection em `main`, Dependabot ativo.

### Verificação (Bloco O)

- MEI/ME com CNPJ ativo; emite NFS-e.
- Conta PJ operacional.
- `vectora.company` e subdomínios resolvendo corretamente.
- Emails `@vectora.company` com SPF/DKIM/DMARC `pass` no mxtoolbox.
- Termos, Privacy, Cookies, SLA, DPA publicados e revisados por advogado.
- GitHub Org criada com branch protection ativa.
- WhatsApp Business com auto-resposta configurada.

---

## BLOCO P — Site `vectora.company`

### P1 — Landing Page (`/`)

Scroll único, seções âncora, mobile-first.

**Hero**:

- Tagline: _"Your AI. Your Data. Your Server."_
- Subtítulo (≤15 palavras): "Self-hosted AI agent com RAG, MCP e chat web multi-usuário. Seus dados nunca saem do seu servidor."
- CTAs: "Começar trial grátis — 30 dias" (→ `/signup`) + "Ver preços" (→ `/pricing`).
- GIF central da interface do Vectora em uso. `loading="lazy" decoding="async"`. Placeholder skeleton durante dev.

**ShowcaseGifs**: grade 2×2 com 4 GIFs (showcase-chat, showcase-rag, showcase-code, showcase-plan) + label e descrição por card. Todos gravados em inglês.

**O que é RAG**: diagrama SVG animado com CSS. Ciclo: `Documento → Embedding → Vector Store → Query → Vector Search → Reranker → LLM → Resposta`. `prefers-reduced-motion` respeitado.

**Diagramas de arquitetura** (3 SVGs interativos):

1. Três modos de uso — CLI, MCP (sub-agente), Chat Web.
2. Agentes especializados (Orchestrator → RAG / Search / Coder).
3. Empresa com Vectora em VPS, time acessando via chat, workspace por dev.

**Pricing** (`#pricing`):

| Feature                     | Plus           | Pro                  |
| --------------------------- | -------------- | -------------------- |
| Trial gratuito              | 30 dias        | —                    |
| CLI + MCP                   | ✓              | ✓                    |
| Vectora Chat (web)          | —              | ✓                    |
| SQLite + LanceDB            | ✓              | ✓                    |
| PostgreSQL + Qdrant + Redis | —              | ✓                    |
| Multi-thread                | —              | ✓                    |
| Webhooks                    | —              | ✓                    |
| REST API `/v1`              | ✓ (60 req/min) | ✓ (600 req/min)      |
| SDKs Python/TS              | ✓              | ✓                    |
| ACP server                  | —              | ✓                    |
| Suporte                     | Email 48h      | Email 24h + WhatsApp |
| **BR**                      | R$20/mês       | R$55/mês             |
| **INTL**                    | $7/mês         | $20/mês              |

**Comparação "Por que self-hosted?"**: 4 cards — Privacidade · Custo · Customização · Soberania.

**Social proof**: pré-lançamento "Seja um dos primeiros — trial grátis, sem cartão."; pós-lançamento depoimentos reais (R5).

**Footer**: Links de produto + Legal + Social + "Made with ❤ in Brazil" + CNPJ.

### P2 — Auth (`/signup`, `/login`)

**`/signup`**: campos nome, email, senha, country select (BR/INTL). Supabase Auth → trigger `on-signup` cria token + trial automaticamente. Redirect para `/dashboard?welcome=true`. Cloudflare Turnstile.

**`/login`**: email + senha. Magic Link por email para recuperação. Sem OAuth no MVP.

### P3 — Dashboard (`/dashboard`)

**Sidebar**: Token · Licença · Pagamento · API Keys · Conta · Suporte.

**Seção Token** (rota default):

```
[ Clique para revelar seu token — exibido uma única vez ]
                                            [Rotacionar token]
⚠ Copie e guarde. Após fechar, não poderá ser exibido novamente.
   Se perder, use "Rotacionar token".
```

Após reveal: token em fonte mono com botão de cópia. Segunda visita → banner amarelo "Token já revelado — rotacione se perder".

**Seção Status da Licença**:

```
Plano: Plus — Trial
──────────────────────────────────────────────
Início:            01/06/2026
Término do trial:  01/07/2026
Dias restantes:    30 dias
Status:            ⏳ Trial ativo

[Assinar Plus — R$20/mês]   [Fazer upgrade para Pro — R$55/mês]
```

Status atualizado via Supabase Realtime (canal `license_status`) sem refresh manual.

**Seção Pagamento**: BR via Asaas embed (PIX/Boleto/Cartão tokenizado PCI DSS); INTL via Stripe Customer Portal.

**Seção API Keys**: lista de OAuth clients com nome, criado em, scopes, último uso. Modal "Criar API key" com show-secret-once. Revogar inline.

**Seção Histórico de Validações**: últimas 20 entradas de `license_checks`.

**Seção Conta**: editar nome/country/idioma, alterar senha via magic link, "Exportar meus dados" (GDPR Art. 20) → ZIP JSON, "Deletar conta" (GDPR Art. 17) → soft delete 30d + hard delete + cancela subscription.

**Guia de início rápido** (só em `?welcome=true`):

```
1. Revele e copie seu VECTORA_TOKEN acima
2. pip install vectora      (ou baixe o instalador nativo)
3. vectora setup            (cole o token quando solicitado)
4. vectora chat             (começar a usar)
```

### P4 — Pricing dedicado (`/pricing`)

Tabela comparativa expandida (todas as features), FAQ inline (8 perguntas), calculadora simples (quantos devs → preço total), CTAs duplos por plano. Toggle BR/INTL no topo (default por geo IP).

### P5 — FAQ (`/faq`)

Accordion por categoria: Geral · Instalação · Licença & Billing · Técnico · Comercial. Cada resposta com link "Saiba mais" para docs.

### P6 — Issues & Suporte (`/issues`, `/support`)

**`/issues`**: formulário → GitHub Issues API para `vectora-company/issues` (público) ou Crisp (billing, privado).

**`/support`**: 4 canais — WhatsApp · Email `support@` · GitHub Issues · Status page.

### P7 — Páginas legais

`/privacy`, `/terms`, `/cookies`, `/sla`, `/dpa` — conteúdo conforme O3. "tldr" no topo, versionadas, mudanças notificadas por email com diff link.

### P8 — i18n + SEO + Performance

**i18n**: Paraglide JS — 7 idiomas: `pt` (padrão), `en`, `es`, `fr`, `it`, `de`, `ru`. Sem sub-códigos. Compile-time, type-safe. Strings em `messages/{locale}.json`. TanStack Router gerencia o segmento de locale na URL.

**SEO**: TanStack Start gera SSR completo — HTML renderizado no servidor sem JavaScript necessário para crawlers. Meta tags via `route.head()`.

- Open Graph completo por página (título, descrição, OG image 1200×630 via edge fn Satori).
- Twitter Cards `summary_large_image`.
- `sitemap.xml` + `robots.txt`. Dashboard bloqueado (`Disallow: /dashboard/`).
- Schema.org JSON-LD: `SoftwareApplication`, `Organization`, `FAQPage`, `Product`.
- Canonical tags + hreflang para todos os 7 idiomas: pt · en · es · fr · it · de · ru.

**Performance**:

- Lighthouse ≥ 95 em Performance/Accessibility/Best Practices/SEO.
- Imagens AVIF/WebP. GIFs com `loading="lazy" decoding="async"` e placeholder skeleton.
- Font subset: Aeonik Mono Latin (já em `public/fonts/`).
- Code splitting automático por rota.

**Analytics**: Plausible self-hosted em `analytics.vectora.company` + GA4. Events: `signup`, `trial_started`, `paid_conversion`, `cancel`, `gif_viewed`, `pricing_viewed`, `waitlist_join`.

### Verificação (Bloco P)

- Landing carrega com GIF hero. Lighthouse ≥ 95.
- Signup BR → dashboard com token + status trial + opções Asaas (PIX/Boleto/Cartão).
- Signup INTL → dashboard com Stripe Checkout em USD.
- Token reveal: aparece uma vez; segunda visita → "já revelado".
- Rotacionar token → novo token exibido uma única vez.
- Assinar Plus BR via PIX → webhook `PAYMENT_RECEIVED` → status "ativo" sem refresh manual (Realtime).
- Upgrade Plus→Pro → tier atualizado com crédito proporcional.
- Cancelar → status "canceled", acesso até fim do período pago.
- FAQ, Issues, Support, Legal acessíveis sem auth.
- 7 idiomas disponíveis via LocaleSwitcher → URL muda, interface traduzida, erros de auth mapeados para Paraglide.
- Exportar dados GDPR → ZIP com JSON completo.
- Deletar conta → confirmação por email + soft delete + hard delete em 30d.
- SSR validado: `curl https://vectora.company` retorna HTML completo com meta tags e json-ld — sem JavaScript.

---

## BLOCO Q — Documentação `docs.vectora.company`

> **Stack**: Docusaurus 3 + customização visual alinhada ao site P (paleta navy + azul claro, Aeonik Mono). Repo público: `vectora-company/docs`.

### Q1 — Setup + tema + i18n

- Docusaurus 3 com `@docusaurus/theme-classic`.
- i18n: `pt` (padrão) + `en`.
- Algolia DocSearch (free para open source docs).
- Theme switcher dark/light.
- Sidebar navegável com auto-collapse + breadcrumbs.
- Versionamento de docs por release major (`/v1.x/...`).

### Q2 — Getting Started

```
getting-started/
├── introduction
├── installation
├── quick-start
├── vectora-token
├── first-workspace
└── upgrade-from-cli
```

Cada página: intro 1 parágrafo, pré-requisitos, passos numerados, resultado esperado, troubleshooting.

### Q3 — Guides

```
guides/
├── vps-deploy
├── team-setup
├── rag-guide
├── mcp-integration
├── git-workflows
├── api-keys
├── webhooks
├── sdk-python
├── sdk-typescript
├── ide-integration
├── github-actions
├── n8n-workflows
└── data-migration
```

### Q4 — Reference

```
reference/
├── cli
├── config
├── tools
├── agents
├── rest-api            (auto-gerado via redocly a partir do OpenAPI 3.1)
├── mcp-server
├── acp-server
└── storage-backends
```

### Q5 — Self-hosting

```
self-hosting/
├── requirements
├── docker
├── kubernetes
├── nginx-traefik
├── storage-backends
├── monitoring
├── backup-restore
└── updates
```

### Q6 — Changelog público + RSS

Página `/changelog`: versão, data, novidades, bugfixes, breaking changes com migration guide. RSS em `docs.vectora.company/changelog/rss.xml`. Webhook `release.published` para integradores.

### Q7 — Padrões de qualidade

- Toda página: intro, pré-requisitos, passos numerados, resultado esperado, troubleshooting.
- Exemplos com output esperado.
- Screenshots/GIFs gerados via Playwright (`docs/scripts/screenshots/`).
- `pt` primário, `en` como tradução.

### Verificação (Bloco Q)

- `docs.vectora.company` com HTTPS verde.
- Algolia DocSearch retorna resultados em ≤300ms.
- Quick-start funciona do zero em 10 min.
- Docker Compose da doc funciona em Ubuntu 24.04 limpo.
- Trocar idioma preserva a página atual.
- Changelog RSS válido (W3C feed validator).

---

## BLOCO R — Suporte & Comunidade

### R1 — WhatsApp Business

- Link no site, docs e dashboard (Settings → Suporte).
- Horário explícito: seg–sex 9h–18h BRT.
- Auto-resposta fora do horário com link para FAQ e issues.
- Templates aprovados para outbound (expiração, upgrade) com opt-in no dashboard.

### R2 — Email `support@vectora.company`

- SLA: ≤48h úteis (Plus), ≤24h úteis (Pro).
- Crisp (PT-BR friendly, free generoso) ou Freshdesk para ticketing.
- 8 templates iniciais: trial estendido, refund, license issue, install trouble, billing dispute, GDPR request, feature request, bug report.

### R3 — GitHub Issues público

Repo `vectora-company/issues`: templates (bug, feature, docs), labels, triagem semanal, auto-assign via GitHub Actions.

### R4 — Comunidade

**MVP**: GitHub Discussions em `vectora-company/issues/discussions`. Categorias: Announcements · Ideas · Q&A · Show and tell · Help. Bruno responde Q&A 2×/semana.

**Discord** (pós-lançamento se ≥500 usuários): canais `#announcements`, `#general`, `#support`, `#show-and-tell`, `#pt-br`, `#en`. Webhooks de releases em `#announcements`.

### R5 — Programa de beta testers

10–20 betas recrutados via Discord LangChain BR, Telegram Python BR, LinkedIn. Acesso Pro gratuito por 6 meses em troca de feedback mensal estruturado (NPS, top 3 positivos, top 3 problemas). Calls 1:1 opcionais. Depoimentos coletados com consent para o site. Hall of Fame com avatar/nome/empresa.

### R6 — Status page (`status.vectora.company`)

BetterStack Uptime ou Upptime. Componentes: API REST · Chat SSE · Validate License Supabase · Site · Docs · Update server. Check interval: 60s. Histórico de 90 dias. Subscribe via email, RSS, webhook.

### R7 — Knowledge base interna

`ops/` (repo privado): `runbooks/` (incidentes), `macros/` (templates de resposta), `weekly-checklist.md`, `monthly-review.md`.

### Verificação (Bloco R)

- WhatsApp Business com perfil + auto-resposta + 5 templates aprovados.
- Email `support@` funcionando, Crisp/Freshdesk configurado, 8 templates prontos.
- GitHub Issues com 3 templates + labels + auto-assign rodando.
- GitHub Discussions com 5 categorias + welcome post pinned.
- ≥10 beta testers recrutados com feedback inicial coletado.
- Status page no ar com 6 componentes; primeiro incidente teste documentado.

---

## BLOCO S — Marketing & Lançamento

> **Pré-requisito**: blocos O–R prontos + produto estável + ≥10 betas com depoimentos.

### S1 — Releases oficiais

- **PyPI** `vectora-cli 1.0.0` com README, badges e classifiers corretos.
- **Docker Hub + GHCR** `vectora/vectora:1.0.0` multi-arch (amd64 + arm64), scanning Trivy verde.
- **GitHub Releases** `v1.0.0` privado: binários assinados (Win .msi + .exe NSIS, macOS .dmg universal, Linux .AppImage + .deb + .rpm), checksums SHA-512, release notes PT-BR + EN.

### S2 — Kit para influenciadores

Enviado com 1–2 semanas de antecedência. Conteúdo: licença Pro por 6 meses, guia de instalação 1 página PDF, 5 sugestões de demo prontas, pasta de assets (logo SVG/PNG, screenshots, banner YouTube, GIF), contato direto Bruno, cupom de tracking por canal.

**Canais BR**: TecMundo · Loop Infinito · Código Fonte TV · Lucas Montano · Mano Deyvin · Filipe Deschamps · Augusto Galego · Computaria · Programador BR.

**Canais INTL (Fase 2)**: Fireship · AI Jason · Theo t3.gg · r/selfhosted · r/LocalLLaMA · Hacker News.

### S3 — Posts de lançamento

LinkedIn (perfil Bruno): 3 posts pré-lançamento (T-14, T-7, T-0) + posts diários T+1 a T+7. Reddit (r/selfhosted, r/LocalLLaMA, r/Python, r/SaaS). X thread de lançamento com GIF. Hacker News "Show HN" terça/quarta 9h ET. Indie Hackers post detalhado.

### S4 — Canal YouTube

4 vídeos (editor contratado ~R$2k): trailer oficial (60–90s) · tutorial completo (15–20 min) · demos de casos de uso (5–10 min cada) · behind the scenes (5 min). Publicação simultânea YouTube + LinkedIn Video + cortes para Shorts/Reels.

### S5 — Cronograma

```
T-30: recrutar beta testers (≥10 confirmados)
T-21: enviar kits para influenciadores BR
T-14: trailer e tutorial finalizados; LinkedIn post 1
T-10: site (P) + docs (Q) no ar
T-7 : LinkedIn post 2; status page com 1 semana de uptime
T-3 : smoke tests finais
T-0 : 🚀 Lançamento
       06h BRT — posts LinkedIn + Reddit + HN + Twitter
       09h BRT — email para mailing list
       12h BRT — trailer YouTube
       14h BRT — WhatsApp blast
T+1–7  : métricas, suporte, hot-fixes
T+14   : Fase 2 canais internacionais
T+30   : retro do lançamento
```

### S6 — Métricas de sucesso

**Meta conservadora (semana 1)**: 500+ instalações · 100+ contas · 50+ trials · 10+ pagantes.

**Meta otimista (semana 1)**: 2.000+ instalações · 500+ contas · 200+ trials · 50+ pagantes.

**Indicadores de qualidade**: conversão trial→pago ≥5% · churn ≤20% em 30d · NPS ≥50 · stars GitHub · tráfego ≥5k visits/semana após T+30.

**Dashboard**: Plausible · Supabase Dashboard · Stripe/Asaas · BetterStack · Sentry.

### S7 — Conteúdo pós-lançamento (semanas 2–8)

Série "Casos de uso do Vectora" — 1 post/vídeo por semana: RAG sobre codebase legado · code review automatizado · equipe de 3 devs · Vectora + Claude Code via MCP · Vectora + n8n · self-hosting em VPS R$30/mês · VS Code extension · Vectora como sub-agente ACP no Zed.

### S8 — Cupons early adopter

- `VECTORA25` — 25% off para primeiros 100 assinantes Plus (`duration: forever`).
- `PROEARLY` — ~18% off para primeiros 50 assinantes Pro (`duration: forever`).
- `MONTANO25` e variantes por canal para tracking de conversão.
- `max_redemptions` configurado no Stripe e Asaas.

### S9 — Roadmap público (`/roadmap`)

Página no site com 4 seções (✓ Lançado · 🚧 Em desenvolvimento · 📍 Planejado) em linguagem de usuário. Updates via blog post + email mensal. Voting via emoji reactions no GitHub Discussions.

### Verificação (Bloco S)

- PyPI `vectora-cli 1.0.0` publicado; `pip install` em VM limpa funciona.
- Docker `vectora/vectora:1.0.0` testado em Ubuntu 24.04 + macOS Docker Desktop.
- GitHub Release `v1.0.0` com 6 binários assinados + checksums + release notes bilíngue.
- Kit enviado para todos os canais BR com ≥2 semanas de antecedência; ≥5 confirmaram publicar.
- Posts LinkedIn/Reddit/HN/Twitter publicados conforme cronograma.
- Trailer finalizado no YouTube com thumbnail.
- ≥10 assinantes pagantes na semana 1.
- Cupons early adopter ativos e rastreáveis.
- `/roadmap` publicado com ≥4 seções e ≥10 itens.

---

## Verificação end-to-end (Company)

- **O**: CNPJ ativo, conta PJ, domínios + emails operacionais, termos publicados.
- **P**: signup → dashboard → token reveal → assinar Plus BR via PIX → status ativo sem refresh. Lighthouse ≥ 95. Prerender validado para Googlebot.
- **Q**: `docs.vectora.company` no ar; quick-start em 10 min em VM limpa.
- **R**: status page com 6 componentes, ≥10 betas com NPS, todos os canais de suporte operacionais.
- **S**: PyPI 1.0 + Docker + Release nativo publicados; ≥5 influenciadores BR confirmados; ≥10 pagantes na semana 1.
