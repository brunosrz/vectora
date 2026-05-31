# Vectora Company — Master Plan

> Plano mestre da **Vectora Company**, empresa de Bruno Soares. Cobre tudo
> fora do produto técnico (documentado no chat-first plan, blocos A–Z):
> billing, licença, site, wizards de onboarding, documentação, suporte,
> distribuição, marketing e legal. Nenhum bloco aqui é opcional para o
> lançamento — todos os 10 blocos serão entregues antes da campanha de
> influenciadores.

---

## Sumário (TOC)

| Bloco | Tema                                            | Depende de |
| ----- | ----------------------------------------------- | ---------- |
| **A** | Identidade & Legal — Empresa, marca e contratos | —          |
| **B** | Billing & Licença — Supabase + Stripe + Token   | A          |
| **C** | Vectora Agent — License Gate & VECTORA_TOKEN    | B          |
| **D** | Wizard CLI — `vectora setup` refactor           | C          |
| **E** | Wizard Chat — Onboarding pós-root               | C          |
| **F** | Site — vectora.company                          | B          |
| **G** | Documentação — docs.vectora.company             | F          |
| **H** | Suporte & Comunidade                            | F          |
| **I** | Distribuição & Kit de Lançamento                | F, G       |
| **J** | Marketing & Campanha de Influenciadores         | I          |

**Ordem de implementação:** `A → B → C → D + E (paralelo) → F → G → H → I → J`

---

## BLOCO A — Identidade & Legal

> **Contexto.** Antes de vender qualquer coisa, a empresa precisa de identidade
> clara (nome, marca, domínio), termos legais válidos e uma estrutura mínima
> de pessoa jurídica ou MEI para emitir cobranças e receber pagamentos.

### A1 — Estrutura jurídica

**Decisão:** abrir MEI ou ME no CNPJ de Bruno Soares.

- **MEI** (limite R$81k/ano): suficiente para o lançamento. Se a receita
  ultrapassar, migra para ME.
- **CNAE sugerido:** 6201-5/01 (Desenvolvimento de programas de computador
  sob encomenda) + 6202-3/00 (Desenvolvimento e licenciamento de programas
  de computador não customizáveis)
- **Conta bancária PJ:** Nubank PJ, Inter PJ ou C6 Bank PJ — zero tarifa,
  abertura digital, integração com Stripe via transferência internacional

**Ação:** abertura via portal do empreendedor (gov.br/mei) ou contador online
(Contabilizei, Agilize).

### A2 — Marca e domínio

**Domínio adquirido:** `vectora.company`

**Domínios adicionais a registrar:**

- `vectora.company` ✓ (já adquirido)
- `docs.vectora.company` — subdomínio (sem custo adicional)
- `api.vectora.company` — subdomínio para REST API pública (Bloco Z do chat-first)
- Considerar `vectora.dev` se disponível — domínio alternativo técnico

**Marca:**

- Nome: **Vectora**
- Registro de marca no INPI (opcional agora, recomendado em 6 meses quando
  houver receita para justificar o custo ~R$1.500)
- Identidade visual já existe (pássaro Vectora, paleta navy + azul claro,
  JetBrains Mono como fonte de marca)

### A3 — Termos legais

Dois documentos obrigatórios para o site (Bloco F) e para o billing (Bloco B):

**Política de Privacidade** (`/privacy`):

- Quais dados são coletados: email, nome, logs de validação de token, dados
  de pagamento (via Stripe — não armazenamos cartão)
- O que **não** coletamos: conteúdo de conversas, arquivos, código — self-hosted
  significa que os dados ficam no servidor do cliente
- Base legal: LGPD (Art. 7º, I — consentimento; Art. 7º, V — execução de contrato)
- Retenção: dados de conta mantidos enquanto a conta existir; logs de licença
  por 90 dias; dados de pagamento pelo prazo legal (5 anos)
- DPO: Bruno Soares (email de contato)
- GDPR: para usuários europeus, mesmo tratamento com adição de direitos GDPR
  (portabilidade, esquecimento)

**Termos de Uso / EULA** (`/terms`):

- Definição de licença: licença de uso não exclusiva, não transferível,
  não sublicenciável
- O que é permitido: uso comercial dentro da organização do licenciado,
  instalação em múltiplos servidores da mesma empresa dentro do mesmo plano
- O que não é permitido: redistribuição, sublicenciamento, engenharia reversa
  para fins de concorrência, revenda de acesso
- Trial: 30 dias gratuitos do plano Plus; sem cartão obrigatório no trial
- Cancelamento: a qualquer momento; acesso mantido até o fim do período pago
- Limitação de responsabilidade: software fornecido "as is"; Vectora Company
  não se responsabiliza por perdas de dados em ambiente self-hosted
- Foro: comarca de São João Batista do Glória/MG ou eletrônico via JFMG

**Nota:** redigir com linguagem clara, não apenas juridiquês. O usuário deve
conseguir ler e entender sem advogado.

### A4 — Email e comunicação

- **Email principal:** bruno@vectora.company (Google Workspace ou Zoho Mail)
- **Email de suporte:** support@vectora.company
- **Email de billing:** billing@vectora.company (Stripe envia notificações
  por aqui)
- **WhatsApp Business:** número pessoal com perfil Vectora Company
- **GitHub Organization:** `vectora-company` (para repositórios públicos
  de documentação, issues, SDK)

### Verificação (Bloco A)

- MEI/ME aberto com CNPJ ativo
- Conta bancária PJ operacional
- `vectora.company` apontando para Vercel (Bloco F)
- Emails `@vectora.company` funcionando
- Termos e Política redigidos e revisados

---

## BLOCO B — Billing & Licença: Supabase + Stripe + Token

> **Contexto.** O VECTORA_TOKEN é o vínculo entre a conta de billing externa
> (Supabase + Stripe) e o Vectora Agent instalado no servidor do cliente.
> A conta Supabase é a identidade de billing — distinta dos usuários internos
> do Vectora Agent (root/member/viewer). Um usuário pode ter uma conta Supabase
> (billing) e dezenas de usuários internos no mesmo servidor Vectora.

### B1 — Schema do banco (Supabase Postgres)

**`profiles`** — estende `auth.users`:

```sql
id          uuid PRIMARY KEY REFERENCES auth.users(id)
full_name   text
company     text | null
created_at  timestamptz DEFAULT now()
```

