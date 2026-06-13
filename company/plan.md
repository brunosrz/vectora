# Vectora Company — Plano do Site `vectora.company`

> Repo separado do monorepo Vectora: `vectora-company`.
> Stack: **TanStack Start** (meta-framework full-stack sobre Vite + TanStack Router).

---

## Stack

| Camada         | Tecnologia                                                       | Decisão                                                                                      |
| -------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Meta-framework | **TanStack Start**                                               | SSR real, `createServerFn()` nativa, Nitro como runtime — elimina edge functions para auth   |
| Build          | **Vite 6** (embutido no Start)                                   | HMR, bundle mínimo, base do Start                                                            |
| Roteamento     | **TanStack Router** (file-based)                                 | Type-safe, `beforeLoad` para auth guard, `route.head()` para SSR de meta tags                |
| Data fetching  | **TanStack Query**                                               | Cache server+client, stale-while-revalidate, mutations — cobre 90% das chamadas de rede      |
| Server         | **`createServerFn()`** (TanStack Start)                          | Auth, token, subscription, API keys, GDPR — tudo no servidor, sem exposição de service role  |
| Estado global  | **Zustand**                                                      | Apenas `session: User \| null` espelhado do `onAuthStateChange` — UI state, não server state |
| UI primitives  | **Radix UI**                                                     | Acessibilidade, sem estilos opinativos                                                       |
| Estilos        | **Tailwind CSS v4**                                              | Utilitário, paleta custom da marca                                                           |
| Backend/Auth   | **Supabase** (Auth + Postgres + Realtime + Storage + Edge Fns)   | Auth com cookies via `@supabase/ssr`, Realtime para `license_status`, Storage para exports   |
| Anti-spam      | **Cloudflare Turnstile**                                         | Signup, issues, waitlist — não em login                                                      |
| Email          | **React Email + Resend**                                         | Templates transacionais tipados, disparo via server fns e Edge Functions                     |
| i18n           | **Paraglide JS** (`@inlang/paraglide-js`)                        | Já presente no repo (`project.inlang/`), compile-time, type-safe, 7 idiomas                  |
| Analytics      | **Plausible** (self-hosted) + **GA4**                            | Já presentes em `src/lib/analytics/` — Plausible GDPR-compliant, GA4 para funil de conversão |
| Deploy         | **Vercel** (adapter `@tanstack/start-vercel`)                    | SSR com Node runtime, preview deployments por branch, `vercel.json` já configurado           |
| Qualidade      | **TypeScript estrito + oxlint + Prettier + Vitest + Playwright** | Padrão vinculante — `pnpm tsc --noEmit` e `oxlint` verdes no pre-commit                      |
| Validação      | **Zod**                                                          | Todos os inputs de server fns validados antes de tocar o Supabase                            |

### Papéis de cada camada (regra inviolável)

**TanStack Query** é a única camada de dados no cliente. Nenhum `fetch` nu em componentes — toda chamada de rede vive em `useQuery`/`useMutation` definidos em `src/hooks/`. Dados do servidor ficam no cache do Query; Zustand não armazena dados de servidor.

**`createServerFn()`** executa no servidor (Nitro). Usa `createSupabaseServerClient()` com cookies — nunca expõe a `SUPABASE_SERVICE_ROLE_KEY` ao cliente. Operações que exigem `adminClient` (service role) ficam exclusivamente em server fns.

**Supabase Edge Functions** ficam reservadas para: webhooks externos (Stripe, Asaas), `on-signup` trigger, `rotate-token`, `create-checkout`, `create-portal`, `cron-hard-delete` — operações que precisam rodar fora do contexto de uma request HTTP do usuário ou que são chamadas por sistemas externos.

---

## Estrutura do repositório

```
vectora-company/
├── app.config.ts                  ← TanStack Start config (SSR, Vite plugins, adapters)
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── tsr.config.json                ← TanStack Router codegen config ✓ já existe
├── vercel.json                    ✓ já existe
├── prettier.config.js             ✓ já existe
├── eslint.config.js               ✓ já existe
├── instrument.server.mjs          ✓ já existe (Sentry)
├── .cta.json                      ✓ já existe (CTA config)
│
├── public/
│   ├── favicon-*.png, vectora.svg ✓ já existem
│   ├── fonts/aeonikmono-*.otf     ✓ já existem
│   ├── robots.txt                 ✓ já existe
│   ├── gifs/
│   │   ├── showcase-chat.gif      [PLACEHOLDER durante dev]
│   │   ├── showcase-rag.gif       [PLACEHOLDER durante dev]
│   │   ├── showcase-code.gif      [PLACEHOLDER durante dev]
│   │   ├── showcase-plan.gif      [PLACEHOLDER durante dev]
│   │   ├── setup-root.gif         [PLACEHOLDER durante dev]
│   │   ├── setup-invite.gif       [PLACEHOLDER durante dev]
│   │   └── setup-project.gif      [PLACEHOLDER durante dev]
│   └── diagrams/
│       ├── agentic-flow.svg
│       └── rag-flow.svg
│
├── messages/                      ✓ já existem (7 idiomas: pt, en, es, fr, it, de, ru)
│   └── pt.json  en.json  es.json  fr.json  it.json  de.json  ru.json
│
├── project.inlang/                ✓ já existe (Paraglide config)
│
├── src/
│   ├── router.tsx                 ✓ já existe — createRouter()
│   ├── styles.css                 ✓ já existe
│   │
│   ├── routes/
│   │   ├── __root.tsx             ← shell HTML + Head meta + analytics inject + locale
│   │   ├── index.tsx              ← Landing (SSR)
│   │   ├── pricing.tsx            ← Pricing dedicado (SSR)
│   │   ├── faq.tsx                ← FAQ accordion (SSR)
│   │   ├── support.tsx            ← Canais de suporte (SSR)
│   │   ├── issues.tsx             ← Formulário + Turnstile (SSR)
│   │   ├── privacy.tsx            ← MDX estático
│   │   ├── terms.tsx
│   │   ├── cookies.tsx
│   │   ├── sla.tsx
│   │   ├── dpa.tsx
│   │   ├── signup.tsx             ← beforeLoad: redirect /dashboard se logado
│   │   ├── login.tsx              ← beforeLoad: redirect /dashboard se logado
│   │   └── dashboard/
│   │       ├── route.tsx          ← beforeLoad: auth guard; onMount: Realtime
│   │       ├── index.tsx          ← Token reveal (rota padrão)
│   │       ├── license.tsx        ← Status da licença
│   │       ├── billing.tsx        ← Checkout / portal Asaas + Stripe
│   │       ├── api-keys.tsx       ← CRUD de API keys
│   │       └── account.tsx        ← Perfil, senha, GDPR
│   │
│   ├── components/
│   │   ├── landing/
│   │   │   ├── Hero.tsx
│   │   │   ├── ShowcaseGifs.tsx
│   │   │   │   └── ShowcaseCard.tsx
│   │   │   ├── AgenticFlowSection.tsx
│   │   │   │   └── AgenticDiagram.tsx       ← SVG inline /public/diagrams/agentic-flow.svg
│   │   │   ├── RagFlowSection.tsx
│   │   │   │   └── RagDiagram.tsx           ← SVG inline /public/diagrams/rag-flow.svg
│   │   │   ├── TeamSetupSection.tsx
│   │   │   │   ├── SetupTimeline.tsx
│   │   │   │   └── TimelineStep.tsx
│   │   │   ├── WhySelfHosted.tsx
│   │   │   ├── PricingSection.tsx
│   │   │   │   └── PricingTable.tsx
│   │   │   └── WaitlistCta.tsx
│   │   │       └── WaitlistForm.tsx
│   │   ├── dashboard/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── TokenReveal.tsx
│   │   │   ├── LicenseStatus.tsx
│   │   │   ├── BillingSection.tsx
│   │   │   ├── ApiKeysList.tsx
│   │   │   │   └── CreateKeyModal.tsx
│   │   │   └── AccountSection.tsx
│   │   └── shared/
│   │       ├── Header.tsx
│   │       ├── Footer.tsx
│   │       ├── LocaleSwitcher.tsx             ✓ já existe
│   │       ├── Turnstile.tsx
│   │       ├── FaqAccordion.tsx
│   │       └── LegalPage.tsx
│   │
│   ├── server/
│   │   └── fns/                              ← createServerFn() — todas as operações servidor
│   │       ├── auth.ts                       (getSession, signUp, signIn, signOut, sendMagicLink)
│   │       ├── token.ts                      (getToken, rotateToken, getTokenStatus)
│   │       ├── subscription.ts               (getSubscription, createCheckout, createPortal)
│   │       ├── api-keys.ts                   (listApiKeys, createApiKey, revokeApiKey)
│   │       ├── gdpr.ts                       (exportData, requestAccountDeletion)
│   │       └── issues.ts                     (submitIssue)
│   │
│   ├── hooks/
│   │   ├── use-session.ts
│   │   ├── use-subscription.ts
│   │   └── use-api-keys.ts
│   │
│   ├── store/
│   │   └── auth.ts                           ← Zustand: session espelhada do Supabase listener
│   │
│   ├── integrations/
│   │   └── tanstack-query/
│   │       ├── root-provider.tsx             ✓ já existe
│   │       └── devtools.tsx                  ✓ já existe
│   │
│   └── lib/
│       ├── supabase/
│       │   ├── client.ts                     ✓ já existe (browser)
│       │   ├── server.ts                     ✓ já existe (SSR com cookies)
│       │   ├── admin.ts                      ✓ já existe (service role — server fns only)
│       │   └── types.ts                      ✓ já existe (gerado via supabase gen types)
│       ├── analytics/
│       │   ├── plausible.ts                  ✓ já existe
│       │   └── ga4.ts                        ✓ já existe
│       ├── email/
│       │   └── resend.ts                     ✓ já existe
│       ├── turnstile.ts                      ✓ já existe
│       └── leads.ts                          ✓ já existe (waitlist — já implementado)
│
├── emails/                                   ← React Email templates
│   ├── welcome.tsx
│   ├── trial-ending-7d.tsx
│   ├── trial-ending-1d.tsx
│   ├── invoice-paid.tsx
│   ├── invoice-failed.tsx
│   ├── magic-link.tsx
│   ├── account-deleted.tsx
│   └── waitlist-confirmation.tsx             ✓ já implementado via leads.ts
│
├── supabase/
│   ├── config.toml                           ✓ já existe
│   ├── migrations/                           ← schema completo (ver P — Banco de Dados)
│   └── functions/
│       ├── on-signup/                        ← trigger: cria profile + token + subscription
│       ├── validate-license/                 ← chamado pelo Vectora Agent a cada 6h
│       ├── rotate-token/                     ← gera novo raw + hash, compare-and-swap
│       ├── create-checkout/                  ← Asaas (BR) ou Stripe (INTL)
│       ├── create-portal/                    ← Stripe Customer Portal URL
│       ├── webhooks/                         ← Asaas PAYMENT_RECEIVED + Stripe invoice.*
│       └── cron-hard-delete/                 ← pg_cron diário: hard delete após 30d
│
└── tests/
    ├── unit/                                 ← Vitest
    └── e2e/                                  ← Playwright
```

