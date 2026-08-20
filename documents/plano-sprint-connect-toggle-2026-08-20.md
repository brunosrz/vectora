# Sprint — Vectora Connect: toggle explícito de ativar/desativar por plataforma

## Contexto e causa raiz (bug já corrigido ao vivo, feature vem agora)

Achado ao vivo em 2026-08-20: o backend subiu com o client Discord
conectado (`connect.discord: cliente iniciado`, `discord.client: logging in
using static token`) sem o usuário nunca ter configurado/ativado a
integração conscientemente. Causa raiz: `C:\Users\Machi\.vectora\.env` tinha
`DISCORD_BOT_TOKEN=tok` — um valor-placeholder de teste esquecido de uma
sessão anterior. Corrigido de imediato removendo a linha (sem código
envolvido nessa parte).

Mas a causa raiz _estrutural_ é real e seguia valendo para qualquer usuário:
`backend/services/connect/manager.py::configured_platforms()` trata
**presença de credencial = plataforma ligada**, sem nenhum flag de "salvei o
token mas não quero que rode ainda" nem "desliguei temporariamente sem
apagar a credencial". `sync_adapters()` roda no boot e reconcilia contra
esse conjunto — qualquer env var (`TELEGRAM_BOT_TOKEN`, `DISCORD_BOT_TOKEN`,
`SLACK_BOT_TOKEN`+`SLACK_APP_TOKEN`, `EMAIL_IMAP_*`) que exista no ambiente
liga o bot correspondente automaticamente, para sempre, até a credencial ser
apagada.

Achado colateral (mesma investigação): `frontend/components/settings/
environment/tabs/connect-tab.tsx` é **write-only** — não faz nenhum `GET` ao
montar, então o formulário sempre abre em branco mesmo com credenciais já
salvas, e não mostra se a plataforma está de fato rodando. Slack também está
ausente desse formulário apesar de suportado pelo `manager.py`/backend
inteiro (pré-existente, fora do escopo direto do bug mas descoberto aqui —
incluído nesta sprint por ser trivial dado o padrão já estabelecido pelas
outras plataformas).

## Parte A — Backend: flag `enabled` desacoplado da credencial

### Design

Reusar o mecanismo já existente pra preferências globais
(`RuntimeSettingsAdapter`, SQLite `app_settings` via `runtime_settings` —
mesmo backing store de `theme`/`language`/`local_env_overrides`). Não é
multi-tenant hoje (`connect.manager._running` já é estado global de
processo, não por usuário) — um flag global por plataforma é consistente
com o modelo atual, não uma regressão de escopo.

**A.1** — Novo par chave→valor em `runtime_settings`:
`connect_enabled_platforms: dict[str, bool]` (ex.:
`{"discord": false, "telegram": true}`; plataforma ausente do dict =
tratada como `false`, comportamento seguro por padrão).

**A.2** — `backend/services/connect/manager.py::configured_platforms()`
passa a exigir **credencial presente E flag habilitado**:

```python
def _enabled(platform: str) -> bool:
    from backend.workspace.runtime_settings import runtime_settings
    flags = runtime_settings.get("connect_enabled_platforms", {})
    return bool(isinstance(flags, dict) and flags.get(platform))
```

Cada `if _env("X_TOKEN"): platforms.add("x")` vira
`if _env("X_TOKEN") and _enabled("x"): platforms.add("x")`.

**A.3** — Novos endpoints em `backend/api/handlers/auth.py` (mesmo módulo
dos env overrides existentes) ou um handler novo `connect.py`:

- `GET /connect/status` → `{platform: {configured: bool, enabled: bool,
running: bool}}` para todas as plataformas suportadas — resolve também o
  gap de write-only do frontend (A.1 do Parte B depende disso).
- `POST /connect/{platform}/enabled` `{enabled: bool}` → persiste o flag
  (A.1) e chama `sync_adapters()` na sequência, reaproveitando o mesmo
  caminho de reconciliação já usado no boot e ao salvar credenciais
  (`connect.manager: mesmo caminho para ligar, desligar e reiniciar` — já é
  a garantia documentada no módulo, o endpoint novo só entra nesse caminho).
  `Depends(get_current_user)` — sem rota pública nova (CLAUDE.md §7).

### Migração de dados (não regredir integrações já em produção)

Sem o seed abaixo, todo usuário com uma integração **já funcionando** hoje
(token configurado e rodando de propósito, não por acidente) veria o bot
cair no primeiro boot pós-upgrade — regressão inaceitável disfarçada de
correção de segurança.

