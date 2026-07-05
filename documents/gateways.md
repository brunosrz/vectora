# Vectora — Gateways de Modelo (Ollama + OpenRouter)

> Hoje o catálogo de modelos do Vectora é uma lista **estática** por provider
> (`backend/settings.py::AVAILABLE_MODELS`, espelhada em
> `frontend/lib/config/deployment-config.ts::MODELS`) — só os ids que o time
> escreveu no código aparecem no seletor de modelo. Isso funciona bem pra
> Google/OpenAI/Anthropic/Cohere (catálogos fechados, poucos ids), mas quebra
> pra dois casos que o usuário quer: **Ollama** (modelos locais — o usuário
> baixa o que quiser, não dá pra prever o id) e **OpenRouter** (gateway que
> agrega centenas de modelos de dezenas de provedores por trás de uma API key
> só). Este documento define como os dois entram como **gateways
> configuráveis pelo usuário**, não catálogos hardcoded — o usuário registra
> um modelo (id + apelido) e ele passa a aparecer no seletor de chat, igual
> aos modelos nativos.
>
> Ollama já tem suporte **parcial** no backend (`ollama_base_url`,
> `_PROVIDER_SPEC["ollama"]`) — é single-model, single-instance, sem UI. Este
> plano generaliza isso pra multi-modelo, multi-instância (conexões remotas)
> e adiciona OpenRouter do zero. Nenhuma das duas telas existe hoje no
> frontend — é greenfield de UI, mas o backbone de carregamento de LLM
> (`load_llm()`) já é provider-agnóstico o suficiente pra não precisar de
> reescrita.

---

## 1. Panorama

|                          | Ollama                                                                            | OpenRouter                                                                                                      |
| ------------------------ | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Onde roda**            | Processo do usuário (local ou outra máquina na rede)                              | Serviço cloud de terceiro (openrouter.ai)                                                                       |
| **Autenticação**         | Nenhuma (ou rede/túnel do usuário)                                                | API key própria do usuário                                                                                      |
| **Catálogo de modelo**   | O que o usuário baixou (`ollama list`) — infinitas variações de tag               | Centenas de modelos de dezenas de provedores, id `provider/model`                                               |
| **Integração LangChain** | `langchain[ollama]`, já usado via `init_chat_model(..., model_provider="ollama")` | Sem pacote dedicado — `init_chat_model("openrouter:<id>")` usa o caminho OpenAI-compatible por baixo (ver §3.2) |
| **Suporte hoje**         | Parcial (single-instance, sem UI, sem registro de modelo)                         | Zero                                                                                                            |

Os dois são "**gateways**" no mesmo sentido: uma conexão configurada pelo
usuário (endpoint + credencial) que expõe uma lista de modelos que o próprio
usuário escolhe registrar, e que entram no seletor de chat lado a lado com
os modelos nativos — sem precisar de release do Vectora pra cada modelo novo
que a Meta/Mistral/Alibaba lançar.

---

## 2. Ollama Gateway

### 2.1 Estado atual (parcial, é o ponto de partida)

`backend/settings.py:59-61`:

```python
# Ollama (local)
ollama_base_url: str | None = None
ollama_model: str = "llama2"
```

`backend/services/utils.py:104-114` (`_build_concrete_model`, caso `"ollama"`):

```python
case "ollama":
    from langchain.chat_models import init_chat_model

    return init_chat_model(
        model=model_name,
        model_provider="ollama",
        base_url=_get_env_with_default(
            "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
        ),
        temperature=temperature,
    )
```

Isso já cobre o caso mais difícil (instanciar o `BaseChatModel` certo) — o
que falta é tudo em volta: múltiplos modelos, múltiplas instâncias
(conexões remotas), e uma UI pra cadastrar isso sem editar `.env`.

### 2.2 Modelo de dados — instâncias + modelos registrados

Uma "instância Ollama" é uma conexão (host); um "modelo registrado" é um id
de modelo que o usuário confirma que existe naquela instância e quer ver no
seletor. Um usuário pode ter mais de uma instância (ex.: Ollama rodando no
PC de casa E num servidor com GPU).