---

## Padrões de engenharia (Company-specific)

Os padrões gerais do Vectora (comentários, i18n, TDD, nomenclatura, async-first, etc.) aplicam-se integralmente. Adicionalmente:

**Server fns com Zod obrigatório.** Todo input de `createServerFn()` passa por `schema.parse()` antes de qualquer operação. Falha de parse lança erro que o TanStack Router trata como resposta 400 — nunca chega ao Supabase.

**`adminClient` exclusivamente em server fns.** A `SUPABASE_SERVICE_ROLE_KEY` não é acessível no cliente. Qualquer operação que exija service role (reveal de token, export de dados, hard delete) é `createServerFn()` — nunca Edge Function chamada diretamente do browser.

**State ephemeral nunca persiste.** Token raw e api-key secret vivem apenas em `useState` local — não entram no cache do TanStack Query, não entram no Zustand, não entram em `localStorage`. Limpar ao navegar ou fechar modal.

**Rotas autenticadas com `noindex`.** Todo `dashboard/*` tem `<meta name="robots" content="noindex, nofollow">` via `route.head()` e está bloqueado em `robots.txt` (`Disallow: /dashboard/`).

**Realtime Supabase apenas no dashboard layout.** Canal `license_status` montado em `dashboard/route.tsx`, cancelado no cleanup — nunca em componentes folha.

**i18n em todos os 7 idiomas.** Strings de erro do Supabase Auth (`Invalid login credentials`, etc.) nunca são exibidas cruas — sempre mapeadas para chaves Paraglide antes de chegar ao usuário.

**`rotate-token` com compare-and-swap.** A Edge Function `rotate-token` executa `UPDATE tokens SET token = $new WHERE token_hash = $old_hash` — se 0 rows afetadas, retorna erro "token já rotacionado". O botão fica desabilitado via `isPending` do `useMutation` durante a operação.

**`exportData` via Supabase Storage.** Nunca retornar blob diretamente de server fn. O fluxo: gera ZIP no servidor → salva em Supabase Storage com URL assinada (TTL: 5 min) → retorna `{ url }` → cliente abre via `<a href download>`.

**`cron-hard-delete` cancela subscriptions antes de deletar.** Ordem: 1. cancelar no Stripe/Asaas via API, 2. DELETE em `auth.users` via adminClient, 3. DELETE em cascade nas tabelas filhas. Nunca deletar da auth sem cancelar billing antes.

---

## BLOCO O — Identidade & Legal

> Pré-requisito absoluto. Sem CNPJ ativo e termos publicados, Stripe e Asaas bloqueiam produção.

### O1 — Estrutura jurídica

- Abrir MEI via `gov.br/mei`. CNAE 6201-5/01 (principal) + 6202-3/00 (secundário). Migrar para ME se faturamento ultrapassar R$81k/ano.
- Conta bancária PJ: Nubank PJ, Inter PJ ou C6 PJ — zero tarifa, abertura digital, integração Stripe via transferência internacional.
- Inscrição municipal para NFS-e se exigida pela prefeitura local.
- Passo a passo documentado em `ops/setup-mei.md`.

### O2 — Marca e domínios

**Domínio principal adquirido**: `vectora.company`.

| Subdomínio                  | Uso                                   |
| --------------------------- | ------------------------------------- |
| `vectora.company`           | Site institucional (P)                |
| `docs.vectora.company`      | Documentação pública (Q)              |
| `api.vectora.company`       | REST API pública (Bloco J do Vectora) |
| `status.vectora.company`    | Status page (R6)                      |
| `updates.vectora.company`   | Channel server auto-update            |
| `analytics.vectora.company` | Plausible self-hosted                 |

**Domínios adicionais (defesa de marca)**: `vectora.dev`, `vectora.com.br`, variantes typo redirecionando para o principal.

**Identidade visual**: pássaro Vectora navy + azul claro, Aeonik Mono (já presente em `public/fonts/`), paleta `#0a0e1a` / `#3b82f6`. Assets centralizados em `brand/`: SVG vetorial, PNGs multi-res, dark/light variants, favicon kit (`public/` já populado), OG cards 1200×630.

**Registro INPI**: Classe 9 + Classe 42. Recomendado após 6 meses do lançamento quando houver receita para justificar (~R$1.500 por classe).

### O3 — Termos legais (LGPD + GDPR-ready)

Todos os documentos em MDX estático, versionados no git, com "tldr" no topo. Revisão por advogado SaaS antes do lançamento (~R$2.000–R$5.000).

**Política de Privacidade** (`/privacy`): dados coletados (email, nome, logs de token, pagamento via gateway — cartão nunca armazenado, IP + user_agent no audit log); dados que não coletamos (conversas, arquivos, embeddings — self-hosted); base legal LGPD Art. 7º I e V; retenção (conta: vigência + 30d; logs de licença: 90d; dados fiscais: 5 anos); DPO `dpo@vectora.company`.

**Termos de Uso / EULA** (`/terms`): licença não exclusiva e não transferível; trial 30 dias sem cartão; cancelamento a qualquer momento com acesso até fim do período pago; limitação de responsabilidade ("as is"); reembolso em 14 dias após primeira cobrança real; foro São João Batista do Glória/MG.

**Cookies Policy** (`/cookies`): apenas 3 cookies essenciais (`vectora_access`, `vectora_refresh`, `vectora_lang`); sem tracking; botão "Limpar cookies" funcional.