**A.4** — Migração one-shot (`backend/storage/migrations/`, seguindo o
padrão de `data_migration.py`): na primeira leitura de
`connect_enabled_platforms` que encontrar a chave ausente, popular
`enabled=true` para toda plataforma que **já tem credencial configurada
neste exato momento** (preserva o estado de quem já usa de verdade) e
`enabled=false` para o resto. A partir daí, salvar uma credencial nova
**não** liga a plataforma sozinha — precisa do toggle explícito.

## Parte B — Frontend: hidratar estado real + toggle por plataforma

**B.1** — `connect-tab.tsx` passa a buscar `GET /connect/status` no mount
(hoje não busca nada — `configs` sempre nasce vazio). Preenche os badges
"Configurado"/"Pendente" com o estado real, não com o que está no
formulário não-submetido.

**B.2** — Adicionar um `Switch` (`@radix-ui/react-switch`, já é dependência
do frontend) ao lado do badge de cada plataforma, refletindo `enabled` e
chamando `POST /connect/{platform}/enabled` no `onChange` — independente do
botão "Salvar Configurações" (que continua só gravando as credenciais).
Switch desabilitado (com tooltip) quando `configured: false` — não faz
sentido ligar uma plataforma sem credencial.

**B.3** — Adicionar o card do Slack ao formulário, mesmo padrão dos
outros (dois campos: `SLACK_BOT_TOKEN` + `SLACK_APP_TOKEN`, conforme
`manager.py` já exige os dois).

**B.4** — Strings novas (rótulo do switch, tooltip de desabilitado, texto
de "Slack") via `m()` nos 3 idiomas (`messages/{pt,en,es}.json`,
CLAUDE.md §2) — nada hardcoded.

## Testes (TDD, CLAUDE.md §18)

**Backend — `configured_platforms()`** (mesmo teste, par happy/erro):

- token presente + `enabled=true` → plataforma incluída (happy).
- token presente + `enabled=false` → **excluída** (este é o caso do bug de
  hoje — o teste que prova que ele não volta).
- `enabled=true` sem token → excluída (não dá pra ligar sem credencial).
- tier != pro → sempre excluída independente do flag (regra existente,
  precisa continuar valendo depois da mudança).

**Backend — endpoint `POST /connect/{platform}/enabled`**:

- toggle liga uma plataforma configurada → `sync_adapters()` dispara e o
  handle aparece em `running_platforms()` (happy, via servidor dummy/stub
  de cada plataforma, não a API real).
- toggle liga plataforma sem credencial → persiste a preferência, não
  inicia nada, sem erro 500 (edge).
- chamada sem autenticação → 401 (auth-first, §7).

**Backend — migração (A.4)**:

- token configurado + chave `connect_enabled_platforms` ausente → seed
  `enabled=true` só para essa plataforma (happy).
- nenhum token configurado + chave ausente → seed fica `{}`/tudo `false`
  (edge).
- chave já existir (migração já rodou antes) → não sobrescreve o valor que
  o usuário já setou manualmente (edge — idempotência da migração).

**Frontend — `connect-tab.test.tsx`**:

- render com `GET /connect/status` mockado retornando `configured:true,
enabled:false` → badge "Configurado", switch desligado (happy).
- clicar no switch → chama o endpoint de toggle com o platform certo e o
  novo valor, sem precisar clicar em "Salvar Configurações" (interação).
- switch desabilitado quando `configured:false`, com o tooltip esperado
  (edge).

## Verificação ao vivo

1. Restaurar `DISCORD_BOT_TOKEN` de teste em `~/.vectora/.env` (só para
   este teste, remover depois), reiniciar o backend: confirmar que **não**
   sobe o client Discord por padrão (migração seed `enabled=false` pra
   token novo, não pra token que já existia antes desta sprint — importante
   testar os dois casos).
2. Ligar o toggle do Discord pelas Settings: confirmar
   `connect.discord: cliente iniciado` aparece no log sem reiniciar o
   backend.
3. Desligar o toggle com o client rodando: confirmar que o processo
   Discord para (`_stop_platform`) sem derrubar o backend nem outras
   integrações.
4. Recarregar a aba Connect: confirmar que o estado (badge + switch)
   reflete o que está de fato rodando, não um formulário em branco.

## Ordem de execução

1. Parte A (backend: flag + migração + endpoints) primeiro — sem isso o
   frontend não tem o que consumir.
2. Parte B (frontend) depois, usando os endpoints da Parte A.
3. Slack no formulário (B.3) pode entrar em paralelo com B.1/B.2 — é
   independente do toggle em si.