**`tokens`** — VECTORA_TOKEN por usuário:

```sql
id          uuid PRIMARY KEY DEFAULT gen_random_uuid()
user_id     uuid REFERENCES profiles(id) ON DELETE CASCADE
token       text | null        -- raw, exibido UMA vez e apagado
token_hash  text UNIQUE NOT NULL  -- SHA-256, usado para validação
created_at  timestamptz DEFAULT now()
rotated_at  timestamptz | null
```

**`subscriptions`** — licença ativa:

```sql
id                    uuid PRIMARY KEY DEFAULT gen_random_uuid()
user_id               uuid REFERENCES profiles(id) ON DELETE CASCADE
tier                  text NOT NULL  -- 'plus' | 'pro'
status                text NOT NULL  -- 'trialing' | 'active' | 'canceled' | 'expired'
trial_ends_at         timestamptz | null
current_period_start  timestamptz NOT NULL
current_period_end    timestamptz NOT NULL
provider              text NOT NULL  -- 'stripe' | 'manual'
provider_sub_id       text | null    -- Stripe subscription ID
created_at            timestamptz DEFAULT now()
updated_at            timestamptz DEFAULT now()
```

**`license_checks`** — log de validações:

```sql
id               uuid PRIMARY KEY DEFAULT gen_random_uuid()
user_id          uuid REFERENCES profiles(id)
token_hash       text NOT NULL
result           text NOT NULL  -- 'valid' | 'invalid' | 'expired' | 'trial'
tier             text | null
ip               text | null
vectora_version  text | null
checked_at       timestamptz DEFAULT now()
```

### B2 — Edge Function: `on-signup`

Trigger automático ao criar conta. Gera token + trial de 30 dias:

```typescript
// supabase/functions/on-signup/index.ts
// Trigger: auth.users INSERT via Database Webhook

export async function handler(req: Request) {
  const { record } = await req.json();
  const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

  // 1. Criar profile
  await supabase.from("profiles").insert({ id: record.id });

  // 2. Gerar VECTORA_TOKEN: "vct_" + 96 chars hex
  const raw =
    "vct_" +
    Array.from(crypto.getRandomValues(new Uint8Array(48)))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  const tokenHash = await sha256(raw);

  // 3. Salvar token (raw para exibição única, hash para validação)
  await supabase.from("tokens").insert({
    user_id: record.id,
    token: raw,
    token_hash: tokenHash,
  });

  // 4. Trial 30 dias — Plus
  const trialEnd = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
  await supabase.from("subscriptions").insert({
    user_id: record.id,
    tier: "plus",
    status: "trialing",
    trial_ends_at: trialEnd.toISOString(),
    current_period_start: new Date().toISOString(),
    current_period_end: trialEnd.toISOString(),
    provider: "manual",
  });
}
```

### B3 — Edge Function: `validate-license`

Chamada pelo Vectora Agent a cada boot (com cache local de 6h):

```typescript
// POST { token: string, vectora_version?: string }
// Retorna: { valid, tier, status, days_remaining, period_end, trial_ends_at? }

export async function handler(req: Request) {
  const { token, vectora_version } = await req.json();
  const tokenHash = await sha256(token);

  const { data: tokenRow } = await supabase
    .from("tokens")
    .select("user_id")
    .eq("token_hash", tokenHash)
    .single();

  if (!tokenRow) return json({ valid: false, reason: "token_invalid" }, 401);

  const { data: sub } = await supabase
    .from("subscriptions")
    .select("*")
    .eq("user_id", tokenRow.user_id)
    .order("created_at", { ascending: false })
    .limit(1)
    .single();

  const now = new Date();
  const periodEnd = new Date(sub.current_period_end);
  const daysRemaining = Math.ceil((+periodEnd - +now) / 86400000);
  const expired = now > periodEnd && sub.status !== "active";

  // Auditoria
  await supabase.from("license_checks").insert({
    user_id: tokenRow.user_id,
    token_hash: tokenHash,
    result: expired ? "expired" : sub.status === "trialing" ? "trial" : "valid",
    tier: sub.tier,
    vectora_version,
  });

  if (expired)
    return json({ valid: false, reason: "expired", tier: sub.tier }, 402);

  return json({
    valid: true,
    tier: sub.tier,
    status: sub.status,
    trial_ends_at: sub.trial_ends_at,
    period_end: sub.current_period_end,
    days_remaining: daysRemaining,
  });
}
```

**Rate limiting:** máx 20 validações/hora por token (Supabase rate limit).
Cache local de 6h no Agent — não valida a cada comando, só no boot ou
quando o cache expirar.

### B4 — Edge Function: `get-token` (reveal único)

```typescript
// GET /functions/v1/get-token — auth: Supabase JWT
// Retorna token raw UMA vez e apaga do banco

export async function handler(req: Request) {
  const user = await getAuthUser(req);
  const { data } = await supabase
    .from("tokens")
    .select("token")
    .eq("user_id", user.id)
    .single();

  if (!data?.token) {
    return json({
      revealed: false,
      message:
        "Token já foi revelado. Use 'Rotacionar token' para gerar um novo.",
    });
  }

  // Apaga raw — apenas hash permanece
  await supabase.from("tokens").update({ token: null }).eq("user_id", user.id);

  return json({ revealed: true, token: data.token });
}
```

### B5 — Edge Function: `rotate-token`

```typescript
// POST /functions/v1/rotate-token — auth: Supabase JWT
// Invalida token anterior, gera novo

export async function handler(req: Request) {
  const user = await getAuthUser(req);

  const raw =
    "vct_" +
    Array.from(crypto.getRandomValues(new Uint8Array(48)))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  const tokenHash = await sha256(raw);

  await supabase
    .from("tokens")
    .update({
      token: raw,
      token_hash: tokenHash,
      rotated_at: new Date().toISOString(),
    })
    .eq("user_id", user.id);

  return json({
    token: raw,
    message: "Token rotacionado. Salve agora — não será exibido novamente.",
  });
}
```

### B6 — Stripe: produtos e checkout

**Produtos no Stripe:**

- `vectora_plus_monthly` — $7 USD / R$20 BRL (localização por país)
- `vectora_pro_monthly` — $20 USD / R$55 BRL

**Edge Functions adicionais:**