**SLA** (`/sla`): uptime ≥ 99.5% mensal para `validate-license`; latência p95 < 500ms; crédito de 10% por 0.5% abaixo do target. Apenas Pro/Enterprise.

**DPA** (`/dpa`): template EU DPA padrão ICC para Enterprise.

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
| `noreply@vectora.company`  | Outbound transacional (Resend)       |

DKIM/SPF/DMARC configurados. WhatsApp Business com auto-resposta fora do horário (seg–sex 9h–18h BRT).

**GitHub Organization** `vectora-company`: repos públicos (`docs`, `examples`, `issues`, `homebrew-tap`, `mcp-server-vectora`); repos privados (`vectora`, `site`, `supabase`, `brand`, `ops`). 2FA obrigatório, branch protection em `main`, Dependabot ativo.

### Verificação (Bloco O)

- MEI/ME com CNPJ ativo; emite NFS-e.
- Conta PJ operacional, recebe transferências.
- `vectora.company` e todos os subdomínios resolvendo com HTTPS.
- SPF/DKIM/DMARC com status `pass` no mxtoolbox.
- Privacy, Terms, Cookies, SLA, DPA publicados e revisados por advogado.
- GitHub Org criada com branch protection ativa em todos os repos.
- WhatsApp Business com perfil completo e auto-resposta configurada.

---

## BLOCO P — Site `vectora.company`

### P — Banco de Dados (Supabase schema)

Schema completo via migrations em `supabase/migrations/`. Todas as tabelas com RLS ativa; `adminClient` (service role) é a única forma de bypassar RLS — exclusivamente em server fns e Edge Functions.

```sql
-- profiles: criada pelo trigger on-signup
profiles (
  id          uuid PRIMARY KEY REFERENCES auth.users,
  full_name   text,
  country     text,                          -- 'BR' | 'INTL'
  language    text DEFAULT 'pt',
  soft_delete_at timestamptz,
  created_at  timestamptz DEFAULT now()
)

-- tokens: VECTORA_TOKEN — show-once
tokens (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid REFERENCES profiles,
  token       text,                          -- null após reveal (show-once)
  token_hash  text NOT NULL,                 -- sha256 do raw — para validate-license
  created_at  timestamptz DEFAULT now()
)

-- subscriptions
subscriptions (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid REFERENCES profiles,
  tier            text NOT NULL,             -- 'plus' | 'pro'
  status          text NOT NULL,             -- 'trialing' | 'active' | 'past_due' | 'canceled' | 'expired'
  provider        text,                      -- 'stripe' | 'asaas'
  provider_sub_id text,
  trial_ends_at   timestamptz,
  current_period_end timestamptz,
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now()
)

-- license_checks: log de validações do Vectora Agent
license_checks (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid REFERENCES profiles,
  vectora_version text,
  result      text,                          -- 'valid' | 'invalid' | 'expired'
  ip          text,
  created_at  timestamptz DEFAULT now()
)

-- payment_events: histórico de cobranças
payment_events (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid REFERENCES profiles,
  provider    text,
  event_type  text,
  amount      numeric,
  currency    text,
  metadata    jsonb,
  created_at  timestamptz DEFAULT now()
)

-- api_keys: chaves OAuth para REST API
api_keys (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid REFERENCES profiles,
  name        text NOT NULL,
  key_hash    text NOT NULL,                 -- sha256 do raw — show-once
  scopes      text[] DEFAULT '{}',
  last_used_at timestamptz,
  created_at  timestamptz DEFAULT now()
)

-- waitlist: já implementado via leads.ts
waitlist (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email       text UNIQUE NOT NULL,
  source      text,
  created_at  timestamptz DEFAULT now()
)

-- issues: reportes públicos
issues (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title       text NOT NULL,
  category    text NOT NULL,                 -- 'bug' | 'feedback' | 'feature'
  description text,
  email       text,
  created_at  timestamptz DEFAULT now()
)
```

**Supabase Realtime**: canal `license_status` configurado para a tabela `subscriptions` com filtro `user_id=eq.{uid}`. Ativo apenas enquanto o dashboard layout está montado.

**Supabase Storage**: bucket `exports` (privado) para ZIPs do GDPR export. URLs assinadas com TTL de 5 minutos.

### P — Árvore de rotas

```
src/routes/
├── __root.tsx          ← shell HTML: <html lang> + Head meta + analytics inject
│                          beforeLoad: set locale (Paraglide), inject Plausible + GA4
│                          Layout: <Header /> + {children} + <Footer />
│
├── index.tsx           ← Landing (SSR)
├── pricing.tsx         ← Pricing dedicado (SSR)
├── faq.tsx             ← FAQ accordion (SSR, json-ld FAQPage)
├── support.tsx         ← Canais de suporte (SSR)
├── issues.tsx          ← Formulário + Turnstile (SSR)
│
├── privacy.tsx         ← MDX estático
├── terms.tsx
├── cookies.tsx
├── sla.tsx
├── dpa.tsx
│
├── signup.tsx          ← beforeLoad: getSession() → redirect /dashboard se logado
├── login.tsx           ← beforeLoad: getSession() → redirect /dashboard se logado
│
└── dashboard/
    ├── route.tsx       ← beforeLoad: getSession() → null → redirect '/login?redirect='
    │                      onMount: subscrever Realtime 'license_status'
    │                      onUnmount: canal.unsubscribe()
    │                      Layout: <Sidebar /> + <main>{children}</main>
    │                      head: noindex, nofollow
    ├── index.tsx       ← Token reveal (rota padrão)
    ├── license.tsx     ← Status da licença + histórico de validações
    ├── billing.tsx     ← Checkout Asaas (BR) / Stripe (INTL) + portal
    ├── api-keys.tsx    ← CRUD de API keys
    └── account.tsx     ← Perfil, senha, GDPR (export + delete)
```

### P1 — Landing Page (`/`)

Scroll único, seções âncora, mobile-first. Animações de entrada via Intersection Observer (`threshold: 0.15`, fade-in + slide-up leve). `prefers-reduced-motion`: sem animação, conteúdo já visível. Separadores entre seções via espaçamento generoso (`py-24` desktop, `py-16` mobile) com alternância de background (transparente · brand-tint · transparente · brand-tint) — sem `<hr>`.

**Seções em ordem**:

```
<LandingPage>
  <Hero />
  <ShowcaseGifs />
  <AgenticFlowSection />
  <RagFlowSection />
  <TeamSetupSection />
  <WhySelfHosted />
  <PricingSection />
  <WaitlistCta />        ← pré-lançamento (VITE_LAUNCH_MODE=waitlist)
                            substituir por <FinalCta /> após launch
```

#### Hero

```
elementos:
  Eyebrow badge: "Self-hosted · Privacy-first · Open core"
    pill com ícone de cadeado, cor brand accent

  H1: m.hero_tagline() — "Your AI. Your Data. Your Server."
    fonte grande, bold, tracking tight
    palavra-chave com gradiente brand

  Subtítulo: m.hero_subtitle()
    1-2 linhas: RAG, MCP, multi-user web chat, never leaves your server

  CTAs (row):
    [Primário]   "Começar trial — 30 dias grátis"  → /signup
    [Secundário] "Ver preços"                        → scroll #pricing

  GIF central:
    Interface do Vectora respondendo pergunta técnica
    bordas arredondadas, sombra com glow brand
    max-width: 860px, aspect-ratio: 16/10
    <img loading="lazy" decoding="async" alt="...">
    placeholder: skeleton shimmer enquanto carrega
    [PLACEHOLDER dev: retângulo 860×537 "GIF showcase-chat"]

layout:
  centralizado, padding vertical generoso
  background: gradiente ou mesh gradient brand
```

#### ShowcaseGifs — "Veja o Vectora em ação"

Grade 2×2 desktop → 1 coluna mobile. Cada `<ShowcaseCard>` tem: GIF/placeholder com borda brand tênue, hover `scale(1.02)` + sombra mais intensa, label bold + descrição `text-sm muted`. `prefers-reduced-motion` → frame estático.