```
OllamaInstance
  id            uuid
  label         "PC de casa" | "Servidor GPU"
  base_url      "http://192.168.1.50:11434"   ← suporta remoto (LAN/túnel/VPN)
  created_at

OllamaRegisteredModel
  id            uuid
  instance_id    → OllamaInstance
  model_tag      "llama3.1:70b" (como aparece em `ollama list`)
  display_name   "Llama 3.1 70B (casa)"       ← opcional, senão usa model_tag
```

**Conexões remotas**: `base_url` é só um HTTP endpoint — não tem nada
especial de "local" vs "remoto" no client (`langchain-ollama` já aceita
qualquer `base_url`). O que muda é a **responsabilidade do usuário**: expor
a porta 11434 do Ollama remoto de forma segura (túnel SSH, Tailscale,
Cloudflare Tunnel, VPN — o Vectora não gerencia isso, só documenta). A UI
deve deixar isso explícito: um campo de ajuda linkando pra
`docs.vectora.company` explicando as opções, não tentar automatizar
networking de terceiro.

### 2.3 Descoberta de modelos — não é digitação livre

Pedir pro usuário digitar `model_tag` de cabeça é ruim (typo → erro cru na
hora de chamar). Ollama expõe `GET /api/tags` (lista os modelos baixados na
instância) — o backend usa isso pra popular um dropdown de "modelos
disponíveis nessa instância" em vez de um campo de texto livre:

```python
# backend/services/gateways/ollama.py (novo)
async def list_ollama_models(base_url: str) -> list[str]:
    """GET {base_url}/api/tags — nomes dos modelos baixados na instância.

    Timeout curto (a instância pode estar offline/remota) — erro vira lista
    vazia com um aviso na UI, nunca exceção que quebra a tela de settings.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.get(f"{base_url.rstrip('/')}/api/tags")
        res.raise_for_status()
        return [m["name"] for m in res.json().get("models", [])]
```

Fluxo na UI: usuário cola o `base_url` → botão "Testar conexão" chama esse
endpoint → dropdown se popula → usuário marca quais modelos quer no
seletor (não precisa registrar todos os baixados, só os que usa no chat).

### 2.4 Backend — endpoints novos

Router novo `backend/api/handlers/gateways.py`, montado em `/gateways`:

- `POST /gateways/ollama/instances` — `{ label, base_url }` → testa conexão
  (`list_ollama_models`) antes de salvar; 400 se não conseguir conectar.
- `GET /gateways/ollama/instances` — lista instâncias do usuário.
- `DELETE /gateways/ollama/instances/{id}`
- `GET /gateways/ollama/instances/{id}/available-models` — chama
  `list_ollama_models` ao vivo (não cacheado — o usuário pode ter baixado
  modelo novo desde o cadastro).
- `POST /gateways/ollama/instances/{id}/models` — `{ model_tag,
display_name? }` registra um modelo daquela instância.
- `DELETE /gateways/ollama/models/{id}`

### 2.5 Persistência — SQLite, tabela nova (não `runtime_settings.json`)

Diferente do `active_provider`/`active_model` de hoje (que vivem em
`~/.vectora/settings.json` via `RuntimeSettings` — ver
`backend/services/runtime_settings.py:1-13`), instâncias/modelos de gateway
são **dados relacionais por usuário** (múltiplas linhas, FK), não uma
preferência escalar — cabem melhor como tabelas SQLite novas, na mesma base
de auth (`backend/storage/migrations/sqlite/`), seguindo o padrão de
`0001_auth.sql`:

```sql
-- 000N_gateways.sql
CREATE TABLE ollama_instances (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label      TEXT NOT NULL,
    base_url   TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE ollama_registered_models (
    id            TEXT PRIMARY KEY,
    instance_id   TEXT NOT NULL REFERENCES ollama_instances(id) ON DELETE CASCADE,
    model_tag     TEXT NOT NULL,
    display_name  TEXT,
    created_at    TEXT NOT NULL,
    UNIQUE (instance_id, model_tag)
);
```