- `create-checkout` — cria sessão Stripe Checkout com `currency` detectado
  por `Accept-Language` ou IP (`brl` para Brasil, `usd` para demais)
- `stripe-webhook` — processa eventos:
  - `checkout.session.completed` → `status = 'active'`, atualiza tier
  - `invoice.payment_succeeded` → renova `current_period_end`
  - `customer.subscription.updated` → atualiza tier (upgrade/downgrade)
  - `customer.subscription.deleted` → `status = 'canceled'`
- `create-portal` — Stripe Customer Portal para gerenciar/cancelar assinatura

**Desconto de upgrade:** ao fazer upgrade de Plus para Pro, Stripe aplica
crédito proporcional dos dias restantes do Plus automaticamente (proration).

### B7 — RLS (Row Level Security)

```sql
-- profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own_profile" ON profiles FOR ALL USING (auth.uid() = id);

-- tokens
ALTER TABLE tokens ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own_token" ON tokens FOR ALL USING (auth.uid() = user_id);

-- subscriptions: leitura própria; escrita apenas service_role
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own_subscription_read" ON subscriptions
  FOR SELECT USING (auth.uid() = user_id);

-- license_checks: sem acesso direto do client
ALTER TABLE license_checks ENABLE ROW LEVEL SECURITY;
-- sem policy pública — apenas service_role via Edge Functions
```

### Estrutura de arquivos (Bloco B)

```
supabase/
├── migrations/
│   ├── 001_profiles.sql
│   ├── 002_tokens.sql
│   ├── 003_subscriptions.sql
│   └── 004_license_checks.sql
└── functions/
    ├── _shared/
    │   ├── hash.ts          (sha256 helper)
    │   ├── auth.ts          (getAuthUser — valida JWT Supabase)
    │   └── stripe.ts        (cliente Stripe)
    ├── on-signup/           (B2)
    ├── validate-license/    (B3)
    ├── get-token/           (B4)
    ├── rotate-token/        (B5)
    ├── create-checkout/     (B6)
    ├── stripe-webhook/      (B6)
    └── create-portal/       (B6)
```

### Verificação (Bloco B)

- Criar conta → profiles + tokens + subscriptions(trialing, 30d) gerados
- `get-token` → retorna raw, apaga do banco; segunda chamada → `revealed: false`
- `validate-license` com token válido → `{valid: true, tier: "plus", status: "trialing", days_remaining: 30}`
- `validate-license` com token inválido → `{valid: false, reason: "token_invalid"}`
- Assinar Plus via Stripe Checkout → webhook → `status: "active"`
- Upgrade para Pro → tier atualizado, crédito proporcional aplicado
- Cancelar via portal → `status: "canceled"`, acesso até fim do período
- RLS: usuário A não acessa token do usuário B

---

## BLOCO C — Vectora Agent: License Gate & VECTORA_TOKEN

> **Contexto.** O Vectora Agent valida o VECTORA_TOKEN no Supabase a cada
> boot. Sem token válido, comandos que inicializam o agente são bloqueados.
> O tier determina quais backends estão disponíveis (Plus: SQLite/LanceDB;
> Pro: PostgreSQL/Qdrant/Redis).

### C1 — `vectora/services/license.py` (novo)

```python
import hashlib, time, json, httpx
from pathlib import Path
from typing import TypedDict

VALIDATE_URL = "https://<project>.supabase.co/functions/v1/validate-license"
CACHE_TTL = 6 * 3600        # 6 horas
OFFLINE_TTL = 48 * 3600     # 48h — graceful degradation
CACHE_PATH = Path("~/.vectora/license_cache.json").expanduser()

class LicenseInfo(TypedDict):
    valid: bool
    tier: str | None        # 'plus' | 'pro' | None
    status: str             # 'trialing' | 'active' | 'expired' | 'invalid'
    days_remaining: int
    period_end: str | None
    trial_ends_at: str | None
    cached_at: float

async def validate_token(token: str, version: str) -> LicenseInfo:
    cached = _load_cache()
    if cached and (time.time() - cached["cached_at"]) < CACHE_TTL:
        return cached

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(VALIDATE_URL,
                json={"token": token, "vectora_version": version})
    except httpx.RequestError:
        # Graceful degradation: usa cache se < 48h
        if cached and (time.time() - cached["cached_at"]) < OFFLINE_TTL:
            cached["_offline"] = True
            return cached
        return {"valid": False, "status": "offline", "tier": None}

    if resp.status_code == 401:
        return {"valid": False, "status": "invalid", "tier": None}
    if resp.status_code == 402:
        data = resp.json()
        return {"valid": False, "status": "expired", "tier": data.get("tier")}

    info = resp.json()
    info["cached_at"] = time.time()
    _save_cache(info)
    return info

def require_pro(info: LicenseInfo, feature: str):
    if info.get("tier") != "pro":
        raise LicenseError(
            f"'{feature}' requer o plano Pro.\n"
            f"Faça upgrade em https://vectora.company/pricing"
        )
```

### C2 — Gate no startup (`vectora/main.py`)

Aplicado antes de: `chat`, `server chat`, `server mcp`, `server headless`.
Isento de: `setup`, `auth`, `license`, `--version`, `--help`.

```python
async def check_license() -> LicenseInfo:
    token = settings.vectora_token
    if not token:
        console.print("[red]❌ VECTORA_TOKEN não configurado.[/red]")
        console.print("   Execute: [bold]vectora setup[/bold]")
        console.print("   Ou acesse: [bold]https://vectora.company[/bold]")
        raise SystemExit(1)

    info = await validate_token(token, __version__)

    if not info["valid"]:
        status = info.get("status")
        msgs = {
            "expired":  "❌ Licença expirada. Renove em https://vectora.company/dashboard",
            "invalid":  "❌ Token inválido. Verifique em https://vectora.company/dashboard",
            "offline":  "⚠  Sem conexão e cache expirado (>48h). Conecte-se para validar.",
        }
        console.print(f"[red]{msgs.get(status, '❌ Licença inválida.')}[/red]")
        raise SystemExit(1)

    # Banner de status
    tier = info["tier"].upper()
    days = info["days_remaining"]
    if info.get("_offline"):
        console.print(f"[yellow]⚠  Modo offline — usando cache ({tier})[/yellow]")
    elif info["status"] == "trialing":
        console.print(f"[yellow]⏳ Trial — {days} dias restantes ({tier})[/yellow]")
    else:
        console.print(f"[green]✓ Vectora {tier} — {days} dias até renovação[/green]")

    return info
```