```
[1] Conversação com contexto
    gif: /gifs/showcase-chat.gif
    título: m.showcase_chat_title()
    desc: "Pergunte em linguagem natural — sobre código, documentos,
           planilhas ou qualquer arquivo do seu servidor."

[2] RAG — busca semântica
    gif: /gifs/showcase-rag.gif
    título: m.showcase_rag_title()
    desc: "Indexe qualquer documento. O Vectora encontra a informação
           certa com busca vetorial no Qdrant."

[3] Agente codando
    gif: /gifs/showcase-code.gif
    título: m.showcase_code_title()
    desc: "Do planejamento ao código. O Vectora escreve, refatora e
           explica usando o contexto do seu repositório."

[4] Raciocínio estruturado
    gif: /gifs/showcase-plan.gif
    título: m.showcase_plan_title()
    desc: "Tarefas complexas divididas automaticamente.
           Veja cada passo do raciocínio em tempo real."
```

#### AgenticFlowSection — "Como o Vectora pensa"

Layout 2 colunas desktop (diagrama esquerda, texto direita) → 1 coluna mobile.

```
[coluna esquerda]
  <AgenticDiagram>  ← SVG inline de /public/diagrams/agentic-flow.svg
    nós (fluxo real do LangGraph, versão pública simplificada):
      Usuário
        ↓
      Orchestrator  (centro, maior — decide roteamento)
        ├─→ Coder Agent    (filesystem, terminal, git, implementação)
        ├─→ Search Agent   (web search, RAG, curadoria da base)
        ├─→ RAG Subgraph   (query expansion, hybrid search, reranking)
        └─→ Paralelo       (múltiplos agentes em asyncio.gather)
                ↓
        Resposta consolidada → Usuário

    cores:
      Orchestrator: brand primary (#3b82f6)
      Coder:        brand secondary azul
      Search:       brand secondary roxo
      RAG:          brand secondary verde
      Paralelo:     brand secondary laranja
    arestas: gradiente entre os nós conectados
    prefers-reduced-motion: SVG estático

[coluna direita]
  bullets com ícone:
    ○ Orquestrador decide em tempo real: responder, delegar ou paralelizar
    ○ Coder Agent: arquivos, terminal, git, implementação de código
    ○ Search Agent: web em tempo real, RAG, curadoria da base de conhecimento
    ○ RAG Subgraph: query expansion, reranking, web fallback
    ○ Modo paralelo: múltiplas tarefas em asyncio.gather
  CTA: "Documentação técnica →" → docs.vectora.company
```

#### RagFlowSection — "Seus documentos, acessíveis de qualquer lugar"

Layout texto esquerda, diagrama direita.

```
[coluna esquerda]
  heading: m.rag_heading()
  bullets:
    ○ PDF, DOCX, TXT, Markdown, código-fonte, planilhas
    ○ Embeddings via Cohere (search_document / search_query assimétrico)
    ○ Hybrid RAG: dense (Cohere) + sparse (BM25) com RRF merge
    ○ Multi-query: LLM gera N variantes da query para maior recall
    ○ HyDE: documento hipotético quando score inicial é baixo
    ○ Reranker Cohere para precisão máxima
    ○ Citação da fonte em cada resposta

[coluna direita]
  <RagDiagram>  ← SVG inline de /public/diagrams/rag-flow.svg
    fluxo real do rag_subgraph (simplificado para o público):

    Documento → Chunking → Cohere Embed → LanceDB
                                               ↓
    Query → Multi-query → Hybrid Search → Reranker
                                               ↓
             Score ≥ 0.7 → inject direto
             Score 0.4–0.7 → search_audit → inject
             Score < 0.4  → Web Fallback → search_audit → inject
                                               ↓
                                       LLM + contexto → Resposta + fonte

    labels discretos nas arestas: "chunking", "embed", "top-K", "reranquear"
    cilindro para LanceDB, caixa para LLM
```

#### TeamSetupSection — "Do zero ao time rodando em minutos"

Timeline vertical com 4 passos. Background brand-tint sutil.

```
[1] Deploy da stack
    ícone: Docker
    visual: code block inline (apenas visual, não copiável)
      docker compose up -d
    badges: Vectora · PostgreSQL · Qdrant · Redis
    desc: "Um único arquivo. Sem dependências externas."

[2] Conta root
    ícone: usuário com escudo
    visual: GIF ~400px — tela de first-time setup
    [PLACEHOLDER: "GIF: setup-root.gif"]
    desc: "Acesso administrativo completo ao seu workspace."

[3] Convidar equipe
    ícone: pessoas
    visual: GIF — painel de membros → Convidar → email enviado
    [PLACEHOLDER: "GIF: setup-invite.gif"]
    desc: "Controle de permissões por projeto."

[4] Inicializar projetos
    ícone: pasta com IA
    visual: GIF — criar projeto, adicionar docs, primeiro chat
    [PLACEHOLDER: "GIF: setup-project.gif"]
    desc: "Cada projeto tem sua própria base de conhecimento e histórico."

banner de compatibilidade:
  ícones: PostgreSQL · Qdrant · Redis · Docker
  texto: "Compatível com qualquer VPS Linux — AWS, GCP, Hetzner, DigitalOcean"
```

#### WhySelfHosted

Grade 2×2, 4 cards:

```
[Privacidade]   ícone cadeado
  "Nenhuma conversa, documento ou código é enviado a terceiros.
   Conformidade com LGPD, GDPR e políticas internas."

[Custo]         ícone moeda
  "Preço fixo pela licença Vectora. Custos de LLM sob seu controle —
   use modelos locais gratuitamente."

[Customização]  ícone engrenagem
  "Configure providers de LLM, modelos de embedding, tamanho de chunk,
   prompts de sistema e muito mais."

[Soberania]     ícone servidor
  "Sem lock-in. Sem dependência de cloud. Rode offline se precisar.
   Seu servidor, suas regras."
```

#### PricingSection

```
id="pricing"
heading: m.pricing_heading()
subtítulo: "30 dias de trial grátis. Sem cartão de crédito."

toggle BRL / USD
  default: 'BRL' se navigator.language contém 'pt', senão 'USD'
  apenas visual, sem reload

[card Plus]
  badge: "Para times pequenos"
  BRL: R$20/mês  |  USD: $7/mês
  features:
    ✓ 1 workspace
    ✓ Até 5 membros
    ✓ RAG ilimitado
    ✓ MCP integrations
    ✓ REST API /v1 (60 req/min)
    ✓ SDKs Python/TS
    ✓ Suporte por email (48h)
    — Priority support
    — SSO / SAML
  CTA: "Começar trial grátis" → /signup?plan=plus

[card Pro]
  badge: "Para empresas"  (destaque — borda brand, fundo tint)
  BRL: R$55/mês  |  USD: $20/mês
  features:
    ✓ Workspaces ilimitados
    ✓ Membros ilimitados
    ✓ RAG ilimitado
    ✓ MCP integrations
    ✓ REST API /v1 (600 req/min)
    ✓ SDKs Python/TS
    ✓ Webhooks
    ✓ ACP server
    ✓ Priority support (SLA 24h)
    ✓ SSO / SAML (em breve)
  CTA: "Começar trial grátis" → /signup?plan=pro

tabela comparativa (colapsável "Ver comparação completa"):
  linhas: Storage · Projetos · API Keys · Webhooks · Audit log · SLA
  expand/collapse com animação
```

#### WaitlistCta (pré-lançamento)

```
visível quando: VITE_LAUNCH_MODE=waitlist
background: brand gradient forte

heading: m.waitlist_heading() — "Seja um dos primeiros"
subtítulo: "Trial grátis de 30 dias para quem entrar na lista agora."

<WaitlistForm>
  input: type="email" placeholder="seu@email.com"
  <Turnstile onSuccess(token) → armazena em useState local />
  botão: "Entrar na lista"
  onSubmit:
    → Turnstile não resolvido → desabilitar botão
    → mutation: joinWaitlist({ email, turnstileToken, source: 'landing-cta' })
      → server fn: verifyTurnstile() → addToWaitlist() (já em leads.ts)
    → sucesso: esconde form, mostra "✓ Você está na lista! Verifique seu email."
    → duplicate: "Esse email já está na lista."
    → erro genérico: m.error_generic()

rodapé: "Sem spam. Apenas o aviso de lançamento."
```

### P2 — Páginas públicas

**`pricing.tsx`**: `loader` vazio (dados estáticos). Head: `title "Preços — Vectora"`, `og:image /og-pricing.png`, json-ld `Product` (Plus + Pro). Render: `<PricingSection />` (reusa componente da landing) + `<FaqAccordion items={pricingFaqs} />` + `<WaitlistCta />` ou `<FinalCta />`.