Modo `lite` (SQLite sempre, ver `CLAUDE.md` — "Usuários/auth/settings
sempre em SQLite, independente do modo") já é o storage de auth hoje — essa
tabela mora no mesmo banco, sem depender do modo `complete`/Postgres.

### 2.6 Model id — como isso chega no `load_llm()`

Hoje o formato de model id é `"provider:model"` (`backend/services/
utils.py`, `load_llm(model_id)`). Um modelo Ollama registrado vira:

```
ollama:<instance_id>:<model_tag>
```

`load_llm()` já faz `model_id.split(":", 1)` — passa a ser `split(":", 2)`
quando o provider é `ollama`, resolvendo o `base_url` daquela instância
específica (lookup na tabela `ollama_instances`) antes de chamar
`_build_concrete_model("ollama", model_tag, ..., base_url=instance.base_url)`.
Isso é a única mudança estrutural no `load_llm()` — os outros providers
continuam com o formato de 2 partes.

---

## 3. OpenRouter Gateway

### 3.1 Por que — sem suporte hoje

`grep -ri openrouter backend/` não retorna nada — é greenfield total. Ao
contrário do Ollama, aqui não tem "instância" (é sempre `openrouter.ai`) —
só uma API key por usuário e uma lista de modelos registrados.

### 3.2 Integração — `init_chat_model("openrouter:<model>")`

Confirmado via MCP docs-langchain (`oss/python/concepts/
providers-and-models.mdx`, seção "Routers & proxies"): LangChain trata
OpenRouter como um provider de primeira classe dentro de `init_chat_model`,
sem pacote dedicado — usa o caminho OpenAI-compatible por baixo (mesma
família do `ChatOpenAI` com `base_url` customizado, documentado em
`oss/python/integrations/chat/index.mdx` — "Chat Completions API"):

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("openrouter:anthropic/claude-sonnet-4-6")
```

A API key vem de `OPENROUTER_API_KEY` no ambiente do processo por padrão —
como o Vectora precisa de uma key **por usuário** (não uma global do
servidor), a implementação passa a key explicitamente em vez de depender da
env var global:

```python
# backend/services/utils.py — novo case em _build_concrete_model
case "openrouter":
    from langchain.chat_models import init_chat_model

    return init_chat_model(
        model=model_name,          # ex.: "anthropic/claude-sonnet-4-6"
        model_provider="openrouter",
        api_key=api_key,           # resolvido por user, não de os.environ
        temperature=temperature,
    )
```

Adiciona `"openrouter"` em `_PROVIDER_SPEC` (`backend/services/utils.py:36`)
e na lista de providers válidos de `load_llm()`/`_build_concrete_model()`
(mensagens de erro em `services/utils.py` e `settings.py:890` citam a
lista fechada de providers — precisa incluir `openrouter` nelas também).

Dependência nova: `langchain[openai]` (openrouter usa o client OpenAI por
baixo) — **já é dependência transitiva do Vectora** hoje (Cohere/OpenAI já
usam pacotes da família `langchain-openai`/`openai`), então não deve
adicionar peso novo relevante ao bundle Nuitka.

### 3.3 Descoberta de modelos — API pública de catálogo

OpenRouter expõe `GET https://openrouter.ai/api/v1/models` **sem
autenticação** — lista completa e atualizada de todos os modelos
disponíveis (id, contexto, preço, provider original). Diferente do Ollama
(onde só dá pra saber o que existe perguntando pra instância do próprio
usuário), aqui dá pra buscar o catálogo inteiro e deixar o usuário
**filtrar/buscar** em vez de digitar id de cabeça:

```python
# backend/services/gateways/openrouter.py (novo)
async def list_openrouter_models() -> list[OpenRouterModel]:
    """GET /api/v1/models — catálogo público, sem auth. Cacheado 1h
    (backend/services/cache_llm.py já tem o padrão de cache pronto) —
    não bate na rede a cada tecla digitada no filtro da UI."""
    ...
```

### 3.4 Backend — endpoints novos

Mesmo router `backend/api/handlers/gateways.py`, prefixo `/gateways/openrouter`:

- `PUT /gateways/openrouter/api-key` — `{ api_key }`. Valida chamando
  `GET /api/v1/auth/key` da OpenRouter (retorna limites/créditos da key —
  serve de verificação "a key é válida?" antes de salvar).
- `DELETE /gateways/openrouter/api-key`
- `GET /gateways/openrouter/catalog?q=` — proxy pro catálogo público
  (cacheado), com filtro de busca por nome/id.
- `POST /gateways/openrouter/models` — `{ model_id, display_name? }`
  registra um modelo do catálogo pro seletor.
- `GET /gateways/openrouter/models` / `DELETE /gateways/openrouter/models/{id}`

### 3.5 Persistência — API key vai em `env_overrides`, modelos em tabela nova

A OpenRouter API key é uma **credencial**, não uma preferência — o Vectora
já tem exatamente esse conceito resolvido: `users.env_overrides_json`
(`backend/storage/migrations/sqlite/0001_auth.sql:10`, funções
`get_env_overrides`/`set_env_override`/`delete_env_override` em
`backend/services/auth.py:579-618`), hoje usado pra `GITHUB_TOKEN` (OAuth,
`backend/api/handlers/oauth.py`). A key entra como
`env_overrides["OPENROUTER_API_KEY"]` — reaproveita o mecanismo de
criptografia/storage que já existe, zero tabela nova pra isso.

Modelos registrados (que não são segredo) vão numa tabela igual à do
Ollama:

```sql
CREATE TABLE openrouter_registered_models (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model_id      TEXT NOT NULL,       -- ex.: "anthropic/claude-sonnet-4-6"
    display_name  TEXT,
    created_at    TEXT NOT NULL,
    UNIQUE (user_id, model_id)
);
```

Model id no formato `"provider:model"` existente: `openrouter:<model_id>`
(sem instância no meio, diferente do Ollama, já que só existe uma
OpenRouter).

---

## 4. Modo local (sem conta) vs modo servidor (multi-usuário)

O Vectora roda sem auth no modo local/CLI puro (single-user, sem tabela
`users` populada por login) — mas mesmo aí o backend usa SQLite pra
storage (`CLAUDE.md`: "Usuários/auth/settings sempre em SQLite,
independente do modo"), então as tabelas de gateway acima funcionam igual
nos dois modos: no local, existe um único "usuário" implícito (linha
seed'ada ou `user_id` fixo tipo `"local"`); no modo servidor/Pro
multi-usuário, cada conta tem suas próprias instâncias Ollama e sua própria
key OpenRouter, isoladas por `user_id` como qualquer outro dado da conta.
Não precisa de bifurcação de código entre os dois modos — só o auth-first
já existente (`Depends(get_current_user)`) resolve o isolamento.

---

## 5. Frontend

### 5.1 Nova aba "Gateways" no `EnvironmentDialog`

`frontend/components/settings/environment/index.tsx` já tem abas "Envs",
"Skills", "Plugins", "Integrações" — adiciona uma quinta: "Gateways". Não
reaproveita a UI de `integracoes-tab.tsx` 1:1 (aquele padrão é 1
card = 1 API key por serviço fixo) porque gateway tem uma dimensão a mais
(lista de modelos por conexão) — mas segue o mesmo padrão visual
(card expansível, badge de status conectado/desconectado, fetch/save
contra o backend).

```
frontend/components/settings/environment/tabs/gateways-tab.tsx   (novo)
  ├─ OllamaSection
  │    ├─ lista de instâncias (label, base_url, badge online/offline)
  │    ├─ form "+ Nova instância" (label, base_url, botão testar conexão)
  │    └─ por instância: dropdown de modelos disponíveis (GET available-models)
  │       + botão "Registrar" por modelo selecionado
  └─ OpenRouterSection
       ├─ campo API key (mascarado, com "Verificar" — mesma UX de integracoes-tab)
       └─ busca no catálogo (debounced) + botão "Registrar" por resultado
```

### 5.2 Catálogo de modelo — estático + dinâmico

`frontend/lib/config/deployment-config.ts` continua sendo o catálogo
**estático** (Google/OpenAI/Anthropic/Cohere) — não vira lugar de modelo
dinâmico. O seletor de modelo (`frontend/components/chat/
model-selector.tsx`) passa a mesclar duas fontes:

```typescript
// novo: frontend/lib/hooks/use-gateway-models.ts
function useGatewayModels() {
  return useQuery({
    queryKey: ["gateway-models"],
    queryFn: () => fetchJson("/gateways/models"), // endpoint agregado novo
    staleTime: 30_000,
  });
}
```

Endpoint agregado novo `GET /gateways/models` no backend retorna todos os
modelos registrados (Ollama + OpenRouter) do usuário num formato já
compatível com `ModelOption` do frontend
(`"ollama:<instance>:<tag>"` / `"openrouter:<model_id>"`), pra não
precisar de dois `useQuery` separados no seletor. `model-selector.tsx`
concatena `getAllowedModels()` (estático) com esse resultado (dinâmico) — o
resto do componente (ícone de provider, `onChange`) já funciona igual
porque o formato de id é o mesmo `provider:model`.

`deployment-config.ts::ModelConfig.provider` ganha `"ollama"` e
`"openrouter"` no union type; `isProviderVisionCapable()` retorna `false`
pros dois por padrão (Ollama depende do modelo local — não dá pra saber
sem introspecção; OpenRouter varia por modelo agregado — mais seguro
recusar imagem por padrão do que assumir suporte e estourar erro cru na
API de terceiro, mesmo princípio do Sprint V1 do bugfix — ver
`rustling-hatching-summit.md`).

---

## 6. Segurança

- OpenRouter API key: nunca loga em texto plano; segue o mesmo tratamento
  de `GITHUB_TOKEN`/outros tokens em `env_overrides` (já criptografado at
  rest conforme o storage de auth existente — não reinventar).
- Ollama `base_url`: é um endereço de rede fornecido pelo usuário, não um
  segredo — mas o backend deve validar que não é `localhost`/`127.0.0.1`
  apontando pra uma porta sensível do próprio host **antes de repassar
  requests livremente** (SSRF básico) — timeout curto (2.4) e
  `httpx.AsyncClient` sem seguir redirect automaticamente já mitigam boa
  parte disso.
- Rota de teste de conexão (`available-models`) é síncrona e pode ser
  abusada pra port-scan interno — rate-limit por usuário (mesmo padrão já
  usado em `LICENSE_VALIDATE_LIMITER` do `services/wrangler.toml`, mas
  aqui no backend Python — `slowapi` ou equivalente já usado em outra rota
  sensível, se existir).

---

## 7. Testes (TDD, seguindo `CLAUDE.md` §18)

- Backend: `list_ollama_models`/`list_openrouter_models` com mock de
  `httpx` — caminho feliz (lista modelos) e erro (instância offline →
  lista vazia + log, nunca exceção pro caller); endpoints `/gateways/*`
  com auth (401 sem sessão, isolamento por `user_id` — usuário A não vê
  instância do usuário B); `load_llm()` com model id de gateway resolve
  pro `base_url`/`api_key` corretos (parametrizado por provider).
- Frontend: `gateways-tab.tsx` — formulário de nova instância valida
  campos, mostra erro de conexão falha; `model-selector.tsx` mescla
  catálogo estático + dinâmico sem duplicar entradas quando os dois
  batem por acaso.

---

## 8. Faseamento sugerido

1. Migration SQLite (tabelas `ollama_instances`, `ollama_registered_models`,
   `openrouter_registered_models`) + `env_overrides["OPENROUTER_API_KEY"]`.
2. Backend: `_PROVIDER_SPEC`/`_build_concrete_model` ganham `openrouter`;
   `load_llm()` resolve model id de 3 partes pro Ollama por instância.
3. Backend: router `/gateways/*` completo (Ollama + OpenRouter + endpoint
   agregado `/gateways/models`).
4. Frontend: aba "Gateways" no `EnvironmentDialog` (Ollama primeiro —
   reaproveita mais do backend parcial existente).
5. Frontend: `model-selector.tsx` mesclando estático + dinâmico.
6. Frontend: seção OpenRouter na mesma aba.
7. Verificação: `scons lint && scons tests`, fluxo manual (cadastrar
   instância Ollama remota de verdade, mandar mensagem; cadastrar
   OpenRouter com key de teste, mandar mensagem com um modelo agregado).