### C3 — Gate de features por tier

Features bloqueadas no plano Plus (requerem Pro):

- PostgreSQL como checkpointer (`VECTORA_CHECKPOINTER=postgres`)
- Qdrant como vector store (`VECTORA_VECTOR_STORE=qdrant`)
- Redis cache layer (`VECTORA_CACHE=redis`)
- Multi-worker simultâneo no server (>1 worker uvicorn)

Verificação em `vectora/config/settings.py` ao inicializar backends:

```python
if settings.checkpointer == "postgres":
    require_pro(license_info, "PostgreSQL checkpointer")
if settings.vector_store == "qdrant":
    require_pro(license_info, "Qdrant vector store")
```

### C4 — Armazenamento do token

Ordem de precedência:

1. Variável de ambiente `VECTORA_TOKEN`
2. `~/.vectora/config.toml` → `[license] token = "vct_..."`
3. Keyring do OS (Windows Credential Manager, macOS Keychain, Secret Service)

### C5 — Subcomando `vectora license`

```
vectora license           → exibe status atual
vectora license check     → força revalidação (ignora cache)
vectora license set <tok> → salva token em config.toml
vectora license clear     → remove token
```

Saída de `vectora license`:

```
  Vectora Plus — Trial
  ├ Status:         Trialing
  ├ Dias restantes: 28
  ├ Período:        01/06/2026 → 01/07/2026
  └ Renovar em:    https://vectora.company/dashboard
```

### Verificação (Bloco C)

- Sem token → `vectora chat` exibe erro, redireciona para setup
- Token inválido → erro claro com URL
- Token válido trial → banner amarelo com dias
- Token válido ativo → banner verde
- Feature Pro em Plus → LicenseError com link de upgrade
- Offline < 48h → inicia com aviso de modo offline
- Offline > 48h → bloqueia com mensagem de conectividade

---

## BLOCO D — Wizard CLI: `vectora setup` refactor

> **Contexto.** O `vectora setup` atual tem wizard básico mas não pede
> VECTORA_TOKEN. Refactor completo para onboarding guiado do zero ao primeiro
> `vectora chat` em 3 passos.

### D1 — Fluxo completo

```
╔══════════════════════════════════════════════════╗
║           Bem-vindo ao Vectora Setup             ║
║     Vamos configurar tudo em menos de 5 min      ║
╚══════════════════════════════════════════════════╝

Passo 1/3 — Licença
──────────────────────────────────────────────────
  Você já tem uma conta no Vectora?

  [1] Sim — já tenho meu VECTORA_TOKEN
  [2] Não — quero criar uma conta grátis (trial 30 dias)
  [3] Perdi meu token

  → [2/3]: abre vectora.company no browser e aguarda Enter
  → Cole seu VECTORA_TOKEN: ••••••••••••••••••••••••••

  Validando... ✓ Vectora Plus — Trial (30 dias)

Passo 2/3 — Provedor de IA
──────────────────────────────────────────────────
  Qual provedor de IA você quer usar?

  [1] Google Gemini  (recomendado — plano gratuito disponível)
  [2] OpenAI         (GPT-4o, o3, o4-mini)
  [3] Anthropic      (Claude 4.x)
  [4] Ollama         (local, zero custo de API)
  [5] Outro          (configuro manualmente depois)

  → API Key: ••••••••••••••••••••••••••
  Testando conexão... ✓ Conexão estabelecida (gemini-2.5-flash)

Passo 3/3 — Cohere (RAG)
──────────────────────────────────────────────────
  O Vectora usa Cohere para busca semântica e reranking.
  Crie uma conta gratuita em: https://cohere.com

  → COHERE_API_KEY: ••••••••••••••••••••••••••
  Testando conexão... ✓ embed-multilingual-v3.0 disponível

  [Pular por agora — funciona sem RAG, mas com capacidade reduzida]

──────────────────────────────────────────────────
✓ Configuração salva em ~/.vectora/config.toml
✓ Vectora pronto para uso!

  Próximo passo:  vectora chat
  Dashboard:      https://vectora.company/dashboard
  Documentação:   https://docs.vectora.company
```

### D2 — Comportamento em re-execução

Se `~/.vectora/config.toml` já existe, mostra valores mascarados por seção
e pergunta se quer reconfigurar cada uma individualmente:

```
Configuração existente detectada:

  Licença:    vct_••••••••••••••• (Plus — Trial, 28 dias)
  Provedor:   Google Gemini
  Cohere:     ••••••••••••••••••• ✓

  Reconfigurar alguma seção? [licença / provedor / cohere / não]
```

### D3 — Implementação

```python
# vectora/cli/setup.py (refactor completo)

import webbrowser
import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm

async def run_setup():
    console = Console()
    _print_welcome(console)

    token   = await _step_license(console)
    llm     = await _step_llm(console)
    cohere  = await _step_cohere(console)

    _write_config(token=token, llm=llm, cohere=cohere)
    _print_success(console)

async def _step_license(console: Console) -> str:
    console.rule("[bold]Passo 1/3 — Licença")
    choice = Prompt.ask(
        "Você já tem um VECTORA_TOKEN?",
        choices=["1", "2", "3"],
        default="1"
    )
    if choice in ("2", "3"):
        url = "https://vectora.company/signup" if choice == "2" \
              else "https://vectora.company/dashboard"
        webbrowser.open(url)
        console.print(f"[dim]Abrindo {url}...[/dim]")
        Prompt.ask("Pressione Enter após copiar seu token")

    token = Prompt.ask("Cole seu VECTORA_TOKEN", password=True)

    with console.status("Validando..."):
        info = await validate_token(token, __version__)

    if not info["valid"]:
        console.print(f"[red]❌ Token inválido: {info['status']}[/red]")
        raise typer.Exit(1)

    tier, days = info["tier"].upper(), info["days_remaining"]
    console.print(f"[green]✓ Vectora {tier} — {info['status']} ({days} dias)[/green]")
    return token
```

### Verificação (Bloco D)

- `vectora setup` fresh → wizard 3 passos completo
- Token inválido → erro, não avança
- Pular Cohere → avança com aviso de capacidade reduzida
- Re-execução → mostra config existente, pergunta o que reconfigurar
- `vectora chat` sem token → redireciona para `vectora setup`
- Config salva em `~/.vectora/config.toml` com permissão `0600`