**`faq.tsx`**: Head com json-ld `FAQPage`. Render: heading + `<FaqAccordion>` com 5 categorias (Geral · Instalação · Planos · Segurança · Técnico). Input de busca filtra visualmente sem reload.

**`support.tsx`**: 3 canais — `mailto:support@vectora.company`, link para GitHub Issues, link para docs. SLA por plano (Plus: 48h, Pro: 24h, Trial: community).

**`issues.tsx`**: `<IssueForm>` com campos título, categoria (bug/feedback/feature), descrição, email + `<Turnstile>`. `onSubmit → mutation: submitIssue()`. Toast de sucesso.

**Páginas legais** (`privacy, terms, cookies, sla, dpa`): MDX estático versionado no git. `<LegalPage title="..." lastUpdated="..."><MDXContent /></LegalPage>`. Sumário lateral desktop com âncoras automáticas dos H2; mobile sem sumário.

### P3 — Auth (`/signup`, `/login`)

**`signup.tsx`**:

```
loader: getSession() → se logado → redirect /dashboard

<SignupForm>
  campos: nome completo · email · senha · país (BR / INTL)
  <Turnstile onSuccess(token) />

  onSubmit → signUp({ name, email, password, country, turnstileToken })
    server fn:
      1. schema.parse(input)                         ← Zod
      2. verifyTurnstile(token)                      ← falha → throw
      3. supabase.auth.signUp({ email, password,
           options: { data: { name, country } } })
      4. Supabase trigger on-signup:
           INSERT profiles(id, full_name, country)
           INSERT tokens(user_id, token=raw, token_hash=sha256(raw))
           INSERT subscriptions(tier='plus', status='trialing',
                                trial_ends_at=now()+30d)
      5. retorna { redirect: '/dashboard?welcome=true' }

  link "Já tenho conta" → /login
  link "Ver preços" → /pricing
```

**`login.tsx`**:

```
loader: getSession() → se logado → redirect /dashboard

<LoginForm>
  campos: email · senha
  link "Esqueci a senha" → sendMagicLink(email) → toast "Link enviado"

  onSubmit → signIn({ email, password })
    server fn:
      1. schema.parse(input)
      2. supabase.auth.signInWithPassword({ email, password })
      3. session cookie setado via @supabase/ssr
    sucesso: redirect para ?redirect param ou /dashboard

  link "Criar conta" → /signup
  Erros do Supabase Auth mapeados para chaves Paraglide — nunca string crua
```

### P3.1 — Auth avançada: TOTP, Passkeys e OAuth social (Google/GitHub)

> Camada por cima do Supabase Auth. Ordem de entrega: TOTP → OAuth social →
> escopos estendidos → Passkeys (a mais complexa, sem suporte nativo Supabase).

#### TOTP — Authenticator app (MFA)

Usa o MFA nativo do Supabase (`supabase.auth.mfa.*`):

```
Dashboard → Conta → Segurança → "Ativar autenticação em duas etapas"
  1. enroll({ factorType: 'totp' }) → QR code + secret em texto (fonte mono)
  2. usuário escaneia no authenticator (Google Authenticator, Aegis, 1Password…)
  3. challenge() + verify({ code }) → fator ativado
  4. gerar 10 recovery codes (hash em tabela `mfa_recovery_codes`, show-once)

Login com fator ativo:
  signInWithPassword → AAL1 → tela "Digite o código do app" →
  mfa.challenge + verify → AAL2 → session completa
  link "Usar recovery code" → consome 1 código (marca used_at)

Enforcement:
  - RLS nas tabelas sensíveis exige aal2 quando o usuário tem fator ativo
    (claim `aal` no JWT)
  - server fns de token/billing/api-keys checam aal2 se MFA ativo
Desativar MFA: exige código TOTP válido + senha.
```

#### OAuth social — Login com Google e GitHub

Providers OAuth do Supabase (`signInWithOAuth`). Botões em `/login` e
`/signup` ("Continuar com Google" / "Continuar com GitHub") com `redirectTo`
de volta ao dashboard. Conta social vincula-se à conta email existente pelo
mesmo email verificado (identity linking do Supabase).

```
Login básico (sem escopos extras):
  google: scopes 'openid email profile'
  github: scopes 'read:user user:email'
  → trigger on-signup roda igual (profile + token + subscription trialing)
```

#### Escopos estendidos — Google Drive/Calendar e GitHub repos

Princípio: **consentimento incremental**. O login pede o mínimo; os escopos
extras são solicitados depois, quando o usuário conecta a integração em
Dashboard → Conta → Integrações (e refletido no Vectora Agent via
`/admin/oauth` já existente no backend).

```
Google (incremental consent):
  card "Google Drive & Calendar" → botão "Conectar"
  → signInWithOAuth({ provider: 'google', scopes:
      'https://www.googleapis.com/auth/drive.readonly
       https://www.googleapis.com/auth/calendar.events',
      queryParams: { access_type: 'offline', prompt: 'consent',
                     include_granted_scopes: 'true' } })
  → provider_refresh_token retornado pelo Supabase é persistido CRIPTOGRAFADO
    em `oauth_connections` (service-role only; nunca exposto ao browser)
  → o Vectora Agent obtém access tokens de curta duração via endpoint
    `POST /functions/v1/oauth-token` autenticado pelo VECTORA_TOKEN
    (refresh feito server-side; o agente nunca vê o refresh token)
  usos no agente: RAG sobre Drive (read-only) e tools de agenda (Calendar)

GitHub (commits e PRs em repositórios SELECIONADOS):
  OAuth scopes clássicos ('repo') dão acesso a TODOS os repos — inaceitável.
  Usar **GitHub App** "Vectora" em vez de OAuth app:
    1. card "GitHub — repositórios" → "Instalar o Vectora App"
    2. fluxo de instalação do GitHub mostra a tela nativa
       "Repository access: Only select repositories" → usuário escolhe os repos
    3. permissões do App: contents: write (commits/branches),
       pull_requests: write, issues: write, metadata: read
    4. webhook installation.created/deleted → upsert em `oauth_connections`
       (installation_id por usuário)
    5. agente pede token via `POST /functions/v1/oauth-token` →
       edge function gera installation access token (JWT do App, TTL 1h)
       restrito aos repos instalados
  Revogação: desinstalar o App no GitHub OU botão "Desconectar" no dashboard.

-- tabela nova (migration):
oauth_connections (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid REFERENCES profiles,
  provider      text NOT NULL,             -- 'google' | 'github-app'
  scopes        text[] DEFAULT '{}',
  refresh_token text,                      -- criptografado (pgsodium) — google
  installation_id bigint,                  -- github app
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
)  -- RLS: deny all; service-role only
```

#### Passkeys (WebAuthn)

Supabase Auth ainda não tem passkeys nativas — implementar com
`@simplewebauthn/server` (server fns) + `@simplewebauthn/browser`:

```
Registro (Dashboard → Conta → Segurança → "Adicionar passkey"):
  server fn generateRegistrationOptions(rpID='vectora.company')
  → navigator.credentials.create() → verifyRegistrationResponse
  → INSERT passkey_credentials(user_id, credential_id, public_key,
      counter, transports, device_name)

Login (/login → botão "Entrar com passkey"):
  generateAuthenticationOptions (discoverable credentials / conditional UI)
  → navigator.credentials.get() → verifyAuthenticationResponse
  → sessão emitida via adminClient (generateLink/signInWithIdToken bridge)
  fallback: senha + TOTP

Regras: máx 5 passkeys por conta; remover exige aal2; counter
anti-replay validado a cada login.
```

**Verificação (P3.1)**: TOTP ativa/valida/recovery code funciona; login Google
e GitHub criam conta com trial; conectar Drive pede tela de consent do Google
com escopos extras; instalar o GitHub App mostra seleção de repositórios e o
agente consegue commitar APENAS nos repos selecionados; passkey registra e
loga sem senha em Chrome/Safari/Android; refresh tokens nunca aparecem em
resposta de rede do browser.

### P4 — Dashboard

#### `dashboard/route.tsx` — layout compartilhado

