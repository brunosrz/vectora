# Pseudo-código — vectora.company

Documento de referência da arquitetura do site institucional e billing da Vectora.
Aprovado antes da implementação. Atualizar conforme o projeto evolui.

---

## Índice

1. [Árvore de rotas](#árvore-de-rotas)
2. [Landing Page](#landing-page)
3. [Páginas públicas](#páginas-públicas)
4. [Auth (signup / login)](#auth)
5. [Dashboard](#dashboard)
6. [Server Functions](#server-functions)
7. [Estado e cache](#estado-e-cache)
8. [Emails transacionais](#emails-transacionais)
9. [SEO por rota](#seo-por-rota)
10. [Estrutura de arquivos](#estrutura-de-arquivos)
11. [Referência: Vectora Agent](#referência-vectora-agent)

---

## Árvore de rotas

```
src/routes/
├── __root.tsx              ← shell HTML: <html lang> + Head meta + analytics
│                              beforeLoad: set locale, inject Plausible + GA4
│                              Layout: <Header /> + {children} + <Footer />
│
├── index.tsx               ← Landing (SSR, pública)
├── pricing.tsx             ← Pricing dedicado (SSR, pública)
├── faq.tsx                 ← FAQ accordion (SSR, pública)
├── support.tsx             ← Canais de suporte (pública)
├── issues.tsx              ← Formulário de issues + Turnstile (pública)
│
├── privacy.tsx             ← Privacidade
├── terms.tsx               ← Termos de uso
├── cookies.tsx             ← Política de cookies
├── sla.tsx                 ← SLA
├── dpa.tsx                 ← DPA
│
├── signup.tsx              ← Cadastro; redireciona /dashboard se já logado
├── login.tsx               ← Login; redireciona /dashboard se já logado
│
└── dashboard/
    ├── route.tsx           ← Layout do dashboard
    │                          beforeLoad: verificar sessão → redirect /login
    │                          Layout: <Sidebar /> + <main>{children}</main>
    │                          onMount: subscrever Supabase Realtime 'license_status'
    │                          onUnmount: cancelar canal Realtime
    ├── index.tsx           ← Token (rota padrão)
    ├── billing.tsx         ← Pagamento
    ├── api-keys.tsx        ← API Keys
    ├── account.tsx         ← Conta
    └── license.tsx         ← Status da Licença
```

---

## Landing Page

### Seções (ordem de cima pra baixo)

```
<LandingPage>
  <Hero />
  <ShowcaseGifs />
  <AgenticFlowSection />
  <RagFlowSection />
  <TeamSetupSection />
  <WhySelfHosted />
  <PricingSection />
  <WaitlistCta />           ← pré-lançamento; substituir por <FinalCta /> após launch
```

---

### Hero

```
<Hero>
  elementos:
    Eyebrow badge: "Self-hosted · Privacy-first · Open core"
      → pill com ícone de cadeado
      → cor: brand accent

    H1 (tagline): m.hero_tagline()
      → "Your AI. Your Data. Your Server."
      → fonte grande, bold, tracking tight
      → palavra chave com gradiente de cor (brand)

    Subtítulo: m.hero_subtitle()
      → 1-2 linhas: RAG, MCP, multi-user web chat, never leaves your server

    CTAs (row):
      [Primário]   "Começar trial — 30 dias grátis"  → /signup
      [Secundário] "Ver preços"                      → scroll para #pricing

    GIF central (destaque visual):
      → Interface do Vectora respondendo pergunta técnica
      → bordas arredondadas, sombra grande com glow brand
      → max-width: 860px, aspect-ratio: 16/10
      → placeholder: skeleton shimmer enquanto carrega
      → <img loading="lazy" decoding="async" alt="...">
      → [PLACEHOLDER durante dev: retângulo 860×537 com texto "GIF showcase-chat"]

  layout:
    → centralizado, padding vertical generoso
    → background: gradiente ou mesh gradient brand
```

---

### ShowcaseGifs — "Veja o Vectora em ação"

```
<ShowcaseGifs>
  heading: m.showcase_heading()
  layout: grade 2×2 (desktop) → 1 coluna (mobile)

  cards (4):

  [1] Conversação com contexto
      gif: /gifs/showcase-chat.gif
      placeholder: retângulo 640×400 "GIF: chat com Vectora"
      título: m.showcase_chat_title()   "Conversa Natural"
      desc: "Pergunte em linguagem natural — sobre código, documentos,
             planilhas ou qualquer arquivo do seu servidor."

  [2] RAG — busca semântica
      gif: /gifs/showcase-rag.gif
      placeholder: retângulo 640×400 "GIF: RAG finding doc"
      título: m.showcase_rag_title()    "RAG Avançado"
      desc: "Indexe qualquer documento. O Vectora encontra
             a informação certa com busca vetorial no Qdrant."

  [3] Agente codando
      gif: /gifs/showcase-code.gif
      placeholder: retângulo 640×400 "GIF: Coder Agent em ação"
      título: m.showcase_code_title()   "Agente Desenvolvedor"
      desc: "Do planejamento ao código. O Vectora escreve, refatora
             e explica usando o contexto do seu repositório."

  [4] Planejamento multi-step
      gif: /gifs/showcase-plan.gif
      placeholder: retângulo 640×400 "GIF: raciocínio estruturado"
      título: m.showcase_plan_title()   "Raciocínio Estruturado"
      desc: "Tarefas complexas divididas automaticamente.
             Veja cada passo do raciocínio em tempo real."

  <ShowcaseCard>
    props: gif: string, placeholder: string, title: string, description: string
    elementos:
      GIF/placeholder com borda brand tênue, bordas arredondadas
      hover: scale(1.02) + sombra mais intensa
      Label/título (bold) + Descrição (text-sm, muted)
    acessibilidade: aria-label descritivo, prefers-reduced-motion → frame estático
```

---

### AgenticFlowSection — "Como o Vectora pensa"

```
<AgenticFlowSection>
  id="agentic-flow"
  heading: m.agentic_heading()   "Como o Vectora pensa"
  subtítulo: "Um orquestrador coordena agentes especializados —
              cada um com ferramentas, memória e foco próprio."

  layout: 2 colunas desktop (imagem esquerda, texto direita)
          1 coluna mobile (imagem acima, texto abaixo)

  [coluna esquerda]
    <AgenticDiagram>  ← SVG inline importado de /public/diagrams/agentic-flow.svg
      nós do diagrama (fluxo real do LangGraph):
        Usuário
          ↓
        Orchestrator  (centro, maior — decide roteamento)
          ├──────────────────────────────────────────────────────────┐
          ↓                    ↓                    ↓                ↓
        Coder Agent      Search Agent         RAG Subgraph    Paralelo
        (filesystem      (web search +        (expand →       (múltiplos
         terminal git     fetch URL +          retrieve →      agentes em
         ingest_docs)     vector_search)       decide →        asyncio.gather)
                                               [rerank|web] →
                                               inject)
          └──────────────────────────────────────────────────────────┘
                                  ↓
                          Orchestrator (síntese)
                                  ↓
                           Resposta ao usuário

      cores:
        Orchestrator: brand primary
        Coder: brand secondary (tom azul)
        Search: brand secondary (tom roxo)
        RAG Subgraph: brand secondary (tom verde)
        Paralelo: brand secondary (tom laranja)
      arestas: gradiente entre os dois nós conectados
      prefers-reduced-motion: SVG estático, sem animações

  [coluna direita]
    bullets com ícone:
      ○ Orquestrador decide em tempo real: responder, delegar ou paralelizar
      ○ Coder Agent: arquivos, terminal, git, implementação de código
      ○ Search Agent: web em tempo real, RAG, curadoria da base de conhecimento
      ○ RAG Subgraph: pipeline completo — query expansion, reranking, web fallback
      ○ Modo paralelo: múltiplas tarefas executadas em asyncio.gather
    CTA: "Documentação técnica →"  → docs externos
```

---

### RagFlowSection — "Seus documentos, acessíveis de qualquer lugar"

```
<RagFlowSection>
  id="rag-flow"
  layout: texto esquerda, diagrama direita

  [coluna esquerda]
    heading: m.rag_heading()
    bullets:
      ○ PDF, DOCX, TXT, Markdown, código-fonte, planilhas
      ○ Embeddings locais via Cohere (search_document / search_query assimétrico)
      ○ Hybrid RAG: dense (Cohere) + sparse (BM25) com RRF merge
      ○ Multi-query: LLM gera N variantes da query para maior recall
      ○ HyDE: documento hipotético quando score inicial é baixo
      ○ Reranker Cohere para precisão máxima
      ○ Citação da fonte em cada resposta

  [coluna direita]
    <RagDiagram>  ← SVG inline de /public/diagrams/rag-flow.svg
      nós (fluxo real do rag_subgraph):
        Documento → Chunking → Cohere Embed → LanceDB (vetor)
                                                    ↓
        Query → Multi-query expansion → Hybrid Search (dense+BM25) → Reranker
                                                                           ↓
                    Score ≥ 0.7: direto ──────────────────────────→ inject
                    Score 0.4–0.7: search_audit → (corrige RAG) → inject
                    Score < 0.4: Web Fallback → search_audit ──→ inject
                                                                           ↓
                                                                    LLM + contexto
                                                                           ↓
                                                                    Resposta com fonte
      labels discretos nas arestas: "chunking", "embed", "top-K", "reranquear"
      cilindro para LanceDB (banco de dados), caixa para LLM
```

---

### TeamSetupSection — "Do zero ao time rodando em minutos"

```
<TeamSetupSection>
  id="team-setup"
  background: brand-tint sutil
  heading: m.team_heading()
  subtítulo: "Stack completa em Docker. Controle total no seu servidor."

  <SetupTimeline>  ← timeline vertical, 4 passos

  [1] Deploy da stack
      ícone: Docker
      título: "Suba a stack com Docker Compose"
      elemento visual: code block inline (apenas visual, não copiável)
        docker compose up -d
      badges: Vectora · PostgreSQL · Qdrant · Redis
      desc: "Um único arquivo. Sem dependências externas."

  [2] Conta root
      ícone: usuário com escudo
      título: "Crie a conta root"
      elemento visual:
        GIF pequeno inline (~400px): tela de first-time setup
        [PLACEHOLDER: retângulo "GIF: setup-root.gif"]
      desc: "Acesso administrativo completo ao seu workspace."

  [3] Convidar equipe
      ícone: pessoas
      título: "Convide os membros"
      elemento visual:
        GIF pequeno: painel de membros → Convidar → email enviado
        [PLACEHOLDER: retângulo "GIF: setup-invite.gif"]
      desc: "Controle de permissões por projeto."

  [4] Criar projetos
      ícone: pasta com IA
      título: "Inicialize seus projetos"
      elemento visual:
        GIF pequeno: criar projeto, adicionar docs, primeiro chat
        [PLACEHOLDER: retângulo "GIF: setup-project.gif"]
      desc: "Cada projeto tem sua própria base de conhecimento e histórico."

  banner de compatibilidade:
    ícones: PostgreSQL · Qdrant · Redis · Docker
    texto: "Compatível com qualquer VPS Linux — AWS, GCP, Hetzner, DigitalOcean"
```

---

### WhySelfHosted — "Por que self-hosted?"

```
<WhySelfHosted>
  layout: grade 2×2 → 4 cards

  [Privacidade]
    ícone: cadeado
    desc: "Nenhuma conversa, documento ou código é enviado a terceiros.
           Conformidade com LGPD, GDPR e políticas internas."

  [Custo]
    ícone: moeda
    desc: "Preço fixo pela licença Vectora. Custos de LLM sob seu controle —
           use modelos locais gratuitamente."

  [Customização]
    ícone: engrenagem
    desc: "Configure providers de LLM, modelos de embedding, tamanho de chunk,
           prompts de sistema e muito mais."

  [Soberania]
    ícone: servidor
    desc: "Sem lock-in. Sem dependência de cloud. Rode offline se precisar.
           Seu servidor, suas regras."
```

---

### PricingSection

```
<PricingSection>
  id="pricing"
  heading: m.pricing_heading()
  subtítulo: "30 dias de trial grátis. Sem cartão de crédito."

  toggle BRL / USD
    → default: 'BRL' se navigator.language contém 'pt', senão 'USD'
    → apenas visual, sem reload

  [card Plus]
    badge: "Para times pequenos"
    preço BRL: R$ 20/mês  |  USD: $ 7/mês
    features:
      ✓ 1 workspace
      ✓ Até 5 membros
      ✓ RAG ilimitado
      ✓ MCP integrations
      ✓ Suporte por email
      — Priority support
      — SSO / SAML
    CTA: "Começar trial grátis" → /signup?plan=plus

  [card Pro]
    badge: "Para empresas"  (destaque — borda brand, fundo tint)
    preço BRL: R$ 55/mês  |  USD: $ 20/mês
    features:
      ✓ Workspaces ilimitados
      ✓ Membros ilimitados
      ✓ RAG ilimitado
      ✓ MCP integrations
      ✓ Priority support (SLA 24h)
      ✓ SSO / SAML (em breve)
    CTA: "Começar trial grátis" → /signup?plan=pro

  tabela comparativa (colapsável "Ver comparação completa"):
    linhas: Storage · Projetos · API Keys · Webhooks · Audit log · SLA
    expand/collapse com animação
```

---

### WaitlistCta — pré-lançamento

```
<WaitlistCta>
  visível quando: VITE_LAUNCH_MODE=waitlist
  background: brand gradient forte

  heading: m.waitlist_heading()   "Seja um dos primeiros"
  subtítulo: "Trial grátis de 30 dias para quem entrar na lista agora."

  <WaitlistForm>
    input: type="email", placeholder="seu@email.com"
    <Turnstile onSuccess(token) → armazena no state local />
    botão: "Entrar na lista"
    onSubmit:
      → Turnstile ainda não resolveu: desabilita botão
      → mutation: joinWaitlist({ email, turnstileToken, source: 'landing-cta' })
      → sucesso: esconde form, mostra "✓ Você está na lista! Verifique seu email."
      → erro duplicate: "Esse email já está na lista."
      → erro genérico: m.error_generic()

  rodapé: "Sem spam. Apenas o aviso de lançamento."
```

---

### Comportamento de scroll e separadores

```
intersection observer em cada seção:
  threshold 0.15 → fade-in + slide-up leve ao entrar na viewport
  prefers-reduced-motion → sem animação, conteúdo já visível

separadores entre seções:
  → sem <hr> ou linha
  → espaçamento vertical generoso (py-24 desktop, py-16 mobile)
  → alternância de background: transparente · brand-tint · transparente · brand-tint
```

---

## Páginas públicas

### pricing.tsx

```
loader: nenhum (dados estáticos)
head: title "Preços — Vectora", og:image /og-pricing.png
render: <PricingSection /> (reusa o componente da landing, sem Hero nem seções extras)
        + <FaqAccordion items={pricingFaqs} /> (subset das mais frequentes sobre preço)
        + <WaitlistCta /> ou <FinalCta />
```

### faq.tsx

```
loader: nenhum (dados estáticos por ora; migrar para Supabase se crescer)
head: title "FAQ — Vectora", json-ld FAQPage
render:
  heading "Perguntas Frequentes"
  <FaqAccordion>
    categorias: Geral · Instalação · Planos · Segurança · Técnico
    cada item: pergunta (H3) + resposta (collapse animado)
    busca: input filtra visualmente sem reload
```

### support.tsx

```
render:
  heading "Suporte"
  3 canais:
    [Email]    mailto:support@vectora.company
    [GitHub]   link para issues do repo público
    [Docs]     link para docs externos
  SLA por plano:
    Plus: resposta em 48h
    Pro:  resposta em 24h
    Trial: community (GitHub)
```

### issues.tsx

```
render:
  heading "Reportar um problema"
  <IssueForm>
    campos: título · categoria (bug/feedback/feature) · descrição · email
    <Turnstile onSuccess(token) />
    onSubmit → mutation: submitIssue({ ...fields, turnstileToken })
      → server fn: verifyTurnstile() → INSERT Supabase issues (nova tabela)
                   → Resend para support@vectora.company
      → sucesso: toast "Problema reportado. Responderemos em breve."
```

### Páginas legais (privacy, terms, cookies, sla, dpa)

```
conteúdo: MDX estático (versionado no git)
render: <LegalPage title="..." lastUpdated="..."><MDXContent /></LegalPage>
  → sumário lateral (desktop): âncoras automáticas dos H2
  → mobile: sem sumário
```

---

## Auth

### signup.tsx

```
loader: getSession() → se logado, redirect /dashboard

<SignupForm>
  campos: nome completo · email · senha · país (BR / INTL)
  <Turnstile onSuccess(token) />

  onSubmit → signUp({ name, email, password, country, turnstileToken })
    server fn:
      1. verifyTurnstile(token)           ← falha → erro imediato
      2. supabase.auth.signUp({ email, password, options: { data: { name, country } } })
      3. Supabase trigger on-signup:
           INSERT profiles (id, full_name, country)
           INSERT tokens (user_id, token=raw, token_hash=sha256(raw))
           INSERT subscriptions (tier='plus', status='trialing', trial_ends_at=now+30d, ...)
      4. redirect /dashboard?welcome=true

  link "Já tenho conta" → /login
  link "Ver preços" → /pricing
```

### login.tsx

```
loader: getSession() → se logado, redirect /dashboard

<LoginForm>
  campos: email · senha
  link "Esqueci a senha" → magic link (sendMagicLink)

  onSubmit → signIn({ email, password })
    server fn: supabase.auth.signInWithPassword()
    sucesso: redirect para ?redirect param ou /dashboard

  link "Criar conta" → /signup
```

---

## Dashboard

### dashboard/route.tsx — layout compartilhado

```
beforeLoad:
  getSession() → null → redirect '/login?redirect=' + pathname

onMount:
  canal Realtime Supabase:
    channel: 'license_status'
    table: subscriptions, filter: user_id=eq.{uid}
    onUpdate: queryClient.invalidateQueries(['subscription'])

onUnmount: canal.unsubscribe()

render:
  <DashboardLayout>
    <Sidebar>
      items:
        Token (ícone key)
        Licença (ícone shield-check)
        Pagamento (ícone credit-card)
        API Keys (ícone zap)
        Conta (ícone user)
        Suporte (ícone help-circle)
      item ativo: destacado com brand color
      mobile: bottom tab bar (5 itens + overflow)
    </Sidebar>
    <main>{children}</main>
  </DashboardLayout>
```

### dashboard/index.tsx — TokenReveal

```
loader: getTokenStatus() → { revealed: boolean, hasToken: boolean }

<TokenReveal>
  estado A — nunca revelado (token existe no DB):
    botão "Clique para revelar"
    onReveal → getToken():
      server fn: adminClient.from('tokens').select('token').single()
      → se token != null: retorna token + UPDATE SET token=null (show-once)
      → exibe token em fonte mono + botão copiar
      warning: "Copie e guarde. Não será exibido novamente."
    onCopy OU onNavigate: limpar token do state (não persiste no cache)

  estado B — já revelado (token=null no DB):
    banner amarelo: "Token já revelado."
    botão "Rotacionar token" → rotateToken():
      → edge function rotate-token: gera novo raw token, salva hash, deleta anterior
      → retorna novo token → exibir (mesmo fluxo de estado A)

  estado C — welcome=true na URL:
    QuickStart guide acima do token:
      4 passos: instalar CLI · configurar VECTORA_TOKEN · rodar vectora · convidar time
```

### dashboard/license.tsx — LicenseStatus

```
data: useQuery(['subscription'], getSubscription)
      + Realtime invalidation do route.tsx

<LicenseStatus>
  Plano + status badge:
    trialing  → "Trial ativo" (verde)
    active    → "Ativo" (verde)
    past_due  → "Pagamento pendente" (amarelo)
    canceled  → "Cancelado" (vermelho)
    expired   → "Expirado" (cinza)

  datas: início · término do trial · dias restantes (countdown)

  CTAs condicionais:
    [trialing] "Assinar Plus" + "Upgrade para Pro"
    [plus]     "Upgrade para Pro" + "Gerenciar assinatura"
    [pro]      "Gerenciar assinatura"
    [past_due] "Atualizar pagamento"
    [canceled/expired] "Reativar"

  histórico de license_checks:
    tabela: data · versão Vectora · resultado · IP (mascarado)
    staleTime: 5min
```

### dashboard/billing.tsx — BillingSection

```
data: useQuery(['subscription']) → subscription.country + subscription.provider

[BR — Asaas]:
  → createCheckout({ plan, country: 'BR' }) → edge function → { url }
  → redirect para Asaas Checkout (PIX · Boleto · Cartão)
  após pagamento: Asaas webhook → UPDATE subscriptions
  botão "Gerenciar assinatura" (se ativo) → Asaas customer portal

[INTL — Stripe]:
  → createCheckout({ plan, country: 'INTL' }) → edge function → { url }
  → redirect para Stripe Checkout
  após pagamento: Stripe webhook → UPDATE subscriptions
  botão "Gerenciar assinatura" → createPortal() → Stripe Customer Portal
```

### dashboard/api-keys.tsx — ApiKeysList

```
data: useQuery(['api-keys'], listApiKeys)

<ApiKeysList>
  tabela: nome · criado em · scopes · último uso · [Revogar]
  botão "Criar API key" → <CreateKeyModal>

<CreateKeyModal>
  campos: nome · scopes (multi-select: read / write / admin)
  onSubmit → createApiKey({ name, scopes })
    server fn: INSERT api_keys → retorna secret raw (show-once, mesmo padrão do token)
  exibe secret UMA vez após criação
  onClose → limpar secret do state

  revogar: DELETE api_keys.eq('id', id) com confirmação
```

### dashboard/account.tsx — AccountSection

```
<AccountSection>
  <ProfileForm>
    campos: nome completo · country (BR/INTL) · idioma preferido
    onSave → UPDATE profiles

  seção Segurança:
    botão "Alterar senha" → sendMagicLink(email) → toast "Link enviado"

  seção GDPR:
    botão "Exportar meus dados"
      → exportData(): adminClient busca profile + subscription + license_checks
      → gera ZIP JSON → download
    botão "Deletar conta"
      → confirmação: digitar email para confirmar
      → deleteAccount(): envia email → soft_delete_at = now()
      → sign out + redirect /
      → cron job hard delete após 30 dias
```

---

## Server Functions

```
Todas via createServerFn() — executam no servidor (Nitro/Vercel)

AUTH
  getSession()
    → createSupabaseServerClient().auth.getUser()
    → retorna: User | null

  signUp(email, password, name, country, turnstileToken)
    → verifyTurnstile(token)  ← falha → throw
    → supabase.auth.signUp({ email, password, options: { data: { name, country } } })
    → session cookie setado via @supabase/ssr
    → retorna { user, redirect: '/dashboard?welcome=true' }

  signIn(email, password)
    → supabase.auth.signInWithPassword({ email, password })
    → session cookie setado
    → retorna { user }

  signOut()
    → supabase.auth.signOut()
    → limpa cookies

  sendMagicLink(email)
    → supabase.auth.signInWithOtp({ email })

TOKEN
  getToken()
    → adminClient.from('tokens').select('token').eq('user_id', uid).single()
    → se token != null:
        adminClient.from('tokens').update({ token: null })
        retorna { token: string }
    → se token == null:
        retorna { revealed: true }

  rotateToken()
    → invokeEdgeFunction('rotate-token')
    → edge fn: gera novo raw + hash → UPDATE tokens
    → retorna { token: string } (show-once)

SUBSCRIPTION
  getSubscription()
    → supabase.from('subscriptions').select('*').eq('user_id', uid).single()

  createCheckout(plan: 'plus'|'pro')
    → getSubscription() → determina country
    → invokeEdgeFunction('create-checkout', { plan, country })
    → retorna { url: string }

  createPortal()
    → invokeEdgeFunction('create-portal')
    → retorna { url: string }

API KEYS
  listApiKeys()
    → supabase.from('api_keys').select('id,name,scopes,created_at,last_used_at')

  createApiKey(name, scopes)
    → raw = crypto.randomUUID() (ou similar seguro)
    → hash = sha256(raw)
    → adminClient.from('api_keys').insert({ user_id, name, scopes, key_hash: hash })
    → retorna { secret: raw } — mostrar apenas uma vez

  revokeApiKey(id)
    → supabase.from('api_keys').delete().eq('id', id)

WAITLIST
  joinWaitlist(email, turnstileToken, source?)
    → verifyTurnstile(turnstileToken)
    → addToWaitlist({ email, source }) — já implementado em src/lib/leads.ts

GDPR
  exportData()
    → adminClient: SELECT profiles + subscriptions + license_checks + api_keys
    → ZIP JSON → retorna como blob download

  requestAccountDeletion()
    → envia email de confirmação (Resend)
    → adminClient.from('profiles').update({ soft_delete_at: now() })
    → supabase.auth.signOut()

ISSUES
  submitIssue(title, category, description, email, turnstileToken)
    → verifyTurnstile(turnstileToken)
    → adminClient.from('issues').insert({ title, category, description, email })
    → resend.emails.send({ to: 'support@vectora.company', ... })
```

---

## Estado e cache

```
TanStack Query (server + client, re-fetch automático):
  ['session']         → getSession()          staleTime: 5min
  ['subscription']    → getSubscription()     staleTime: 30s + invalidado por Realtime
  ['api-keys']        → listApiKeys()          staleTime: 1min
  ['license-checks']  → getLicenseHistory()   staleTime: 5min

URL params (TanStack Router search params, type-safe):
  /dashboard?welcome=true    → mostrar QuickStart
  /signup?plan=plus|pro      → pré-selecionar plano
  /pricing?currency=brl|usd  → toggle de moeda
  /login?redirect=...        → redirecionar após login

Ephemeral (useState local — NÃO cachear nem persistir):
  token raw             → limpar ao navegar (TokenReveal)
  api-key secret        → limpar ao fechar modal (CreateKeyModal)
  turnstile token       → válido 5min, não persistir

Supabase Realtime (montado em dashboard/route.tsx):
  channel: 'license_status'
  table: subscriptions, filter: user_id=eq.{uid}
  onInsert + onUpdate: queryClient.invalidateQueries(['subscription'])

Zustand store (src/store/auth.ts):
  session: User | null  ← espelhado do Supabase onAuthStateChange
  Usado por Header para CTA "Entrar" vs Avatar dropdown
```

---

## Emails transacionais

```
src/emails/ — React Email templates

welcome.tsx
  disparo: 1h após signup (via cron ou webhook on-signup)
  assunto: "Seu Vectora está pronto"
  conteúdo: link dashboard + quickstart 4 passos

trial-ending-7d.tsx
  disparo: 7 dias antes de trial_ends_at
  assunto: "Seu trial vence em 7 dias"
  CTA: "Assinar agora"

trial-ending-1d.tsx
  disparo: 1 dia antes de trial_ends_at
  assunto: "Último dia do trial"
  CTA urgente: "Assinar agora"

invoice-paid.tsx
  disparo: após PAYMENT_RECEIVED (Asaas) / invoice.paid (Stripe)
  conteúdo: confirmação de pagamento + link para dashboard

invoice-failed.tsx
  disparo: após PAYMENT_OVERDUE / invoice.payment_failed
  conteúdo: link para atualizar método de pagamento

magic-link.tsx
  disparo: sendMagicLink()
  assunto: "Link de acesso ao Vectora"

account-deleted.tsx
  disparo: após requestAccountDeletion()
  assunto: "Conta Vectora agendada para exclusão"
  conteúdo: "Sua conta será excluída em 30 dias. Clique aqui para cancelar."

waitlist-confirmation.tsx
  disparo: addToWaitlist() — já implementado
  assunto: "Você está na lista do Vectora"
```

---

## SEO por rota

```
Rotas com SSR completo (TanStack Start):
  / pricing faq support issues privacy terms cookies sla dpa login signup

Head por rota (via route.head()):
  title:      m.site_title() + " — " + nome da página
  description: m.site_description() contextual por rota
  og:image:   /api/og?title=...&desc=... (edge fn Satori/og)
  og:url:     APP_URL + pathname
  hreflang:   pt · en · es · fr · it · de · ru (todos 7 idiomas)
  canonical:  URL sem query params, com prefixo de idioma correto
  json-ld:
    /         → SoftwareApplication + Organization + WebSite (sitelinks searchbox)
    /pricing  → Product (Plus + Pro)
    /faq      → FAQPage
    /support  → ContactPage

Sitemap (edge function ou build-time):
  rotas públicas × 7 idiomas (PT sem prefixo, demais com /en/ /es/ etc.)
  frequência: / pricing → weekly; faq legais → monthly
  prioridade: / → 1.0; pricing → 0.9; faq → 0.7; legais → 0.3

Dashboard (/dashboard/*):
  <meta name="robots" content="noindex, nofollow">
  → também em robots.txt: Disallow: /dashboard/
```

---

## Estrutura de arquivos

```
src/
├── routes/
│   ├── __root.tsx
│   ├── index.tsx
│   ├── pricing.tsx
│   ├── faq.tsx
│   ├── support.tsx
│   ├── issues.tsx
│   ├── privacy.tsx  terms.tsx  cookies.tsx  sla.tsx  dpa.tsx
│   ├── signup.tsx   login.tsx
│   └── dashboard/
│       ├── route.tsx
│       ├── index.tsx
│       ├── billing.tsx
│       ├── api-keys.tsx
│       ├── account.tsx
│       └── license.tsx
│
├── components/
│   ├── landing/
│   │   ├── Hero.tsx
│   │   ├── ShowcaseGifs.tsx
│   │   │   └── ShowcaseCard.tsx
│   │   ├── AgenticFlowSection.tsx
│   │   │   └── AgenticDiagram.tsx     ← SVG inline
│   │   ├── RagFlowSection.tsx
│   │   │   └── RagDiagram.tsx         ← SVG inline
│   │   ├── TeamSetupSection.tsx
│   │   │   ├── SetupTimeline.tsx
│   │   │   └── TimelineStep.tsx
│   │   ├── WhySelfHosted.tsx
│   │   ├── PricingSection.tsx
│   │   │   └── PricingTable.tsx
│   │   └── WaitlistCta.tsx
│   │       └── WaitlistForm.tsx
│   ├── dashboard/
│   │   ├── Sidebar.tsx
│   │   ├── TokenReveal.tsx
│   │   ├── LicenseStatus.tsx
│   │   ├── BillingSection.tsx
│   │   ├── ApiKeysList.tsx
│   │   │   └── CreateKeyModal.tsx
│   │   └── AccountSection.tsx
│   └── shared/
│       ├── Header.tsx
│       ├── Footer.tsx
│       ├── LocaleSwitcher.tsx
│       ├── Turnstile.tsx
│       ├── FaqAccordion.tsx
│       └── LegalPage.tsx
│
├── server/fns/          ← createServerFn: auth, token, subscription, api-keys, gdpr
├── hooks/
│   ├── use-session.ts
│   ├── use-subscription.ts
│   └── use-api-keys.ts
├── store/
│   └── auth.ts          ← Zustand: session espelhada do Supabase listener
└── lib/
    ├── supabase/        ← client, server, admin, types ✓
    ├── email/           ← resend ✓
    ├── analytics/       ← plausible, ga4 ✓
    ├── turnstile.ts     ✓
    └── leads.ts         ✓

emails/                  ← React Email templates
supabase/
├── migrations/          ← K1: profiles, tokens, subscriptions, license_checks,
│                              payment_events, waitlist, api_keys, issues
└── functions/           ← on-signup, validate-license, rotate-token,
                              create-checkout, create-portal, webhooks

public/
├── gifs/
│   ├── showcase-chat.gif     [PLACEHOLDER durante dev]
│   ├── showcase-rag.gif      [PLACEHOLDER durante dev]
│   ├── showcase-code.gif     [PLACEHOLDER durante dev]
│   ├── showcase-plan.gif     [PLACEHOLDER durante dev]
│   ├── setup-root.gif        [PLACEHOLDER durante dev]
│   ├── setup-invite.gif      [PLACEHOLDER durante dev]
│   └── setup-project.gif     [PLACEHOLDER durante dev]
└── diagrams/
    ├── agentic-flow.svg
    └── rag-flow.svg
```

---

## Referência: Vectora Agent

Referência do backend Python (monorepo separado) para uso nos diagramas e copy do site.
Código-fonte em `agent/` (não rastreado pelo git, apenas referência local).

### Tools (src/tools/)

#### Filesystem (fs.py)

| Tool              | Categoria  | Destrutivo | Descrição                                                        |
| ----------------- | ---------- | ---------- | ---------------------------------------------------------------- |
| `file_read`       | filesystem | não        | Lê conteúdo completo de arquivo                                  |
| `file_edit`       | filesystem | sim        | Edita arquivo substituindo texto (old→new, replace_all opcional) |
| `file_write`      | filesystem | sim        | Cria ou sobrescreve arquivo completamente                        |
| `grep`            | filesystem | não        | Busca regex em arquivos (max 100 resultados)                     |
| `list_dir`        | filesystem | não        | Lista diretório (recursive opcional, respeita .gitignore)        |
| `terminal`        | filesystem | sim        | Shell async com streaming em tempo real (timeout 30s)            |
| `create_artifact` | artifacts  | não        | Cria documento estruturado em ~/.vectora/artifacts/{session_id}/ |

Tipos de artifact: `plan`, `spec`, `task_list`, `overview`, `guide`, `architecture`, `implementation`

#### Git (git.py)

| Tool           | Destrutivo | Descrição                                                |
| -------------- | ---------- | -------------------------------------------------------- |
| `git_status`   | não        | Branch ativa, staged, modified, untracked, ahead/behind  |
| `git_log`      | não        | Histórico de commits (n=10, branch opcional)             |
| `git_diff`     | não        | Diff do working tree ou contra ref                       |
| `git_branch`   | não/sim    | list / create / delete branches                          |
| `git_checkout` | sim        | Troca branch ou commit                                   |
| `git_commit`   | sim        | Cria commit; flag `all` para -a                          |
| `git_push`     | sim        | Push para remote (force opcional)                        |
| `git_pull`     | sim        | Pull do remote                                           |
| `git_stash`    | não/sim    | push / pop / list / drop                                 |
| `git_init`     | não        | Inicializa repo (idempotente)                            |
| `git_worktree` | sim        | list / add / remove worktrees (em ~/.vectora/worktrees/) |

#### GitHub CLI (gh.py)

| Tool               | Destrutivo | Descrição                                 |
| ------------------ | ---------- | ----------------------------------------- |
| `gh_pr_list`       | não        | Lista PRs (state: open/closed/merged/all) |
| `gh_pr_create`     | não        | Cria PR (draft opcional)                  |
| `gh_pr_view`       | não        | Detalhes de um PR                         |
| `gh_pr_merge`      | sim        | Merge de PR (method: squash/merge/rebase) |
| `gh_issue_list`    | não        | Lista issues (state + labels)             |
| `gh_issue_create`  | não        | Cria issue                                |
| `gh_issue_view`    | não        | Detalhes de issue                         |
| `gh_issue_comment` | não        | Adiciona comentário a issue               |

#### Web (web.py)

| Tool         | Descrição                                                                               |
| ------------ | --------------------------------------------------------------------------------------- |
| `web_search` | Busca web via Tavily (topic: general/news/finance; time_range; include/exclude_domains) |
| `fetch_url`  | Extrai conteúdo de URL via TavilyExtract                                                |

#### RAG (rag.py)

| Tool               | Destrutivo | Descrição                                                                      |
| ------------------ | ---------- | ------------------------------------------------------------------------------ |
| `embedding`        | não        | Enfileira doc para embedding assíncrono (fire-and-forget → LanceDB via Cohere) |
| `vector_search`    | não        | Busca vetorial LanceDB + reranker Cohere (limit=5)                             |
| `ingest_docs`      | não        | Indexa diretório inteiro (glob_pattern, respeita .gitignore + .vectoraignore)  |
| `manage_retriever` | sim        | list / delete / purge documentos do RAG por collection                         |

Collections LanceDB: `articles` (docs curados), `web_cache` (auto), `search` (Search Agent), `knowledge_base`

#### Memory (memory.py)

| Tool            | Descrição                                         |
| --------------- | ------------------------------------------------- |
| `save_memory`   | Salva memória com embedding Cohere (TTL opcional) |
| `get_memory`    | Recupera por chave (ou todas)                     |
| `search_memory` | Busca semântica em memórias (cosine similarity)   |
| `delete_memory` | Deleta memória por chave                          |

Namespace por prioridade: `user:{id}` → `workspace_{id}` → `session_{thread_id}` → `default_session`

#### Workspace (workspace.py)

| Tool                 | Descrição                                                      |
| -------------------- | -------------------------------------------------------------- |
| `workspace_describe` | Descreve workspace ativo via MANIFEST.md (gerado pelo curator) |
| `workspace_list`     | Lista todos os workspaces registrados                          |
| `bucket_summary`     | Resumo de um bucket específico (code/docs/notes/web_cache)     |

#### MCP (mcp.py)

| Tool            | Descrição                                                       |
| --------------- | --------------------------------------------------------------- |
| `call_mcp_tool` | Invoca tool de servidor MCP externo (stdio/SSE/streamable_http) |

---

### Agentes (src/agents/)

#### Orchestrator (orchestrator.py)

Agente generalista e ponto de entrada do grafo. Pode:

1. **Responder diretamente** — saudações, conhecimento, síntese, identidade
2. **Delegar** — cria instrução clara para sub-agent (não passa histórico bruto)
3. **Paralelizar** — despacha múltiplas tasks em asyncio.gather
4. **Criar artifacts** — planos, specs, guias salvos em ~/.vectora/artifacts/

Contexto enviado ao LLM:

- SystemMessage: AGENTS.md / CLAUDE.md do projeto (primeira vez)
- SystemMessage: prompt de instrução
- SystemMessage: bloco de contexto (session_id, tool chain, artifacts)
- Últimas 5 HumanMessages + últimas 2 AIMessages sem tool_calls

#### Coder Agent (coder.py)

Especializado em filesystem, terminal, git e implementação.
Recebe `ALL_TOOLS` — especialidade vem do system prompt.
Ferramentas por prioridade: `file_*` / `terminal` / `git_*` → RAG e indexação → web search → memory

#### Search Agent (search.py)

Especializado em pesquisa e recuperação de informação.
Recebe `ALL_TOOLS` — estratégia RAG-first, depois web.
Atua também como `rag_search_audit` — valida docs pós-rerank, pode corrigir a base.

#### RAG Subgraph (nodes/rag_subgraph.py)

Pipeline LangGraph de múltiplos nós (não uma função única):

```
START
  ↓
rag_expand_query   ← Multi-query (C2): LLM gera N variantes da query
  ↓
rag_retrieve       ← Hybrid RAG (C1): dense (Cohere embed) + sparse (BM25) + RRF merge
  ↓
rag_decide         ← avalia best_score dos docs
  ├── score ≥ 0.7  → rag_inject (direto, resultado bom)
  ├── score ≥ 0.4  → rag_rerank → rag_search_audit → rag_inject
  └── score < 0.4  → rag_websearch → rag_search_audit → rag_inject
                       (+ HyDE C3 quando score inicial baixo)

rag_search_audit:  Search Agent valida docs, pode chamar manage_retriever (delete),
                   fetch_url e embedding(collection="search") para corrigir a base
rag_inject:        Injeta contexto como SystemMessage(name="rag_context")
  ↓
Orchestrator (re-invocado para síntese → _is_post_rag() → _synthesize_after_rag() → END)
```

---

### Fluxo principal do grafo (graph.py)

```
User Input
    ↓
Orchestrator
    ├── respond directly ──────────────────────────────────────────→ END
    ├── routing_decision='coder' → Coder Agent (tool loop) ──────→ Orchestrator → END
    ├── routing_decision='search' → Search Agent (tool loop) ────→ Orchestrator → END
    ├── routing_decision='rag' → RAG Subgraph ────────────────────→ Orchestrator → END
    └── routing_decision='parallel' → parallel_dispatch ─────────→ Orchestrator → END
                                        (asyncio.gather de N agents)

process_retrieval:  nó que monitora ToolMessages de web_search →
                    passa por curate_and_enqueue (reranker + LLM judge) →
                    persiste apenas conteúdo aprovado no bucket web_cache
```

---

### API REST (src/api/handlers/)

| Handler         | Endpoints-chave                                                  |
| --------------- | ---------------------------------------------------------------- |
| `chat.py`       | POST /chat — mensagem → resposta streaming                       |
| `threads.py`    | CRUD de threads de conversa                                      |
| `workspaces.py` | CRUD de workspaces (cwd, trust, manifest)                        |
| `tools.py`      | GET /tools — lista todas as tools com metadata                   |
| `artifacts.py`  | CRUD de artifacts salvos                                         |
| `memory.py`     | CRUD de memórias por namespace                                   |
| `terminal.py`   | WebSocket streaming de output do terminal                        |
| `auth.py`       | Login / logout / session                                         |
| `oauth.py`      | OAuth providers                                                  |
| `license.py`    | validate-license endpoint (chamado pelo Vectora Agent a cada 6h) |
| `plugins.py`    | Gerenciamento de plugins                                         |
| `skills.py`     | Gerenciamento de skills                                          |
| `share.py`      | Compartilhar conversas                                           |
| `admin.py`      | Operações administrativas                                        |

---

### Diagrama para o site — fluxo simplificado para o público

O SVG de `agentic-flow.svg` deve representar a versão simplificada (não o grafo LangGraph completo):

```
[Usuário] → [Orchestrator]
               ├─→ [Coder Agent]   (código, arquivos, terminal)
               ├─→ [Search Agent]  (web, documentos, RAG)
               ├─→ [RAG Pipeline]  (base de conhecimento indexada)
               └─→ [Paralelo]      (múltiplos agentes ao mesmo tempo)
                        ↓
              [Resposta consolidada] → [Usuário]
```

O SVG de `rag-flow.svg` deve representar o pipeline real simplificado:

```
[Documento] → [Chunking] → [Embed (Cohere)] → [LanceDB]
                                                    ↓
[Pergunta] → [Multi-query] → [Hybrid Search] → [Reranker] → [LLM] → [Resposta + Fonte]
                                                    ↑
                                          (fallback: Web Search)
```