---

## BLOCO E — Wizard Chat: Onboarding pós-root

> **Contexto.** O chat tem o setup do usuário root (Bloco C do chat-first).
> Após criar o root, deve iniciar um wizard de configuração de envs —
> equivalente ao `vectora setup` mas na interface web. Detectado via flag
> `vectora-onboarding-done-{userId}` no localStorage.

### E1 — Fluxo do wizard (modal multi-step)

**Passo 1 — VECTORA_TOKEN:**

```
Configure sua Licença

O token vincula sua licença ao servidor Vectora.
Obtenha em: vectora.company/dashboard

[____________________________]  Cole seu VECTORA_TOKEN

                           [Pular por agora]  [Validar e continuar →]
```

- Valida via `POST /api/license/validate`
- Exibe tier + dias restantes após validação bem-sucedida
- Salva via `POST /api/auth/envs` com `{key: "VECTORA_TOKEN", value: token}`

**Passo 2 — Provedor de IA:**

```
Configure seu Provedor de IA

  ○ Google Gemini  (recomendado — gratuito para começar)
  ○ OpenAI
  ○ Anthropic
  ○ Ollama (local)

API Key: [____________________________]

                    [← Voltar]  [Pular por agora]  [Testar e continuar →]
```

**Passo 3 — Cohere:**

```
Configure o Cohere (RAG)

Usado para busca semântica e reranking na sua base de conhecimento.
Conta gratuita em: cohere.com

COHERE_API_KEY: [____________________________]

                    [← Voltar]  [Pular por agora]  [Finalizar →]
```

**Passo 4 — Conclusão:**

```
✓  Vectora configurado!

Próximos passos:
  → Adicionar outros usuários — Configurações → Administração
  → Criar seu primeiro workspace — clique na pasta no header
  → Começar a conversar

                                          [Ir para o chat →]
```

### E2 — Banner de licença no chat

Exibido no header do chat conforme status da licença:

```
# Sem token (laranja, não-bloqueante)
⚠ VECTORA_TOKEN não configurado. Configure em Configurações → Envs
  ou execute vectora setup no CLI.  [Configurar →]

# Trial expirando ≤ 7 dias (amarelo)
⏳ Trial expira em 5 dias. Assine para continuar.  [Assinar →]

# Licença expirada (vermelho, bloqueia o input)
❌ Licença expirada. Renove em vectora.company para continuar.  [Renovar →]
```

### E3 — Novo endpoint: `GET /license/status`

Lê cache de `validate_token()` e retorna status atual para o frontend:

```python
# vectora/api/handlers/license.py (novo)

@router.get("/license/status")
async def get_license_status():
    token = settings.vectora_token
    if not token:
        return {"configured": False}
    info = await validate_token(token, __version__)
    return {"configured": True, **info}
```

### E4 — Implementação frontend

```typescript
// chat/components/onboarding/setup-wizard.tsx (novo)
// Modal multi-step — abre automaticamente no primeiro login do root

const STEPS = [
  { id: "token", title: "Licença", component: TokenStep },
  { id: "llm", title: "Provedor de IA", component: LlmStep },
  { id: "cohere", title: "RAG (Cohere)", component: CohereStep },
  { id: "done", title: "Pronto!", component: DoneStep },
];

// chat/components/layout/license-banner.tsx (novo)
// Lê GET /api/license/status a cada boot do chat
```

### Verificação (Bloco E)

- Primeiro login root → wizard abre automaticamente
- Colar token → valida → exibe tier + dias
- Pular qualquer passo → fecha com banner correspondente
- Segundo login → wizard não abre (flag salva)
- Trial ≤ 7 dias → banner amarelo
- Sem token → banner laranja
- Licença expirada → banner vermelho + input bloqueado

---

## BLOCO F — Site: vectora.company

> **Stack:** Next.js 15 + Tailwind + shadcn/ui + Supabase Auth SSR +
> Stripe. Deploy: Vercel (integração Supabase nativa). Repo separado:
> `vectora-company/site`.

### F1 — Landing Page (`/`)

**Estrutura (scroll único, seções âncora):**

**Hero:**

- Tagline: _"Your AI. Your Data. Your Server."_
- Sub (1 linha): o que o Vectora faz em menos de 15 palavras
- CTAs: "Começar trial grátis — 30 dias" (→ `/signup`) + "Ver demo" (âncora)
- Vídeo 1 em loop, sem voz: chat em uso (workspace aberto, agente respondendo)
  — primeiro e mais impactante

**O que é o Vectora (texto + vídeos intercalados):**
Prosa fluida explicando o produto para o público-alvo (empresas tech + devs
solo). Vídeos intercalados sem voz (1 por seção):

1. Uso do chat (RAG respondendo sobre o projeto)
2. Instalação em VPS (30–60s, `pip install vectora` + `vectora setup`)
3. Workspace + indexação de docs
4. Acesso multi-usuário via chat web

**O que é RAG (diagrama animado SVG):**
Ciclo de vida visual: `Documento → Embedding → Vector Store → Query →
Vector Search → Reranker → LLM → Resposta`. Técnico mas acessível —
público-alvo são devs.

**Diagramas de arquitetura:**

- Diagrama 1: Três modos de uso — CLI, MCP (sub-agente), Chat Web
- Diagrama 2: Agentes especializados (Orchestrator → RAG / Search / Coder)
- Diagrama 3: Empresa com Vectora em VPS, time acessando via chat,
  cada dev com seu workspace e API key própria

**Planos (`#pricing`):**

| Feature                     | Plus      | Pro        |
| --------------------------- | --------- | ---------- |
| Trial gratuito              | 30 dias   | —          |
| CLI + MCP                   | ✓         | ✓          |
| Vectora Chat (web)          | —         | ✓          |
| SQLite + LanceDB            | ✓         | ✓          |
| PostgreSQL + Qdrant + Redis | —         | ✓          |
| Multi-thread (acesso web)   | —         | ✓          |
| **Preço**                   | $7 · R$20 | $20 · R$55 |
|                             | [Começar] | [Assinar]  |

**Social proof:**
Espaço reservado pré-lançamento: "Seja um dos primeiros — trial grátis,
sem cartão." Substituído por depoimentos reais após lançamento.