```
beforeLoad:
  getSession() → null → redirect '/login?redirect=' + pathname

head:
  <meta name="robots" content="noindex, nofollow">

onMount:
  canal Realtime Supabase:
    channel: 'license_status'
    table: subscriptions, filter: user_id=eq.{uid}
    onInsert + onUpdate: queryClient.invalidateQueries(['subscription'])

onUnmount: canal.unsubscribe()

render:
  <DashboardLayout>
    <Sidebar>
      items:
        Token       (ícone key)       → /dashboard
        Licença     (ícone shield)    → /dashboard/license
        Pagamento   (ícone card)      → /dashboard/billing
        API Keys    (ícone zap)       → /dashboard/api-keys
        Conta       (ícone user)      → /dashboard/account
        Suporte     (ícone help)      → /support
      item ativo: destacado com brand color
      mobile: bottom tab bar (5 itens + overflow)
    </Sidebar>
    <main>{children}</main>
  </DashboardLayout>
```

#### `dashboard/index.tsx` — TokenReveal

```
loader: getTokenStatus() → { revealed: boolean }

<TokenReveal>
  estado A — nunca revelado (token != null no DB):
    botão "Clique para revelar"
    onReveal → getToken():
      server fn (adminClient):
        SELECT token FROM tokens WHERE user_id = uid
        → token != null:
            UPDATE tokens SET token = null    ← show-once
            retorna { token: string }
        → exibe token em fonte mono + botão copiar
        → warning: "Copie e guarde. Não será exibido novamente."
    onCopy OU onNavigate → limpar token do useState (não persiste no cache)

  estado B — já revelado (token = null no DB):
    banner amarelo: "Token já revelado."
    botão "Rotacionar token" → rotateMutation:
      isPending → botão desabilitado (previne double-click)
      server fn → invokeEdgeFunction('rotate-token'):
        → edge fn: compare-and-swap
            UPDATE tokens SET token=new_raw, token_hash=sha256(new_raw)
            WHERE token_hash = old_hash AND user_id = uid
            → 0 rows → erro "token já rotacionado"
        → retorna { token: string } → exibir (fluxo estado A)

  estado C — welcome=true na URL:
    QuickStart guide acima do token:
      1. Revele e copie seu VECTORA_TOKEN acima
      2. pip install vectora
      3. vectora setup  (cole o token quando solicitado)
      4. vectora chat
```

#### `dashboard/license.tsx` — LicenseStatus

```
data:
  useQuery(['subscription'], getSubscription, { staleTime: 30_000 })
  + invalidação via Realtime (route.tsx)

<LicenseStatus>
  badge de status:
    trialing  → "Trial ativo"          (verde)
    active    → "Ativo"                (verde)
    past_due  → "Pagamento pendente"   (amarelo)
    canceled  → "Cancelado"            (vermelho)
    expired   → "Expirado"             (cinza)

  datas: início · término do trial · dias restantes (countdown)

  CTAs condicionais:
    [trialing]       "Assinar Plus"  +  "Upgrade para Pro"
    [plus/active]    "Upgrade para Pro"  +  "Gerenciar assinatura"
    [pro/active]     "Gerenciar assinatura"
    [past_due]       "Atualizar pagamento"
    [canceled/expired] "Reativar"

<LicenseHistory>
  useQuery(['license-checks'], getLicenseHistory, { staleTime: 5 * 60_000 })
  tabela: data · versão Vectora · resultado · IP (mascarado: primeiros 2 octetos)
```

#### `dashboard/billing.tsx` — BillingSection

```
data: useQuery(['subscription']) → { country, provider, status }

[BR — Asaas]:
  botão "Assinar" ou "Upgrade" →
    mutation: createCheckout({ plan, country: 'BR' })
    server fn → invokeEdgeFunction('create-checkout', { plan, country: 'BR' })
    → retorna { url } → redirect para Asaas Checkout (PIX · Boleto · Cartão)
  após pagamento: Asaas webhook → UPDATE subscriptions → Realtime invalida cache
  botão "Gerenciar assinatura" (se ativo) → Asaas customer portal URL

[INTL — Stripe]:
  botão "Assinar" ou "Upgrade" →
    mutation: createCheckout({ plan, country: 'INTL' })
    server fn → invokeEdgeFunction('create-checkout', { plan, country: 'INTL' })
    → retorna { url } → redirect para Stripe Checkout
  após pagamento: Stripe webhook → UPDATE subscriptions → Realtime invalida cache
  botão "Gerenciar assinatura" →
    mutation: createPortal()
    server fn → invokeEdgeFunction('create-portal')
    → retorna { url } → redirect para Stripe Customer Portal
```

#### `dashboard/api-keys.tsx` — ApiKeysList

```
data: useQuery(['api-keys'], listApiKeys, { staleTime: 60_000 })

<ApiKeysList>
  tabela: nome · criado em · scopes · último uso · [Revogar]
  botão "Criar API key" → abre <CreateKeyModal>

<CreateKeyModal>
  campos: nome · scopes (multi-select: read / write / admin)
  onSubmit → createApiKey({ name, scopes })
    server fn (adminClient):
      1. schema.parse(input)
      2. raw = crypto.randomUUID() (ou equivalente seguro)
      3. hash = sha256(raw)
      4. INSERT api_keys({ user_id, name, scopes, key_hash: hash })
      5. retorna { secret: raw }  ← show-once
    exibe secret em fonte mono UMA vez após criação
    onClose → limpar secret do useState (não persiste no cache)

  revogar inline:
    confirmação simples → revokeApiKey(id)
    server fn: DELETE FROM api_keys WHERE id=id AND user_id=uid
    → invalidate ['api-keys']
```

#### `dashboard/account.tsx` — AccountSection

```
<ProfileForm>
  campos: nome completo · country (BR/INTL) · idioma preferido
  onSave → mutation: updateProfile({ name, country, language })
    server fn: UPDATE profiles WHERE user_id = uid

seção Segurança:
  botão "Alterar senha" →
    server fn: sendMagicLink(email) → supabase.auth.signInWithOtp({ email })
    toast "Link enviado para seu email"

seção GDPR:
  botão "Exportar meus dados"
    mutation: exportData()
    server fn (adminClient):
      1. SELECT profiles + subscriptions + license_checks + api_keys
      2. gera ZIP JSON
      3. upload para Supabase Storage bucket 'exports' (privado)
      4. gera URL assinada TTL 5 min
      5. retorna { url }
    cliente: <a href={url} download> ← abre download direto

  botão "Deletar conta"
    confirmação: digitar email para confirmar
    mutation: requestAccountDeletion()
    server fn (adminClient):
      1. Resend: envia account-deleted.tsx para o email
      2. UPDATE profiles SET soft_delete_at = now() WHERE id = uid
      3. supabase.auth.signOut()
    redirect /
    cron-hard-delete (Edge Fn + pg_cron, diário):
      1. cancelar subscription no Stripe/Asaas via API
      2. DELETE FROM auth.users WHERE id IN (
           SELECT id FROM profiles WHERE soft_delete_at < now() - interval '30 days'
         )
      3. cascade deleta profiles, tokens, subscriptions, api_keys, license_checks
```

### P5 — Server Functions (especificação completa)

Todas em `src/server/fns/` via `createServerFn()`. Executam no runtime Nitro (Vercel Node). Usam `createSupabaseServerClient()` para operações com a session do usuário. Usam `adminClient` apenas onde service role é obrigatório.

