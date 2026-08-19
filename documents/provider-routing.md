# Vectora — Provider Routing de Modelo (Ollama + OpenRouter + 9Router)

> Além do catálogo **estático** por provider (`backend/settings.py::AVAILABLE_MODELS`,
> espelhado em `frontend/lib/config/deployment-config.ts::MODELS`) — os ids
> que o time escreve no código pra Google/OpenAI/Anthropic/Cohere (catálogos
> fechados, poucos ids) — o Vectora tem três **gateways configuráveis pelo
> usuário**: **Ollama** (modelos locais — o usuário baixa o que quiser),
> **OpenRouter** (agrega centenas de modelos de dezenas de provedores por
> trás de uma API key só) e **9Router** (proxy local OpenAI-compatible do
> próprio usuário, [github.com/decolua/9router](https://github.com/decolua/9router)).
> Nos três casos o usuário registra um modelo (descoberto via API do
> gateway, nunca digitado de cabeça) e ele passa a aparecer no seletor de
> chat lado a lado com os modelos nativos.

---

## 1. Panorama

|                        | Ollama                                                           | OpenRouter                                                                                      | 9Router                                                                                             |
| ---------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Onde roda**          | Processo do usuário (local, `http://127.0.0.1:11434` por padrão) | Serviço cloud de terceiro (`openrouter.ai`)                                                     | Proxy local do próprio usuário (self-hosted)                                                        |
| **Autenticação**       | Nenhuma                                                          | API key própria do usuário, validada contra `/api/v1/auth/key` antes de salvar                  | Endpoint + key próprios do usuário, salvos juntos (sem endpoint de auth dedicado pra validar antes) |
| **Catálogo de modelo** | O que o usuário baixou (`GET {base_url}/api/tags`)               | Catálogo público (`GET https://openrouter.ai/api/v1/models`, sem auth, cacheado ~1h no backend) | `GET {base_url}/models` (endpoint OpenAI-compatible padrão)                                         |
| **Client nativo**      | `OllamaChatClient` (`backend/llm/ollama/chat_client.py`)         | `OpenRouterChatClient` (`backend/llm/openrouter/chat_client.py`)                                | Reaproveita `OpenRouterChatClient`/`OpenRouterClient` com `base_url` trocada                        |
| **Model id**           | `ollama:<tag>`                                                   | `openrouter:<id>` (ex.: `openrouter:anthropic/claude-sonnet-4.5`)                               | `nine_router:<id>`                                                                                  |

Os três protocolos de fato entram no chat pelo mesmo ponto de entrada,
`load_chat_client(model_id)` em `backend/llm/fallback_chat_client.py` — um
`match provider` sobre a primeira parte do model id (`"provider:model"`,
`model_id.partition(":")`) que instancia o `ChatClient` (Protocol de
`backend/llm/base.py`) correto. Ollama e OpenRouter/9Router não têm
"instância" por usuário — é sempre uma única configuração global do
processo backend (`ollama_base_url`/`OPENROUTER_API_KEY`/`nine_router_*`
em `backend/settings.py`), consistente com o Vectora rodar um backend por
instalação, não multi-tenant nesse nível.

---

## 2. Backend — `backend/api/handlers/provider_routing.py`

Router `/provider-routing`, montado em `backend/api/server.py`. Cobre
descoberta (nunca digitação livre de model id — erro de digitação vira
falha silenciosa no chat) + registro (o subconjunto de modelos descobertos
que o usuário realmente quer no seletor):

| Endpoint                                              | Método       | Propósito                                                                                                                                              |
| ----------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `/provider-routing/ollama/models`                     | `GET`        | Descoberta via `{ollama_base_url}/api/tags`. Host fora do ar → `{reachable: false}`, nunca 500                                                         |
| `/provider-routing/ollama/registered`                 | `GET`        | Lista modelos Ollama registrados                                                                                                                       |
| `/provider-routing/ollama/registered`                 | `POST`       | Registra uma tag (`{tag}`)                                                                                                                             |
| `/provider-routing/ollama/registered/{model_id}`      | `DELETE`     | Remove                                                                                                                                                 |
| `/provider-routing/openrouter/status`                 | `GET`        | Key configurada? (`{configured, masked}`)                                                                                                              |
| `/provider-routing/openrouter/key`                    | `POST`       | Valida contra `GET /api/v1/auth/key` da OpenRouter e persiste (`{api_key}`)                                                                            |
| `/provider-routing/openrouter/key`                    | `DELETE`     | Remove a key                                                                                                                                           |
| `/provider-routing/openrouter/models?q=`              | `GET`        | Catálogo público (cache em memória ~1h); sem cache e sem rede, cai num catálogo embutido (`OPENROUTER_FALLBACK_MODELS`) pra não deixar o seletor vazio |
| `/provider-routing/openrouter/registered`             | `GET`/`POST` | Lista/registra (`{tag}`)                                                                                                                               |
| `/provider-routing/openrouter/registered/{model_id}`  | `DELETE`     | Remove                                                                                                                                                 |
| `/provider-routing/nine-router/status`                | `GET`        | Endpoint+key configurados? (`{configured, base_url, masked}`)                                                                                          |
| `/provider-routing/nine-router/config`                | `POST`       | Salva `base_url`+`api_key` juntos (interdependentes, sem validação prévia)                                                                             |
| `/provider-routing/nine-router/config`                | `DELETE`     | Remove os dois                                                                                                                                         |
| `/provider-routing/nine-router/models`                | `GET`        | Descoberta via `{base_url}/models`. Não configurado/fora do ar → `{reachable: false}`                                                                  |
| `/provider-routing/nine-router/registered`            | `GET`/`POST` | Lista/registra (`{tag}`)                                                                                                                               |
| `/provider-routing/nine-router/registered/{model_id}` | `DELETE`     | Remove                                                                                                                                                 |

### 2.1 Persistência — SQLite, tabelas globais (sem `user_id`)

Modelos registrados vivem em três tabelas SQLite (`ollama_registered_models`,
`openrouter_registered_models`, `nine_router_registered_models`), criadas
sob demanda (`CREATE TABLE IF NOT EXISTS`) no mesmo arquivo
`~/.vectora/checkpoints.db` que o handler de threads já usa (`_get_db()`
reaproveita `backend/api/handlers/threads.py::_get_db`) — não abre conexão
própria. Schema:

```sql
CREATE TABLE {ollama|openrouter|nine_router}_registered_models (
    id         TEXT PRIMARY KEY,
    tag        TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
)
```

Sem `user_id`: o Vectora roda um backend por instalação (mesmo em modo
servidor, ver `CLAUDE.md` — SQLite de auth/settings é sempre por
instalação), então os modelos registrados são um catálogo por instância de
backend, não por conta multi-tenant. `tag` é `UNIQUE` — registrar de novo
devolve 409.

### 2.2 OpenRouter — key vai pro `.env`, não pra tabela

A API key da OpenRouter (`POST /provider-routing/openrouter/key`) é
validada contra `GET https://openrouter.ai/api/v1/models` +
`/auth/key` (Bearer da key recebida) antes de persistir — nunca salva uma
key que a própria OpenRouter rejeita. Persistência via
`backend/cli/keys.py::upsert_env_key` no `~/.vectora/.env` (chave
`OPENROUTER_API_KEY`), espelhada em `os.environ` e em
`settings.openrouter_api_key` na mesma request — sem restart do backend
pra valer. `DELETE` reverte os três (arquivo, env do processo, settings).
9Router segue o mesmo padrão (`NINE_ROUTER_BASE_URL`/`NINE_ROUTER_API_KEY`),
mas sem validação prévia — o proxy não expõe endpoint dedicado de
"auth/key" como a OpenRouter.

### 2.3 `load_chat_client()` — resolução em tempo de chat

`backend/llm/fallback_chat_client.py::load_chat_client(model_id)`:

```python
case "ollama":
    return OllamaChatClient(
        model=model_name,
        client=OllamaClient(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            api_key=os.getenv("OLLAMA_API_KEY", ""),
        ),
    )
case "openrouter":
    api_key = get_env("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY não configurado...")
    return OpenRouterChatClient(model=model_name, client=OpenRouterClient(api_key=api_key))
case "nine_router":
    # Reusa o client do OpenRouter com base_url trocada — mesmo protocolo
    # OpenAI-compatível.
    base_url = settings.nine_router_base_url
    api_key = settings.nine_router_api_key
    if not base_url or not api_key:
        raise ValueError("9Router não configurado...")
    return OpenRouterChatClient(model=model_name, client=OpenRouterClient(api_key=api_key, base_url=base_url))
```

`OpenRouterClient` (`backend/llm/openrouter/client.py`) é o mesmo client
HTTP reaproveitado pelo `openrouter` e pelo `nine_router` — os dois falam o
protocolo OpenAI-compatible Chat Completions; a única diferença é
`base_url`/`api_key`. Adicionar um gateway novo de terceiro que fale o
mesmo protocolo é o mesmo padrão: um `case` a mais em `load_chat_client()`,
sem dependência nova.

O `FallbackChatClient` (mesmo arquivo, ver `documents/…` sobre fallback de
provider) trata os três gateways como qualquer outro provider na cadeia —
`get_fallback_chain()`/`_provider_has_key()`
(`backend/llm/provider_fallback.py`) já reconhecem `ollama` (sempre "tem
key", é local) e `openrouter` (via `settings.openrouter_api_key`).

### 2.4 Endpoint agregado pro seletor — `GET /models/providers`

`backend/api/handlers/models.py`, consumido pelo `model-selector.tsx` do
frontend:

```python
@router.get("/providers")
async def get_configured_providers() -> dict:
    dynamic_models = (
        [{"id": f"ollama:{m.tag}", "label": m.tag} for m in await list_registered_ollama_models()]
        + [{"id": f"openrouter:{m.tag}", "label": m.tag} for m in await list_registered_openrouter_models()]
        + [{"id": f"nine_router:{m.tag}", "label": m.tag} for m in await list_registered_nine_router_models()]
    )
    return {
        "providers": settings.configured_llm_providers(),
        "dynamic_models": dynamic_models,
        "tool_incompatible_models": sorted(TOOL_CALLING_INCOMPATIBLE_MODELS),
    }
```

`settings.configured_llm_providers()` devolve os providers **estáticos**
com credencial presente (Google/OpenAI/Anthropic/Cohere/OpenRouter — e
`ollama` quando `ollama_base_url` está setado); `dynamic_models` é a lista
plana dos três gateways, já no formato de model id que
`load_chat_client()` espera. O frontend não precisa de três `useQuery`
separados — uma chamada só devolve tudo.

---

## 3. Descoberta de capacidade — visão por modelo, não por provider

`VISION_CAPABLE_PROVIDERS` (`backend/settings.py`) é `{"google-genai",
"openai", "anthropic"}` — Ollama e OpenRouter/9Router ficam de fora desse
conjunto estático **porque a capacidade real varia por modelo**, não por
provider:

- **Ollama**: sem introspecção — `isProviderVisionCapable()` no frontend
  trata Ollama como sem visão por padrão (não dá pra consultar o daemon
  sobre capability de cada modelo baixado sem uma chamada dedicada por
  modelo).
- **OpenRouter**: a checagem real consulta `architecture.input_modalities`
  do catálogo público por `model_id` —
  `openrouter_model_supports_image()` no backend
  (`provider_routing.py`) e `checkOpenRouterModelSupportsImage()` no
  frontend (`frontend/lib/api/openrouter-vision.ts`), os dois com o mesmo
  cache TTL ~1h e a mesma política de **fail-open**: modelo ausente do
  catálogo ou catálogo indisponível → assume que suporta imagem (deixa a
  chamada real ao provider decidir, em vez de bloquear um modelo que
  processa imagem de verdade).

---

## 4. Frontend

### 4.1 Aba "Provider Routing" — `EnvironmentDialog`

`frontend/components/settings/environment/tabs/provider-routing-tab.tsx`
(`ProviderRoutingTab`) — uma das abas do `EnvironmentDialog`
(`frontend/components/settings/environment/index.tsx`), ao lado de Envs/
Skills/Plugins/Integrações. Três seções, cada uma repetindo o mesmo padrão
descoberta → registrar → lista de registrados com botão remover:

```
ProviderRoutingTab
  ├─ OllamaSection        — botão "Detectar modelos" (GET .../ollama/models),
  │                          lista descobertos + botão registrar por item
  ├─ OpenRouterSection    — campo de key (mascarado, POST/DELETE .../openrouter/key),
  │                          busca no catálogo com debounce 300ms
  │                          (GET .../openrouter/models?q=)
  ├─ NineRouterSection    — campos base_url + key, descoberta automática
  │                          assim que configurado (mesmo princípio do
  │                          OpenRouter), filtro local nos resultados
  │                          quando há mais de 5 modelos
  └─ MediaModelsSection   — modelos de imagem/TTS por gateway (Ollama/
                             OpenRouter), via GET/PATCH /admin/media-models;
                             Gemini/OpenAI resolvem sozinhos por
                             PROVIDER_CAPABILITIES, não aparecem aqui
```

Todas as seções usam o mesmo componente `RegisteredModelsList` pra
renderizar a lista de registrados (mono-space, botão de remover com
loading state) — só a lógica de descoberta/registro muda entre gateways.

### 4.2 Catálogo de modelo — estático + dinâmico

`frontend/lib/config/deployment-config.ts` continua sendo o catálogo
**estático** (Google/OpenAI/Anthropic/Cohere) — o seletor de modelo
(`frontend/components/chat/model-selector.tsx`) mescla esse catálogo com
`dynamic_models` de `GET /models/providers`. `ModelConfig.provider` inclui
`"ollama"`, `"openrouter"` e `"nine_router"` no union type; o resto do
componente (ícone de provider, `onChange`) funciona igual porque o formato
de id é sempre `provider:model`.

---

## 5. Segurança

- **OpenRouter/9Router API key**: nunca loga em texto plano; persistida no
  `.env` local da instalação (`~/.vectora/.env`), mesmo mecanismo de
  qualquer outra credencial de provider — não um segredo remoto num
  serviço multi-tenant.
- **Ollama/9Router `base_url`**: endereço de rede fornecido pelo usuário —
  as rotas de descoberta (`/api/tags`, `/models`) usam timeout curto
  (`_DISCOVERY_TIMEOUT_S = 2.5`) e nunca deixam a exceção subir como 500;
  o host estar offline é um resultado esperado (`reachable: false`), não
  um erro de servidor.
- **Catálogo OpenRouter com fallback embutido**: se a rede cair e o cache
  em memória ainda estiver vazio, `OPENROUTER_FALLBACK_MODELS` (lista fixa
  de ids populares) evita que o seletor apareça sem nenhuma opção — o
  usuário leria isso como "Vectora não suporta OpenRouter" em vez de
  "estou sem internet". Essa lista nunca é gravada no cache — a próxima
  tentativa busca o catálogo real de novo.

---

## 6. Testes

`vectora/tests/` cobre o handler `provider_routing.py` (descoberta com
`httpx.AsyncClient` injetado via `Depends` — caminho feliz e host
offline/`reachable: false`; registro/remoção com tag duplicada → 409;
validação de key OpenRouter rejeitada pelo provider → 400) e o frontend
(`provider-routing-tab.test.tsx`) cobre os três fluxos de UI (descobrir,
registrar, remover, erro de conexão). `openrouter-vision.test.ts` cobre a
checagem de capability com cache e fallback aberto.