**Footer:**
Docs, FAQ, Suporte, Issues, Política de Privacidade, Termos de Uso,
WhatsApp (link direto `wa.me/...`).

### F2 — Auth (`/signup`, `/login`)

**`/signup`:**

- Campos: nome, email, senha
- Supabase Auth → trigger `on-signup` (B2) cria token + trial automaticamente
- Após signup: redirect para `/dashboard?welcome=true`

**`/login`:**

- Email + senha
- "Esqueci a senha" → Supabase Magic Link por email
- Sem OAuth por ora (Google pode ser adicionado depois)

### F3 — Dashboard (`/dashboard`)

**Seção Token:**

```
Seu VECTORA_TOKEN
─────────────────────────────────────────────────────
  [ Clique para revelar seu token — exibido uma única vez ]
                                          [Rotacionar token]

  ⚠ Copie e guarde. Após fechar, não poderá ser exibido novamente.
     Se perder, use "Rotacionar token".
```

Após reveal: exibe token em fonte mono com botão de cópia. Fecha → não
exibe mais (apenas hash permanece no banco).

**Seção Status da Licença:**

```
Plano: Plus — Trial
──────────────────────────────────────────────
Início:            01/06/2026
Término do trial:  01/07/2026
Dias restantes:    30 dias
Status:            ⏳ Trial ativo

[Assinar Plus — R$20/mês]   [Fazer upgrade para Pro — R$55/mês]
```

Para assinantes ativos:

```
Plano: Pro — Ativo
Próxima cobrança: 01/07/2026 (R$55,00)
[Gerenciar assinatura]   [Cancelar]
```

**Seção Histórico de Validações** (últimas 5):

```
01/06/2026 14:32 — ✓ válido (Plus, trial) — Vectora v0.5.0
01/06/2026 08:15 — ✓ válido (Plus, trial) — Vectora v0.5.0
```

**Guia de início rápido** (apenas em `?welcome=true`):

```
1. Revele e copie seu VECTORA_TOKEN acima
2. pip install vectora
3. vectora setup  (cole o token quando solicitado)
4. vectora chat   (começar a usar)
```

### F4 — Pricing (`/pricing`)

Página dedicada com tabela comparativa completa de todas as features,
FAQ de preços inline e CTAs.

### F5 — FAQ (`/faq`)

Categorias:

- **Geral:** o que é, o que significa self-hosted, meus dados ficam onde
- **Instalação:** requisitos, Windows/macOS/Linux, VPS vs máquina local
- **Licença & Billing:** trial, expiração, cancelamento, meios de pagamento, desconto
- **Técnico:** o que é RAG, diferença Plus/Pro, API keys próprias, VECTORA_TOKEN

### F6 — Issues & Requests (`/issues`)

- Formulário: título, descrição, categoria (bug / feature / docs)
- Submete via GitHub Issues API para repositório público de issues
- Link direto WhatsApp para suporte humano

### F7 — Páginas legais (`/privacy`, `/terms`)

Conteúdo conforme A3. Linguagem clara, não só juridiquês.

### F8 — i18n

Idiomas iniciais: `pt-BR` (default) e `en`.
Implementação: `next-intl`. Vídeos sem voz — sem necessidade de versionar
por idioma. Diagramas SVG em inglês (linguagem universal técnica).

### Estrutura de arquivos (Bloco F)

```
vectora-site/                     (repo: vectora-company/site)
├── app/
│   └── [locale]/
│       ├── page.tsx              (landing — F1)
│       ├── pricing/page.tsx      (F4)
│       ├── faq/page.tsx          (F5)
│       ├── issues/page.tsx       (F6)
│       ├── privacy/page.tsx      (F7)
│       ├── terms/page.tsx        (F7)
│       ├── login/page.tsx        (F2)
│       ├── signup/page.tsx       (F2)
│       └── dashboard/page.tsx    (F3)
├── components/
│   ├── landing/
│   │   ├── hero.tsx
│   │   ├── video-section.tsx
│   │   ├── rag-diagram.tsx       (SVG animado)
│   │   ├── arch-diagrams.tsx
│   │   └── pricing-table.tsx
│   └── dashboard/
│       ├── token-reveal.tsx
│       ├── license-status.tsx
│       ├── license-history.tsx
│       └── quick-start.tsx
├── lib/
│   ├── supabase/
│   │   ├── client.ts             (browser client)
│   │   └── server.ts             (SSR client)
│   └── stripe/client.ts
└── messages/
    ├── pt-BR.json
    └── en.json
```

### Verificação (Bloco F)

- Landing carrega com vídeo 1 em loop, sem som
- Signup → dashboard com token + status trial
- Token reveal: aparece uma vez, segunda vez mostra "já revelado"
- Rotacionar token → novo token gerado e exibido uma vez
- Assinar Plus → Stripe Checkout em BRL → webhook → dashboard atualiza
- Gerenciar assinatura → Stripe Portal → cancelar → status "canceled"
- FAQ e Issues acessíveis sem auth
- Trocar locale PT-BR ↔ EN → interface traduzida

---

## BLOCO G — Documentação: docs.vectora.company

> **Stack:** Docusaurus 3 ou Mintlify. Subdomínio `docs.vectora.company`.
> Repo público: `vectora-company/docs`. Contribuições da comunidade via PR.

### G1 — Estrutura da documentação

```
docs.vectora.company/
├── getting-started/
│   ├── introduction          (o que é o Vectora, para quem é)
│   ├── installation          (pip install + requisitos)
│   ├── quick-start           (vectora setup + vectora chat em 5 min)
│   ├── vectora-token         (o que é, como obter, como configurar)
│   └── first-workspace       (criar workspace, indexar docs, primeira query)
├── guides/
│   ├── vps-deploy            (DigitalOcean, Hetzner, Contabo — passo a passo)
│   ├── team-setup            (Vectora Chat multi-usuário para equipes)
│   ├── rag-guide             (embedding, indexação, boas práticas)
│   ├── mcp-integration       (usar Vectora como sub-agente via MCP)
│   ├── git-workflows         (workspaces git, worktrees, PRs via agente)
│   └── api-keys              (configurar OpenAI, Anthropic, Gemini, Cohere)
├── reference/
│   ├── cli                   (todos os comandos com exemplos)
│   ├── config                (config.toml — todas as opções)
│   ├── tools                 (todas as 20+ tools do agente)
│   ├── agents                (Orchestrator, RAG, Search, Coder)
│   ├── api                   (REST API v1 — Bloco Z do chat-first)
│   └── mcp-server            (tools e resources expostos via MCP)
├── self-hosting/
│   ├── requirements          (hardware mínimo e recomendado)
│   ├── docker                (docker-compose.yml pronto para uso)
│   ├── nginx-traefik         (reverse proxy com TLS)
│   ├── storage-backends      (SQLite vs PostgreSQL, LanceDB vs Qdrant)
│   └── updates               (como atualizar o Vectora)
└── changelog/
    └── (por versão)
```