```
AUTH (auth.ts)
  getSession()
    → createSupabaseServerClient().auth.getUser()
    → retorna: User | null

  signUp(input: { name, email, password, country, turnstileToken })
    → z.object({ name: z.string().min(2), email: z.string().email(),
                 password: z.string().min(8), country: z.enum(['BR','INTL']),
                 turnstileToken: z.string() }).parse(input)
    → verifyTurnstile(turnstileToken)
    → supabase.auth.signUp({ email, password, options: { data: { name, country } } })
    → retorna { redirect: '/dashboard?welcome=true' }

  signIn(input: { email, password })
    → z.object({ email: z.string().email(), password: z.string() }).parse(input)
    → supabase.auth.signInWithPassword({ email, password })
    → retorna { user }

  signOut()
    → supabase.auth.signOut()

  sendMagicLink(input: { email })
    → z.object({ email: z.string().email() }).parse(input)
    → supabase.auth.signInWithOtp({ email })

TOKEN (token.ts)
  getTokenStatus()
    → adminClient.from('tokens').select('token').eq('user_id', uid).single()
    → retorna { revealed: token === null }

  getToken()
    → adminClient.from('tokens').select('token').eq('user_id', uid).single()
    → token != null:
        adminClient.from('tokens').update({ token: null }).eq('user_id', uid)
        retorna { token: string }
    → token == null:
        retorna { revealed: true }

  rotateToken()
    → invokeEdgeFunction('rotate-token', { user_id: uid })
    → edge fn executa compare-and-swap (ver P4 TokenReveal estado B)
    → retorna { token: string }

SUBSCRIPTION (subscription.ts)
  getSubscription()
    → supabase.from('subscriptions').select('*').eq('user_id', uid).single()

  createCheckout(input: { plan: 'plus'|'pro' })
    → z.object({ plan: z.enum(['plus','pro']) }).parse(input)
    → getSubscription() → determina country + provider
    → invokeEdgeFunction('create-checkout', { plan, country })
    → retorna { url: string }

  createPortal()
    → invokeEdgeFunction('create-portal', { user_id: uid })
    → retorna { url: string }

API KEYS (api-keys.ts)
  listApiKeys()
    → supabase.from('api_keys')
        .select('id, name, scopes, created_at, last_used_at')
        .eq('user_id', uid)
        .order('created_at', { ascending: false })

  createApiKey(input: { name, scopes })
    → z.object({ name: z.string().min(1).max(64),
                 scopes: z.array(z.enum(['read','write','admin'])) }).parse(input)
    → raw = crypto.randomUUID()
    → hash = sha256(raw)
    → adminClient.from('api_keys').insert({ user_id: uid, name, scopes, key_hash: hash })
    → retorna { secret: raw }

  revokeApiKey(input: { id })
    → z.object({ id: z.string().uuid() }).parse(input)
    → supabase.from('api_keys').delete().eq('id', id).eq('user_id', uid)

GDPR (gdpr.ts)
  exportData()
    → adminClient: SELECT profiles + subscriptions + license_checks + api_keys
    → gera ZIP JSON em memória
    → storage.upload('exports', `${uid}-${Date.now()}.zip`, zip)
    → storage.createSignedUrl('exports', filename, 300)  ← TTL 5min
    → retorna { url: signedUrl }

  requestAccountDeletion()
    → Resend: send account-deleted.tsx para user.email
    → adminClient.from('profiles').update({ soft_delete_at: new Date() }).eq('id', uid)
    → supabase.auth.signOut()

ISSUES (issues.ts)
  submitIssue(input: { title, category, description, email, turnstileToken })
    → z.object({ title: z.string().min(3).max(200),
                 category: z.enum(['bug','feedback','feature']),
                 description: z.string().max(5000),
                 email: z.string().email().optional(),
                 turnstileToken: z.string() }).parse(input)
    → verifyTurnstile(turnstileToken)
    → adminClient.from('issues').insert({ title, category, description, email })
    → Resend: send para support@vectora.company

WAITLIST (via leads.ts — já implementado)
  joinWaitlist(input: { email, turnstileToken, source? })
    → verifyTurnstile(turnstileToken)
    → addToWaitlist({ email, source })  ← leads.ts
```

### P6 — Estado e cache

```
TanStack Query (staleTime explícito em cada useQuery):
  ['session']         getSession()          staleTime: 5 * 60_000
  ['subscription']    getSubscription()     staleTime: 30_000  + invalidado por Realtime
  ['api-keys']        listApiKeys()          staleTime: 60_000
  ['license-checks']  getLicenseHistory()   staleTime: 5 * 60_000

URL params (TanStack Router search params, type-safe):
  /dashboard?welcome=true      → mostrar QuickStart
  /signup?plan=plus|pro        → pré-selecionar plano na PricingSection
  /pricing?currency=brl|usd   → toggle de moeda
  /login?redirect=...          → redirecionar após login bem-sucedido

Ephemeral (useState — NÃO cachear, NÃO persistir, NÃO colocar no Zustand):
  token raw        → limpar ao navegar (TokenReveal onCopy / onNavigate)
  api-key secret   → limpar ao fechar modal (CreateKeyModal onClose)
  turnstile token  → válido 5min, descartado após uso

Supabase Realtime (dashboard/route.tsx):
  channel: 'license_status'
  table: subscriptions, filter: user_id=eq.{uid}
  onInsert + onUpdate: queryClient.invalidateQueries(['subscription'])
  cleanup: canal.unsubscribe() no onUnmount do route

Zustand (src/store/auth.ts):
  state: { session: User | null }
  hydration: supabase.auth.onAuthStateChange → setState
  uso: Header — renderizar "Entrar" vs avatar dropdown
  NÃO usar para dados de subscription, token, api-keys — isso é TanStack Query
```

### P7 — Emails transacionais

Todos os templates em `emails/` via React Email. Disparados via Resend (`src/lib/email/resend.ts`).

```
welcome.tsx
  disparo: 1h após signup (pg_cron ou webhook on-signup delay)
  assunto: "Seu Vectora está pronto"
  conteúdo: link dashboard + quickstart 4 passos

trial-ending-7d.tsx
  disparo: 7 dias antes de trial_ends_at (pg_cron diário)
  assunto: "Seu trial vence em 7 dias"
  CTA: "Assinar agora"

trial-ending-1d.tsx
  disparo: 1 dia antes de trial_ends_at
  assunto: "Último dia do trial"
  CTA urgente: "Assinar agora"

invoice-paid.tsx
  disparo: após PAYMENT_RECEIVED (Asaas) / invoice.paid (Stripe)
  conteúdo: confirmação + link dashboard

invoice-failed.tsx
  disparo: após PAYMENT_OVERDUE / invoice.payment_failed
  conteúdo: link para atualizar método de pagamento

magic-link.tsx
  disparo: sendMagicLink()
  assunto: "Link de acesso ao Vectora"

account-deleted.tsx
  disparo: requestAccountDeletion()
  assunto: "Conta Vectora agendada para exclusão"
  conteúdo: "Sua conta será excluída em 30 dias. Clique aqui para cancelar."

waitlist-confirmation.tsx
  disparo: addToWaitlist() — já implementado via leads.ts
  assunto: "Você está na lista do Vectora"
```

### P8 — SEO por rota

TanStack Start gera SSR completo para todas as rotas públicas. Meta tags via `route.head()` — executado no servidor, sem JavaScript necessário para o crawler.

```
Rotas com SSR (todas as públicas):
  / pricing faq support issues privacy terms cookies sla dpa login signup

Head por rota (route.head()):
  title:      m.site_title() + " — " + nome da página
  description: m.site_description() contextual por rota
  og:image:   /api/og?title=...&desc=...  (edge fn Satori)
  og:url:     APP_URL + pathname
  hreflang:   pt · en · es · fr · it · de · ru  (7 idiomas — todos em messages/)
  canonical:  URL sem query params, com prefixo de idioma correto
  json-ld:
    /         → SoftwareApplication + Organization + WebSite (sitelinks searchbox)
    /pricing  → Product (Plus + Pro)
    /faq      → FAQPage
    /support  → ContactPage

Sitemap (edge fn ou build-time):
  rotas públicas × 7 idiomas
  frequência: / pricing → weekly; faq legais → monthly
  prioridade: / → 1.0; pricing → 0.9; faq → 0.7; legais → 0.3

Dashboard (/dashboard/*):
  route.head(): <meta name="robots" content="noindex, nofollow">
  robots.txt: Disallow: /dashboard/
```

**Performance**: Lighthouse ≥ 95. Imagens AVIF/WebP. GIFs com `loading="lazy" decoding="async"` e placeholder skeleton. Font subset Aeonik Mono Latin (já em `public/fonts/`). Code splitting automático por rota.

**Analytics**: Plausible + GA4 já implementados em `src/lib/analytics/`. Events a trackear: `signup`, `trial_started`, `paid_conversion`, `cancel`, `gif_viewed`, `pricing_viewed`, `waitlist_join`.

### Verificação (Bloco P)