### G2 — Padrões de qualidade

- Toda página tem: introdução de 1 parágrafo, pré-requisitos, passos numerados,
  resultado esperado, seção de troubleshooting
- Exemplos de código com output esperado — não só o comando
- Screenshots ou GIFs para UI do chat
- Linguagem: PT-BR como idioma primário, EN como tradução
- Cada bloco do chat-first implementado → página de referência correspondente

### G3 — Changelog público

Página `/changelog` ou arquivo `CHANGELOG.md` no repo público com:

- Versão e data
- Novidades (features)
- Correções (bugfixes)
- Mudanças que quebram compatibilidade (breaking changes) em destaque

### G4 — Contribuição

- `CONTRIBUTING.md` no repo de docs
- Issues para erros e sugestões de docs
- PRs bem-vindos para correções e traduções

### Verificação (Bloco G)

- `docs.vectora.company` resolve corretamente
- Quick-start funciona do zero: usuário sem nenhuma experiência consegue
  instalar e usar em 10 minutos seguindo a doc
- Todos os comandos CLI documentados com exemplos testados
- Docker Compose da doc funciona em Ubuntu 24.04 limpo

---

## BLOCO H — Suporte & Comunidade

### H1 — Canais de suporte

**WhatsApp Business:**

- Link direto no site e na documentação
- Horário de atendimento explícito (ex: seg–sex 9h–18h BRT)
- Auto-resposta fora do horário com link para FAQ e issues

**Email `support@vectora.company`:**

- Para questões de billing e licença
- SLA: resposta em até 48h úteis
- Integração com ferramenta de ticketing (Crisp, Freshdesk ou Linear)

**GitHub Issues público:**

- Repositório `vectora-company/issues` (ou no repo principal se for público)
- Templates para: bug report, feature request, docs improvement
- Labels: `bug`, `enhancement`, `question`, `docs`, `billing`
- Triagem semanal por Bruno

### H2 — Comunidade

**Discord (futuro, pós-lançamento):**

- Servidor Vectora com canais: `#announcements`, `#general`, `#support`,
  `#show-and-tell`, `#feature-requests`, `#pt-br`, `#en`
- Bot de boas-vindas com link para docs e quick-start

**GitHub Discussions (alternativa sem Discord):**
Para o lançamento, GitHub Discussions é suficiente e requer menos manutenção.

### H3 — Programa de beta testers

Antes da campanha de influenciadores:

- Recrutar 10–20 beta testers via comunidades de dev (Discord LangChain BR,
  grupos Telegram Python BR, Slack MLOPS BR)
- Dar acesso Pro gratuito por 3 meses em troca de feedback estruturado
- Depoimentos e casos de uso reais para o site

### H4 — Status page

`status.vectora.company` (Upptime ou BetterStack):

- Uptime da API de validação de licença (Supabase)
- Uptime do site
- Histórico de incidentes

### Verificação (Bloco H)

- WhatsApp Business com perfil configurado e auto-resposta
- Email `support@` funcionando e com template de resposta
- GitHub Issues público com templates configurados
- 10+ beta testers recrutados com feedback coletado antes do lançamento

---

## BLOCO I — Distribuição & Kit de Lançamento

### I1 — PyPI

O Vectora já está no PyPI. Para o lançamento:

- Versão de lançamento oficial (ex: `1.0.0`) com changelog completo
- `README.md` do PyPI atualizado com: descrição, quickstart, link para docs,
  badges (versão, licença, Python)
- Classifiers corretos: `License :: Other/Proprietary License`,
  `Topic :: Scientific/Engineering :: Artificial Intelligence`

### I2 — Docker Hub / GitHub Container Registry

Imagem oficial `vectora/vectora:latest` e `vectora/vectora:1.0.0`:

```dockerfile
FROM python:3.13-slim
RUN pip install vectora
EXPOSE 8080
CMD ["vectora", "server", "chat"]
```

`docker-compose.yml` de referência disponível na documentação e no repo
de exemplos.

### I3 — Kit para influenciadores e canais

Um kit por destinatário, enviado com antecedência de 1–2 semanas:

**Conteúdo do kit:**

- Licença Pro gratuita por 6 meses (VECTORA_TOKEN incluído)
- Guia de instalação de 1 página (PDF) — do zero ao chat em 5 min
- 3–5 sugestões de demo prontas para vídeo/stream:
  1. _"Instalei o Vectora na minha VPS e indexei meu repositório"_
  2. _"Pedi pro Vectora revisar minha PR e ele fez o code review completo"_
  3. _"Minha equipe usa o Vectora como assistente interno — sem enviar dados pra ninguém"_
  4. _"Deixei o Vectora acessar meu código legado e ele me explicou tudo"_
- Pasta de assets: logo, screenshots do chat, diagrama de arquitetura,
  banner para thumbnail
- Contato direto do Bruno (WhatsApp) para suporte durante a produção do conteúdo

**Lista de canais brasileiros (fase 1):**

- TecMundo
- Loop Infinito
- Código Fonte TV
- Lucas Montano
- Mano Deyvin
- Grupo Flow (Flow News + Flow Games)
- Dicionário Tech
- (outros conforme afinidade com o produto)

**Lista de canais internacionais (fase 2, pós-lançamento BR):**

- Fireship
- AI Jason
- David Ondrej
- (comunidades Reddit: r/selfhosted, r/LocalLLaMA, r/Python)

### I4 — Posts de lançamento (redes próprias)

**LinkedIn (já redigidos nos posts anteriores):**

- Post 1: repo-cafe (contexto + por que RAG importa)
- Post 2: Vectora (história + arquitetura + lançamento)

**Reddit (no dia do lançamento):**

- r/selfhosted: "I built a self-hosted AI agent with RAG, MCP server and
  multi-user web chat — and it's now available"