- Landing carrega com GIF hero em loop. Lighthouse ≥ 95.
- SSR validado: `curl https://vectora.company` retorna HTML completo com meta tags e json-ld — sem JavaScript.
- Signup BR → dashboard → token reveal → "Copie e guarde". Segunda visita → banner amarelo.
- Rotacionar token → novo token exibido UMA vez. Double-click no botão → bloqueado por `isPending`.
- `exportData` → ZIP baixado via URL assinada (expira em 5 min).
- Signup BR via PIX → webhook Asaas → `UPDATE subscriptions` → Realtime invalida cache → status "ativo" sem refresh manual.
- Signup INTL → Stripe Checkout em USD.
- Upgrade Plus→Pro → tier atualizado com crédito proporcional.
- Cancelar → status "canceled", acesso até fim do período.
- Deletar conta → email enviado + soft_delete_at definido + signOut + redirect /. Após 30d cron executa hard delete na ordem correta (billing → auth → cascade).
- FAQ, Issues, Support, Legal acessíveis sem auth.
- i18n: trocar idioma → URL muda, interface traduzida, erros de auth mapeados para Paraglide.
- `noindex` confirmado em todas as rotas `/dashboard/*` via curl.

---

## BLOCO Q — Documentação `docs.vectora.company`

> **Stack**: Docusaurus 3 + customização visual alinhada ao site (paleta navy + azul claro, Aeonik Mono). Repo público: `vectora-company/docs`.

### Q1 — Setup + tema + i18n

Docusaurus 3 com `@docusaurus/theme-classic`. i18n: `pt` (padrão) + `en`. Algolia DocSearch (free para open source). Theme switcher dark/light. Sidebar com auto-collapse + breadcrumbs. Versionamento por release major (`/v1.x/...`).

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
├── rest-api       (auto-gerado via redocly a partir do OpenAPI 3.1)
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

### Q6 — Changelog + RSS

Página `/changelog`: versão, data, novidades, bugfixes, breaking changes com migration guide. RSS em `docs.vectora.company/changelog/rss.xml`. Webhook `release.published`.

### Q7 — Padrões de qualidade

Toda página: intro, pré-requisitos, passos numerados, resultado esperado, troubleshooting. Exemplos com output esperado. Screenshots/GIFs gerados via Playwright. `pt` primário, `en` como tradução.

### Verificação (Bloco Q)

- `docs.vectora.company` com HTTPS verde.
- Algolia DocSearch em ≤300ms.
- Quick-start em 10 min em VM limpa.
- Docker Compose da doc funciona em Ubuntu 24.04 limpo.
- Trocar idioma preserva a página atual.
- Changelog RSS válido (W3C feed validator).

---

## BLOCO R — Suporte & Comunidade

### R1 — WhatsApp Business

Link no site, docs e dashboard (Settings → Suporte). Horário: seg–sex 9h–18h BRT. Auto-resposta fora do horário com link para FAQ e issues. Templates aprovados para outbound (expiração, upgrade) com opt-in no dashboard.

### R2 — Email `support@vectora.company`

SLA: ≤48h úteis (Plus), ≤24h úteis (Pro). Crisp ou Freshdesk para ticketing. 8 templates iniciais: trial estendido, refund, license issue, install trouble, billing dispute, GDPR request, feature request, bug report.

### R3 — GitHub Issues público

Repo `vectora-company/issues`: templates (bug, feature, docs), labels, triagem semanal, auto-assign via GitHub Actions.

### R4 — Comunidade

**MVP**: GitHub Discussions com 5 categorias (Announcements · Ideas · Q&A · Show and tell · Help). Bruno responde Q&A 2×/semana.

**Discord** (pós-lançamento se ≥500 usuários): canais `#announcements`, `#general`, `#support`, `#show-and-tell`, `#pt-br`, `#en`. Webhooks de releases em `#announcements`.

### R5 — Beta testers

10–20 betas via Discord LangChain BR, Telegram Python BR, LinkedIn. Acesso Pro gratuito 6 meses em troca de feedback mensal (NPS, top 3 positivos, top 3 problemas). Calls 1:1 opcionais. Depoimentos com consent para o site. Hall of Fame com avatar/nome/empresa.

### R6 — Status page (`status.vectora.company`)

BetterStack Uptime ou Upptime. Componentes: API REST · Chat SSE · Validate License Supabase · Site · Docs · Update server. Check interval: 60s. Histórico 90 dias. Subscribe via email, RSS, webhook.

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

- **PyPI** `vectora-cli 1.0.0` com README, badges e classifiers corretos (`License :: Other/Proprietary License`, `Topic :: Scientific/Engineering :: Artificial Intelligence`, `Programming Language :: Python :: 3.13`).
- **Docker Hub + GHCR** `vectora/vectora:1.0.0` multi-arch (amd64 + arm64), Trivy scanning verde.
- **GitHub Releases** `v1.0.0` privado: binários assinados (Win .msi + .exe NSIS, macOS .dmg universal, Linux .AppImage + .deb + .rpm), checksums SHA-512, release notes PT-BR + EN.

### S2 — Kit para influenciadores

Enviado com 1–2 semanas de antecedência. Conteúdo: licença Pro por 6 meses, guia de instalação 1 página PDF, 5 sugestões de demo prontas, pasta de assets (logo SVG/PNG, screenshots, banner YouTube 1280×720, GIF), contato direto Bruno, cupom de tracking por canal.

**Canais BR**: TecMundo · Loop Infinito · Código Fonte TV · Lucas Montano · Mano Deyvin · Filipe Deschamps · Augusto Galego · Computaria · Programador BR.

**Canais INTL (Fase 2)**: Fireship · AI Jason · Theo t3.gg · r/selfhosted · r/LocalLLaMA · Hacker News.

### S3 — Posts de lançamento

LinkedIn: 3 posts pré-lançamento (T-14, T-7, T-0) + diários T+1 a T+7. Reddit (r/selfhosted, r/LocalLLaMA, r/Python, r/SaaS). X thread com GIF. Hacker News "Show HN" terça/quarta 9h ET. Indie Hackers post detalhado.

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

**Indicadores**: conversão trial→pago ≥5% · churn ≤20% em 30d · NPS ≥50 · tráfego ≥5k visits/semana após T+30.

**Dashboard**: Plausible · GA4 · Supabase Dashboard · Stripe/Asaas · BetterStack · Sentry.

### S7 — Conteúdo pós-lançamento (semanas 2–8)

Série "Casos de uso do Vectora" — 1 post/vídeo por semana: RAG sobre codebase legado · code review automatizado · equipe de 3 devs · Vectora + Claude Code via MCP · Vectora + n8n · self-hosting em VPS R$30/mês · VS Code extension · Vectora como sub-agente ACP no Zed.

### S8 — Cupons early adopter

- `VECTORA25` — 25% off para primeiros 100 assinantes Plus (`duration: forever`, `max_redemptions: 100`).
- `PROEARLY` — ~18% off para primeiros 50 assinantes Pro (`duration: forever`, `max_redemptions: 50`).
- Variantes por canal: `MONTANO25`, etc. — tracking de conversão por cupom.
- Criados manualmente no Stripe e Asaas.

### S9 — Roadmap público (`/roadmap`)

Página no site com 4 seções (✓ Lançado · 🚧 Em desenvolvimento · 📍 Planejado) em linguagem de usuário. Updates via blog post + email mensal. Voting via emoji reactions no GitHub Discussions.

### Verificação (Bloco S)

- PyPI `vectora-cli 1.0.0` publicado; `pip install` em VM limpa funciona.
- Docker `vectora/vectora:1.0.0` testado em Ubuntu 24.04 + macOS Docker Desktop.
- GitHub Release `v1.0.0` com 6 binários assinados + checksums + release notes bilíngue.
- Kit enviado para todos os canais BR com ≥2 semanas de antecedência; ≥5 confirmaram publicar.
- Posts LinkedIn/Reddit/HN/Twitter publicados conforme cronograma.
- Trailer no YouTube com thumbnail.
- ≥10 assinantes pagantes na semana 1.
- Cupons early adopter ativos e rastreáveis nos dashboards Stripe + Asaas.
- `/roadmap` publicado com ≥4 seções e ≥10 itens.

---

## Verificação end-to-end (Company)

- **O**: CNPJ ativo, conta PJ, domínios + emails operacionais, termos publicados e revisados.
- **P**: SSR validado via curl. Fluxo completo: signup → dashboard → reveal → billing BR + INTL → Realtime atualiza status. Hard delete na ordem correta após 30d. Lighthouse ≥ 95.
- **Q**: `docs.vectora.company` no ar; quick-start em 10 min em VM limpa.
- **R**: status page com 6 componentes, ≥10 betas com NPS, todos os canais de suporte operacionais.
- **S**: PyPI 1.0 + Docker + Release nativo publicados; ≥5 influenciadores BR confirmados; ≥10 pagantes na semana 1.