- r/LocalLLaMA: foco no RAG híbrido e Deep Agents
- r/Python: foco na arquitetura técnica

**X / Twitter:**
Thread de lançamento com GIF do chat em uso.

**Hacker News:**
"Show HN: Vectora — self-hosted AI agent with hybrid RAG, MCP server and
multi-user web chat"

### I5 — Canal próprio do Vectora (YouTube)

Vídeos de lançamento produzidos por Bruno:

1. **Trailer oficial** (60–90s): produto em uso, sem narração técnica,
   música, visual limpo — serve como hero do site também
2. **Tutorial completo** (15–20 min): instalação + configuração + primeiro uso
3. **Demo de caso de uso** (5–10 min por caso): equipe usando o chat,
   code review via agente, RAG sobre documentação técnica

Editor de vídeo contratado para trailer e edição dos demos.

### Verificação (Bloco I)

- PyPI `1.0.0` publicado com README atualizado
- Imagem Docker publicada e testada do zero
- Kit enviado para todos os canais da lista BR com 2 semanas de antecedência
- Posts LinkedIn, Reddit e HN redigidos e agendados
- Trailer finalizado e aprovado

---

## BLOCO J — Marketing & Campanha de Influenciadores

### J1 — Cronograma de lançamento

```
T-30 dias: Bloco H3 — recrutar beta testers
T-21 dias: Bloco I3 — enviar kits para influenciadores BR
T-14 dias: Bloco I5 — trailer e tutorial finalizados
T-7  dias:  Site no ar (vectora.company) com todos os blocos F completos
T-3  dias:  Docs no ar (docs.vectora.company) com G1 completo
T-0  dia:   Lançamento oficial
            08h — posts LinkedIn + Reddit + HN publicados
            12h — trailer no YouTube
            (influenciadores publicam conforme agenda própria, semana do lançamento)
T+7  dias:  Análise de métricas, resposta a comentários, suporte ativo
T+14 dias:  Campanha fase 2 — canais internacionais + Reddit EN
```

### J2 — Métricas de sucesso do lançamento

**Meta conservadora (semana 1):**

- 500+ instalações (`pip install vectora` downloads no PyPI)
- 100+ contas criadas no Supabase
- 50+ usuários em trial ativo
- 10+ assinantes pagantes

**Meta otimista (semana 1):**

- 2.000+ instalações
- 500+ contas criadas
- 200+ trials ativos
- 50+ assinantes pagantes

**Indicadores de qualidade:**

- Taxa de conversão trial → pago (meta: ≥ 5%)
- Churn nos primeiros 30 dias (meta: ≤ 20%)
- NPS informal via WhatsApp/email nos primeiros beta testers

### J3 — Conteúdo de suporte pós-lançamento

Para manter tração orgânica após a semana de lançamento:

**Série "Casos de uso do Vectora" (LinkedIn/YouTube):**

- Um post/vídeo por semana nos primeiros 2 meses
- Temas: RAG sobre codebase legado, code review automatizado, equipe de
  3 devs usando como assistente compartilhado, Vectora + MCP no Claude Code

**Engajamento em comunidades:**

- Responder issues no GitHub em até 24h nos primeiros 30 dias
- Participar ativamente nos posts dos influenciadores (comentários técnicos)
- Post semanal no r/selfhosted sobre uso real

### J4 — Precificação para early adopters

Para incentivar conversão rápida no lançamento:

- **Early adopter Plus:** R$15/mês (desconto de 25%) para os primeiros
  100 assinantes — cupom `VECTORA25` no Stripe com `max_redemptions: 100`
- **Early adopter Pro:** R$45/mês (desconto de ~18%) para os primeiros
  50 assinantes — cupom `PROEARLY` com `max_redemptions: 50`
- Cupons com `duration: "forever"` — early adopters mantêm o preço
  enquanto a assinatura estiver ativa (incentivo para não cancelar)

### J5 — Roadmap público pós-lançamento

Publicar um roadmap simplificado no site (não os detalhes técnicos dos blocos,
mas as features planejadas em linguagem de usuário):

```
✓ Lançado
  → CLI + MCP (Plus)
  → Chat web multi-usuário (Pro)
  → RAG híbrido com reranking
  → HITL, workspaces, git integration

Em desenvolvimento
  → Deep Agents SDK (melhor performance dos agentes)
  → Terminal embarcado (PTY no chat)
  → REST API pública
  → ACP Protocol (integração com Zed, JetBrains, VS Code)

Planejado
  → Aplicativo desktop (Electron/Flet)
  → Aplicativo mobile
  → Marketplace de plugins MCP
```

### Verificação (Bloco J)

- Cronograma T-30 → T+14 executado conforme planejado
- Todos os influenciadores da lista BR publicaram conteúdo na semana do lançamento
- Meta conservadora de 10 assinantes pagantes atingida na semana 1
- Posts de suporte pós-lançamento agendados para as 8 semanas seguintes
- Roadmap público no site atualizado

---

## Princípios da Vectora Company

1. **Self-hosted é a proposta de valor central.** Toda comunicação,
   documentação e marketing reforça: seus dados ficam no seu servidor.
   Nunca armazenamos conversas, código ou arquivos.

2. **Produto primeiro, empresa depois.** Nenhuma frente de marketing começa
   sem o produto estar estável. Influenciadores recebem kit só quando o
   produto está no ar e testado.

3. **Suporte pessoal é diferencial.** WhatsApp direto com o fundador é
   uma vantagem real que empresas grandes não conseguem oferecer. Usar isso.

4. **Documentação é produto.** Um usuário que não consegue instalar o
   Vectora com a doc é uma venda perdida. A doc recebe o mesmo cuidado
   que o código.

5. **Preço honesto.** R$20/mês para Plus e R$55/mês para Pro é
   deliberadamente barato para o público-alvo (empresas). A estratégia
   é volume + fidelização, não margem alta em poucas contas.

6. **Open source como comunidade, fechado como produto.** Issues públicos,
   docs públicas, changelog público. O código é proprietário — e os
   usuários sabem exatamente o que o produto faz porque a documentação
   é transparente.

7. **Um fundador, muita alavancagem.** Influenciadores como força de
   marketing, beta testers como QA informal, comunidade como suporte
   de primeiro nível. Bruno foca em produto e no que só ele pode fazer.
