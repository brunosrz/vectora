# Vectora — Plano IA+: TTS, STT e Geração de Imagens

> Pseudo-plano de feature set para expandir o conjunto de IAs do Vectora
> de **3 modalidades** (LLM chat/code, embedding, reranker) para **6**
> (+ TTS, + STT, + image generation). Inclui também atualizações no
> registry de modelos LLM (Aya Expanse, Aya Tiny, Gemini 3.5).
>
> **Nota**: este é um documento de planejamento independente. Quando uma
> feature for aprovada para implementação, migrar para o `docs/plan.md`
> principal como sub-bloco (Bloco H ou I do roadmap).

---

## 0. Conflito com o posicionamento atual (resolver antes)

`docs/pitch_deck.md` afirma textualmente:

> _"Não há áudio/voz no Vectora — nem TTS nem STT estão no roadmap atual.
> Para essas necessidades, o Perssua é a referência brasileira correta."_

`docs/ux.md` (UX-32, UX-33) já reabriu a discussão de áudio com a
existência do hook `useVoiceInput` (Web Speech API) e propõe TTS opcional.

Este plano **substitui** a posição anti-áudio do pitch deck. Justificativa:

1. **Custo de implementação caiu** — Cohere lançou `Transcribe`; Gemini
   3.x faz speech-generation nativo; OpenAI image gen é tool oficial
   `langchain-openai`. Não precisamos manter Whisper/TTS locais.
2. **Continuamos não competindo com Perssua** — Perssua é assistente de
   reuniões (diferenciar falantes, transcrição em tempo real, modo stealth).
   Vectora adiciona TTS/STT como **modalidade de input/output do agente
   de produtividade**, não como produto de reuniões.
3. **Image generation é capability** — não é "feature de IA arte". É
   diagramas, mockups, screenshots-de-referência, geração de favicon em
   3 segundos, redesenho rápido de fluxos. Devs usam.

Ação obrigatória ao aprovar este plano:

- `docs/pitch_deck.md`: remover a frase "Não há áudio/voz no Vectora";
  adicionar seção "Modalidades de IA" alinhada com este documento.
- `docs/products.md` Tier 1: adicionar TTS/STT/image gen às
  capacidades default do Vectora (sem mudança de preço).
- `docs/plan.md` Bloco H ou novo Bloco H+ se H já estiver fechado.

---

## 1. Estado atual — 3 modalidades

| Modalidade    | Provider único                              | Onde se usa                           |
| ------------- | ------------------------------------------- | ------------------------------------- |
| **LLM**       | Google / OpenAI / Anthropic                 | Orchestrator, Coder, Search subagents |
| **LLM RAG**   | Cohere Command R+ opcional                  | RAG synthesis quando default falha    |
| **Embedding** | Cohere `embed-multilingual-v3.0` (1024-dim) | Indexação RAG, busca semântica        |
| **Reranker**  | Cohere `rerank-multilingual-v3.0`           | Pipeline RAG (estágio 3)              |

Tooling implementado:

- `src/services/utils.load_llm()` — factory de LLM via
  `langchain-{google-genai, openai, anthropic, cohere}`.
- `src/tools/rag.py` + `nodes/rag_subgraph.py` — pipeline de retrieval.
- Cohere é o **backbone obrigatório** do RAG (parceria estratégica
  documentada em `docs/apoiadores.md`).

Frontend já tem:

- `chat/lib/hooks/files/use-voice-input.ts` — STT via Web Speech API
  (Chrome/Edge desktop + Android). Não cobre Safari/Firefox nem ambientes
  onde a API roteia para Google Cloud.

---

## 2. Visão expandida — 6 modalidades

```
┌──────────────────────────────────────────────────────────────────┐
│                          VECTORA AGENT                            │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │ Input do user   │  │ Processamento   │  │ Output do agente│   │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤   │
│  │ • Texto         │  │ • LLM           │  │ • Texto         │   │
│  │ • Arquivos      │  │ • Embedding     │  │ • Imagens (NOVO)│   │
│  │ • Imagens       │  │ • Reranker      │  │ • Áudio  (NOVO) │   │
│  │ • Áudio  (NOVO) │  │ • Image gen NEW │  │   (TTS streaming│   │
│  │   (STT inline   │  │ • STT     NEW   │  │    do response) │   │
│  │    ou anexo)    │  │ • TTS     NEW   │  │                 │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.1 Provider strategy por modalidade

| Modalidade    | Provider primário               | Fallback                       | Razão                                                                                                         |
| ------------- | ------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| LLM chat      | Gemini 3.5 Flash                | OpenAI GPT-5.x, Anthropic 4.x  | Custo baixo, multimodal nativo (vê imagem/áudio direto)                                                       |
| LLM mult.     | Cohere Aya Expanse 32B          | Aya Expanse 8B, Aya Tiny       | Multilingual líder, **incluindo pt-BR forte**; alternativa ao OpenAI/Anthropic em workloads sensíveis a custo |
| Embedding     | Cohere `embed-multilingual-v3`  | Gemini `text-embedding-004`    | Cohere é parceiro estratégico; Gemini só como fallback de redundância                                         |
| Reranker      | Cohere `rerank-multilingual-v3` | —                              | Sem fallback hoje; Cohere domina o estado da arte                                                             |
| **TTS**       | **Gemini speech-generation**    | OpenAI TTS-1-HD                | Gemini suporta vozes multi-idioma + SSML; OpenAI é fallback estável                                           |
| **STT**       | **Cohere Transcribe**           | OpenAI Whisper-1, Gemini audio | Cohere lançou em 2025 — alinha com nossa parceria; Whisper é commodity                                        |
| **Image gen** | **Gemini 3.5 nano-banana-pro**  | OpenAI `gpt-image-1`           | Nano-banana-pro é state-of-the-art em qualidade/custo; OpenAI é fallback                                      |

Cohere fica como **âncora de RAG e multilingual** (embedding + reranker

- Aya + Transcribe). Gemini é o **canivete suíço multimodal** (chat +
  image + TTS + audio input). OpenAI/Anthropic são **opcionais premium**.

### 2.2 Diretriz cardinal: nenhuma modalidade vira lock-in

Tudo passa por Protocol abstrato em `src/services/media/` — trocar
provider de TTS de Gemini para OpenAI é mudança de config, não de
código. Mesma regra das outras modalidades (princípio 5 do plan mestre).

---

## 3. Atualizações no registry de modelos LLM (chat-first)

Adicionar ao `src/settings.py::AVAILABLE_MODELS` + espelhar em
`chat/lib/config/deployment-config.ts`:

### 3.1 Cohere Aya — multilingual de produção

| Model ID          | Família  | Tamanho | Contexto | Strengths                         |
| ----------------- | -------- | ------- | -------- | --------------------------------- |
| `aya-expanse-32b` | Aya      | 32B     | 128k     | Multilingual top, pt-BR forte     |
| `aya-expanse-8b`  | Aya      | 8B      | 128k     | Multilingual médio, mais barato   |
| `c4ai-aya-tiny`   | Aya Tiny | <8B     | 32k      | Edge/offline-friendly, multi-lang |

Use cases:

- **Aya Expanse 32B** como alternativa default para users que priorizam
  resposta em pt-BR de qualidade nativa (não-traduzida do inglês).
- **Aya Tiny** para o futuro modo `vectora server mcp --light` (edge
  deployment) — não é prioridade agora.

### 3.2 Gemini 3.5 — atualização do family

| Model ID                      | Família    | Strengths                                      |
| ----------------------------- | ---------- | ---------------------------------------------- |
| `gemini-3.5-pro`              | Gemini 3.5 | Reasoning + multimodal premium                 |
| `gemini-3.5-flash`            | Gemini 3.5 | **Novo default do Vectora** (substitui 2.5)    |
| `gemini-3.5-flash-image`      | Gemini 3.5 | "nano-banana-pro" — image generation high-end  |
| `gemini-3.5-flash-image-nano` | Gemini 3.5 | "nano-banana" — image generation rápido/barato |
| `gemini-3.5-flash-audio`      | Gemini 3.5 | TTS streaming + voice variants                 |

Notas:

- `gemini-2.5-flash` continua disponível por compat, mas o **default
  passa para `gemini-3.5-flash`** assim que SLA do Google estabilizar
  (acompanhar status page por 2 semanas pré-flip).
- Modelos `-image` e `-audio` **não aparecem no chat picker** — são
  consumidos via tools (§5) e routing automático (§6).

### 3.3 Aliases lógicos para o user

Em vez de o user escolher `gemini-3.5-flash-image-nano`, ele escolhe
em Settings → Mídia:

```
Geração de imagens:
  ◉ Rápida e barata  → gemini-3.5-flash-image-nano
  ○ Alta qualidade   → gemini-3.5-flash-image
  ○ OpenAI gpt-image → gpt-image-1
```

Aliases mapeados em `chat/lib/config/media-providers.ts`.

---

## 4. Features pendentes (IA-1 a IA-N)

### IA-1 — Camada `src/services/media/`: Protocols + factories

> Tudo que segue (IA-2 a IA-N) depende desta camada. Mesmo padrão de
> abstração do `src/services/utils.load_llm()` que já existe para chat.

```python
# src/services/media/protocols.py
class ImageGenerator(Protocol):
    async def generate(
        self,
        prompt: str,
        *,
        size: ImageSize = "1024x1024",
        n: int = 1,
        reference_images: list[bytes] | None = None,
        style_hint: str | None = None,
    ) -> list[GeneratedImage]: ...

    async def edit(
        self,
        source: bytes,
        prompt: str,
        *,
        mask: bytes | None = None,
    ) -> GeneratedImage: ...

class Transcriber(Protocol):
    async def transcribe(
        self,
        audio: bytes,
        *,
        language: str | None = None,
        timestamps: bool = False,
        diarization: bool = False,  # cohere transcribe suporta
    ) -> Transcript: ...

class Synthesizer(Protocol):
    async def synthesize(
        self,
        text: str,
        *,
        voice: VoiceId,
        language: str | None = None,
        speed: float = 1.0,
        ssml: bool = False,
    ) -> AsyncIterator[bytes]: ...  # stream de chunks PCM/MP3
```

Factories em `src/services/media/factory.py`:

```python
def get_image_generator(user_id: str | None = None) -> ImageGenerator: ...
def get_transcriber(user_id: str | None = None) -> Transcriber: ...
def get_synthesizer(user_id: str | None = None) -> Synthesizer: ...
```

Cada factory lê `effective_env` do user (B1/C10), aplica políticas de
tier (K6), retorna a implementação correta. Cache singleton por
`(user_id, provider_version)`.

### IA-2 — `image_generate` tool

**O que é**: tool LangGraph que gera imagem a partir de prompt.
Disponível para o agente decidir usar (orchestrator + coder subagents).

```python
# src/tools/image.py
@tool(
    metadata={
        "render_hint": "image_preview",
        "category": "media",
        "destructive": False,  # mas billing-destructive (§9)
        "icon": "image",
    },
)
async def image_generate(
    prompt: str,
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1024x1024",
    n: int = 1,
    style: Literal["natural", "vivid", "diagram", "photo"] = "natural",
    *,
    config: RunnableConfig,
) -> ImageGenResult:
    """Gera imagem(ns) a partir do prompt. Use para diagramas,
    mockups, ícones, ilustrações. Não use para edição de imagem
    existente (use image_edit). Não use para gerar vídeo (não suportado)."""
    user_id = _user_from_config(config)
    require_media_quota(user_id, kind="image", cost_estimate_usd=...)
    gen = get_image_generator(user_id)
    images = await gen.generate(prompt, size=size, n=n, style_hint=style)
    asset_ids = [persist_asset(user_id, img) for img in images]  # §8
    return ImageGenResult(asset_ids=asset_ids, prompt=prompt, ...)
```

Retorno tipado, com `asset_id` que o frontend resolve via `GET
/v1/assets/{id}` (§8). **Nunca** retorna base64 inline grande no SSE —
explode o adapter.

### IA-3 — `image_edit` tool

Edição de imagem existente. Aceita mascara opcional (inpaint) ou
prompt de modificação global (Gemini nano-banana suporta ambos via
"reference image + prompt").

```python
@tool(metadata={"render_hint": "image_preview", ...})
async def image_edit(
    source_asset_id: str,
    prompt: str,
    mask_asset_id: str | None = None,
    *,
    config: RunnableConfig,
) -> ImageGenResult: ...
```

Use case principal: "regenere essa imagem com fundo azul" sem precisar
reescrever o prompt original.

### IA-4 — `audio_transcribe` tool

```python
@tool(metadata={"render_hint": "code_block", "category": "media", ...})
async def audio_transcribe(
    audio_asset_id: str,
    language: str | None = None,
    diarization: bool = False,
    *,
    config: RunnableConfig,
) -> Transcript:
    """Transcreve áudio em texto. Suporta diarização (separar falantes)
    via Cohere Transcribe. Use quando o user anexa áudio ou pede
    transcrição de gravação."""
```

Retorna `Transcript` com `text`, `segments` (timestamps), `speakers`
opcionais. Render hint `code_block` mostra texto + timestamps; com
diarização, render hint `transcript` (novo, §7).

### IA-5 — `audio_synthesize` tool (TTS)

```python
@tool(metadata={"render_hint": "audio_player", ...})
async def audio_synthesize(
    text: str,
    voice: str = "default",
    language: str | None = None,
    speed: float = 1.0,
    *,
    config: RunnableConfig,
) -> AudioAsset:
    """Sintetiza áudio a partir de texto. Use quando o user pede
    'leia em voz alta', 'gere áudio de…', ou explicitamente solicita
    TTS. NÃO use proativamente em toda resposta — TTS é opt-in pelo
    user via Settings (UX-33) ou per-message via botão 🔊."""
```

Importante: a tool em si é **raramente chamada pelo agente** — é
exposta para casos em que o user pede explicitamente. O TTS "ler em
voz alta cada resposta" é feature do frontend (§7), não tool.

### IA-6 — Tools sobre transcrição (continuação)

- `audio_translate(asset_id, target_lang)` — opcional v2, transcreve +
  traduz via mesmo provider.
- `audio_summarize(asset_id)` — passa transcript pelo LLM com prompt
  de resumo. Útil para "resuma essa reunião gravada". **Composição de
  tools**, não nova tool primitiva.

### IA-7 — STT remoto (complementa `useVoiceInput`)

Hoje o frontend tem `useVoiceInput` (Web Speech API). Lacunas (já
mapeadas em UX-32):

- Safari/Firefox sem suporte → fallback remoto.
- User pode preferir Cohere/Whisper por privacidade (Web Speech roteia
  pelo Google em Chrome).

**Implementação**:

- Frontend: gravação local via `MediaRecorder` (já disponível em todos
  os browsers), upload do blob para `POST /v1/audio/transcribe` (rota
  pública sob OAuth do Bloco J).
- Backend: roteia para `get_transcriber(user_id)` → Cohere por default.
- Streaming opcional: Cohere Transcribe suporta WebSocket streaming;
  v2 do Vectora pode usar para transcrição em tempo real (não-prioritário).

UI: no chat input, ao lado do botão de microfone existente, badge
mostrando provider ("Browser" vs "Cohere"). Toggle em Settings → Voz.

### IA-8 — TTS streaming de respostas longas

Botão "🔊 Ouvir" em cada mensagem do agente (UX-33). Implementação:

- Frontend chama `POST /v1/audio/synthesize` com o texto da mensagem;
  recebe stream de chunks MP3/PCM.
- `MediaSource` API faz append progressivo no `<audio>` element —
  começa a tocar antes do stream terminar (latency-first).
- Skip de code-blocks ao falar (regex remove ` ```...``` ` blocks antes
  de mandar pro TTS — não faz sentido ler código char por char).
- Pause/resume/cancel via controles HTML5 padrão.

### IA-9 — Routing automático no orchestrator

Novo node `media_intent` no orchestrator que detecta requests de mídia
e roteia para a tool certa **sem o user precisar saber qual tool
chamar**:

```
User: "Cria uma imagem do logo da Vectora estilo neon roxo"
  → media_intent classifica: "image_generation"
  → orchestrator dispara image_generate tool
  → render_hint image_preview na resposta

User: "Transcreve isso aqui [áudio.mp3]"
  → media_intent classifica: "transcription"
  → orchestrator dispara audio_transcribe tool

User: "Lê em voz alta a próxima resposta"
  → media_intent classifica: "tts_directive_persistent"
  → seta thread.metadata.auto_tts = true
  → próxima resposta dispara audio_synthesize após o stream de texto
```

`media_intent` é um node **leve** (não subagent inteiro) — só um
prompt curto + LLM Flash classificando em 5 categorias
(`image_gen`, `image_edit`, `transcribe`, `tts_request`, `none`). Cache
agressivo (300 ms p95).

### IA-10 — Sub-agent dedicado a mídia (opcional v2)

Se o volume de tool calls de mídia crescer, criar `media_agent` como
subagent específico (mesmo padrão de `coder`/`search`/`rag`). Hoje as
tools podem viver no orchestrator direto sem perda. Reavaliar quando

> 20% das mensagens da semana tocarem em mídia.

---

## 5. Tools (resumo do registry pós-IA+)

Espelha o que entra em `src/tools/__init__.py::ALL_TOOLS`:

| Tool               | render_hint     | category | destructive | HITL                 |
| ------------------ | --------------- | -------- | ----------- | -------------------- |
| `image_generate`   | `image_preview` | media    | false\*     | só se cost>threshold |
| `image_edit`       | `image_preview` | media    | false\*     | idem                 |
| `audio_transcribe` | `transcript`    | media    | false       | não                  |
| `audio_synthesize` | `audio_player`  | media    | false\*     | não                  |

`*` — não destrutivas no FS, mas **billing-destructive** (consumem
créditos). Ver §9 sobre HITL por custo.

Todas registradas no `services/tool_resolver.resolve_tools(user_id)`
respeitando `tool_policy` (C2). Admin pode desabilitar `image_generate`
para users específicos (gate de custo).

---

## 6. Graph nodes e routing

### 6.1 Novo node `media_intent`

Inserido entre `orchestrator_decide` e `dispatch_tool`. Lógica:

```python
async def media_intent(state: AgentState) -> AgentState:
    last_user_msg = state.messages[-1].content
    if not _has_media_signals(last_user_msg, state.attachments):
        return state  # passthrough
    classification = await _classify_media_intent(last_user_msg, state)
    state.media_intent = classification  # downstream tools veem
    return state
```

`_has_media_signals` é heurística rápida (regex por "gere uma imagem",
"transcreve", "lê em voz alta", "🎤", presença de attachment de áudio).
Falha-aberto → só chama LLM se sinal positivo (custo zero no caso comum).

### 6.2 Render hints novos

Adicionar a `chat/lib/types/render.ts::RenderHint`:

```ts
export type RenderHint =
  | "json"
  | "diff"
  | "code_block"
  | "terminal"
  | "search_results"
  | "table"
  | "queue_badge"
  | "queue_progress"
  | "artifact_card"
  | "image_preview" // NOVO
  | "image_grid" // NOVO — múltiplas imagens (n>1)
  | "audio_player" // NOVO
  | "transcript"; // NOVO
```

Dispatcher em `chat/components/chat/tool-call-renderer.tsx` ganha 4
cases novos.

### 6.3 Eventos SSE novos

```ts
type StreamEvent =
  | ...
  | {
      type: "media_asset";
      asset_id: string;
      kind: "image" | "audio" | "transcript";
      mime_type: string;
      size_bytes: number;
      url: string;  // URL pré-assinada, TTL 1h
      metadata?: Record<string, unknown>;
    }
  | {
      type: "tts_chunk";
      sequence: number;
      data_base64: string;
      mime_type: string;
      final: boolean;
    };
```

`media_asset` substitui o output JSON do tool quando o asset é grande
(imagens, áudios). `tts_chunk` é específico para streaming TTS quando
o frontend solicita "leia esta resposta" durante o stream principal.

---

## 7. UX no chat — componentes novos

### 7.1 `<ImagePreview>` — image_preview

- Container 16:9 com aspect-ratio do output real.
- Loading skeleton enquanto asset_id resolve.
- Hover overlay:
  - 🔄 Regenerar (call `image_generate` com mesmo prompt)
  - ✏️ Editar (abre input "como modificar?" → `image_edit`)
  - ⬇️ Download
  - 📋 Copiar para clipboard
  - 🔗 Adicionar ao workspace ativo (`/rag add` da imagem)
- Click → modal fullscreen com pan/zoom.

### 7.2 `<ImageGrid>` — image_grid (n>1)

Grid 2×2 ou 3×3 quando `n > 1` em `image_generate`. Cada card é
clicável e tem as mesmas ações do `<ImagePreview>`.

### 7.3 `<AudioPlayer>` — audio_player

- Controles HTML5 nativos + customização Tailwind.
- Waveform visual (lazy — usar `wavesurfer.js` só quando o user dá
  play; bundle separado).
- Speed control (0.5×, 1×, 1.25×, 1.5×, 2×).
- Botão "Baixar" + "Transcrever este áudio" (que chama
  `audio_transcribe` no asset).

### 7.4 `<Transcript>` — transcript

- Texto agrupado por segmento de tempo.
- Quando `diarization=true`: cada falante em cor diferente, label
  "Falante 1", "Falante 2". User pode renomear ("João", "Maria") — vai
  pro storage como override.
- Click no timestamp → seek do áudio original (se asset disponível).
- Botão "Resumir" → cria nova mensagem com `audio_summarize` chain.

### 7.5 Botão 🔊 em cada mensagem do agente

UX-33 do `ux.md` formalizado aqui:

- Visível em hover (mesma posição do "Copiar").
- Click 1× → solicita TTS e toca; muda para ⏸ enquanto toca.
- Click ⏸ → pausa; click ▶ → resume.
- Click "× cancelar" → para e descarrega chunks pendentes.
- Toggle "Auto-leitura" em Settings → Voz → "Ler respostas em voz alta"
  → próxima mensagem dispara TTS automaticamente.

### 7.6 Capture screenshot do desktop (UX-36) — integra com image_edit

Botão "📸 Screenshot" no plus-menu (Electron only). Imagem capturada
vira anexo da próxima mensagem, **e** ganha botão rápido "Editar com
IA" que pré-popula `image_edit` ao invés de mandar para o LLM como
input multimodal.

### 7.7 Microfone visível e funcional

UX-32 formalizado: botão de microfone ao lado do send. Estados:

- Idle: ícone cinza.
- Listening: vermelho pulsante + interim transcript em itálico no input.
- Error: badge + toast.
- Provider fallback: se Web Speech indisponível → usa MediaRecorder +
  IA-7 endpoint. Tooltip mostra qual provider está ativo.

---

## 8. Storage de assets gerados

### 8.1 Layout

```
~/.vectora/assets/
├── <user_id>/
│   ├── <yyyy>/<mm>/<dd>/
│   │   ├── img_<asset_id>.png
│   │   ├── img_<asset_id>.metadata.json
│   │   ├── aud_<asset_id>.mp3
│   │   ├── aud_<asset_id>.metadata.json
│   │   └── txt_<asset_id>.json    # transcripts
```

Particionado por data → cleanup eficiente.

### 8.2 Tabela `vectora_assets`

```sql
CREATE TABLE vectora_assets (
  asset_id     TEXT PRIMARY KEY,              -- sha256[:16] do conteúdo
  user_id      TEXT NOT NULL,
  thread_id    TEXT,                          -- nullable (CLI / batch)
  kind         TEXT NOT NULL CHECK (kind IN ('image','audio','transcript')),
  mime_type    TEXT NOT NULL,
  size_bytes   INTEGER NOT NULL,
  path         TEXT NOT NULL,                 -- relativo a ~/.vectora/assets
  provider     TEXT,                          -- gemini-3.5-flash-image / cohere-transcribe / etc
  prompt       TEXT,                          -- prompt original (imagens)
  cost_usd     REAL,                          -- custo estimado da geração
  created_at   INTEGER NOT NULL,
  expires_at   INTEGER,                       -- nullable; null = permanente até user deletar
  metadata_json TEXT
);
CREATE INDEX idx_assets_user_thread ON vectora_assets(user_id, thread_id);
CREATE INDEX idx_assets_expires ON vectora_assets(expires_at) WHERE expires_at IS NOT NULL;
```

### 8.3 Endpoints REST

- `GET /v1/assets/{id}` → retorna o blob (auth + ownership).
- `GET /v1/assets/{id}/url` → URL pré-assinada com TTL 1h (para embedar
  em `<img>` sem cookie).
- `DELETE /v1/assets/{id}` → user pode apagar.
- `GET /v1/threads/{id}/assets` → lista assets da thread.

### 8.4 GC e quotas

- Assets **temporários** (gerados mas não anexados a mensagem
  persistida em 24h) → TTL 7 dias.
- Assets **anexados a threads** → vivos enquanto a thread existir;
  deletar thread → cascata delete assets.
- Cap por user (default Pro: 5 GB; Plus: 500 MB). UI mostra uso em
  Settings → Mídia → "Espaço de assets".
- Cleanup job em `services/background.py` roda diário às 3am UTC.

---

## 9. Custo, quotas e tier gates

### 9.1 Tabela de custos referência (atualizar trimestralmente)

| Operação                 | Provider               | Custo ref.         |
| ------------------------ | ---------------------- | ------------------ |
| Image gen 1024×1024 nano | Gemini nano-banana     | ~$0.005 / imagem   |
| Image gen 1024×1024 pro  | Gemini nano-banana-pro | ~$0.04 / imagem    |
| Image gen 1024×1024      | OpenAI gpt-image-1     | ~$0.04 / imagem    |
| Image edit 1024×1024     | qualquer               | ≈ mesmo da geração |
| STT por minuto           | Cohere Transcribe      | ~$0.006 / min      |
| STT por minuto           | OpenAI Whisper-1       | ~$0.006 / min      |
| TTS por 1k chars         | Gemini speech          | ~$0.015 / 1k chars |
| TTS por 1k chars         | OpenAI tts-1-hd        | ~$0.030 / 1k chars |

Fonte: `chat/lib/config/media-prices.ts` (versionado, igual UX-46).

### 9.2 Quotas por tier

| Tier                 | Imagens/mês | Min STT/mês | Min TTS/mês | Storage assets |
| -------------------- | ----------- | ----------- | ----------- | -------------- |
| Plus                 | 30          | 30          | 60          | 500 MB         |
| Pro                  | 300         | 300         | 600         | 5 GB           |
| Pay-as-you-go (BYOK) | ∞           | ∞           | ∞           | tier do plano  |

User com API key própria de Gemini/OpenAI/Cohere via
`Settings → Envs` **bypassa** as quotas (BYOK paga direto ao provider).
Backend detecta presença da env e marca `metered: false` na operação.

### 9.3 HITL por custo

Novo gate em `services/agent_factory.py`:

```python
if tool_name in ("image_generate", "image_edit"):
    est_cost = estimate_cost(args, user_id)
    threshold = user.media_hitl_threshold_usd  # default $0.10
    if est_cost > threshold:
        raise HITLInterrupt(
            tool_name=tool_name,
            reason=f"Custo estimado ${est_cost:.3f} excede limite",
            args_json=...,
        )
```

User pode configurar threshold em Settings → Mídia → "Pedir confirmação
acima de $\_\_\_". Default $0.10 (≈ 2 imagens pro ou 20 nano).

### 9.4 Gate de tier em `storage/factory.py` (espelha K6)

```python
def get_image_generator(user_id):
    tier = get_user_tier(user_id)
    quota_remaining = get_quota(user_id, kind="image")
    has_byok = user_has_env(user_id, "GOOGLE_API_KEY") or user_has_env(user_id, "OPENAI_API_KEY")
    if not has_byok and quota_remaining <= 0:
        raise LicenseError(
            f"Quota de imagens esgotada para o plano {tier}. "
            f"Configure VECTORA_TOKEN com plano superior ou adicione "
            f"sua própria GOOGLE_API_KEY/OPENAI_API_KEY em Settings → Envs."
        )
    ...
```

---

## 10. Settings, CLI e MCP

### 10.1 Aba "Mídia" no Settings

Nova subaba `chat/components/layout/settings-dialog/tabs/midia-tab.tsx`:

```
Geração de imagens
  Provider:        [Gemini nano-banana-pro ▼]
  Qualidade default: [Alta ▼]
  HITL acima de:   [$ 0.10]
  Uso este mês:    87 / 300 imagens   [Ver detalhes]

Transcrição (STT)
  Provider:        [Cohere Transcribe ▼]
  Idioma padrão:   [Português (BR) ▼]
  Diarização default: [ ] Off
  Uso este mês:    12 min / 300 min

Síntese de voz (TTS)
  Provider:        [Gemini speech ▼]
  Voz default:     [Aria (feminina) ▼]   [▶ Testar]
  Velocidade:      [1.0×]
  Auto-leitura:    [ ] Ler todas as respostas do agente em voz alta
  Uso este mês:    1.2k / 600 min*

Captura
  Reconhecimento de voz no chat (mic):
    ◉ Browser (rápido, requer Chrome/Edge)
    ○ Provider escolhido acima (universal)

Storage
  Espaço usado: 142 MB / 5 GB
  [Limpar assets > 30 dias]   [Exportar tudo]
```

### 10.2 CLI

```
vectora media gen-image "logo neon roxo, vetorial" --out logo.png
vectora media transcribe gravacao.mp3 --diarize --lang pt-BR
vectora media speak "Olá mundo" --voice aria --out hello.mp3
vectora media list --thread <id>
vectora media quota
```

Espelha as tools internas via mesmo `services/media/factory.py`.

### 10.3 MCP exposure

Tools `image_generate`, `image_edit`, `audio_transcribe`,
`audio_synthesize` ficam expostas via `src/mcp/server.py`. Claude Code,
Codex e outros agentes via MCP podem delegar `image_generate` ao
Vectora — útil quando o agente externo não tem capability própria.

Tier gates ainda aplicam — chamada MCP consome a quota do `VECTORA_TOKEN`
configurado.

### 10.4 REST API v1 (Bloco J)

```
POST /v1/media/images               body: {prompt, size, n, style}
POST /v1/media/images/{id}/edit     body: {prompt, mask_asset_id}
POST /v1/media/transcribe           multipart: audio + {language, diarize}
POST /v1/media/speak                body: {text, voice, language, speed}
                                    returns: SSE stream of audio chunks
GET  /v1/media/voices               lista vozes por provider/idioma
GET  /v1/media/quota                quotas atuais do user
```

OAuth client credentials (J1). Scope `media` cobre todos.

---

## 11. i18n

Strings novas em `chat/lib/i18n/strings.csv.ts` (en/es/pt-BR):

```
media.image.generating,Generating image…,Generando imagen…,Gerando imagem…
media.image.regenerate,Regenerate,Regenerar,Regenerar
media.image.edit,Edit,Editar,Editar
media.image.download,Download,Descargar,Baixar
media.image.cost_warning,This will cost ~{cost}. Continue?,…,Isso vai custar ~{cost}. Continuar?
media.audio.play,Play,Reproducir,Tocar
media.audio.pause,Pause,Pausar,Pausar
media.audio.transcribe,Transcribe,Transcribir,Transcrever
media.tts.read_aloud,Read aloud,Leer en voz alta,Ler em voz alta
media.tts.auto,Read all responses aloud,Leer todas las respuestas en voz alta,Ler todas as respostas em voz alta
media.stt.listening,Listening…,Escuchando…,Escutando…
media.stt.provider_fallback,Using {provider} (browser unavailable),…,Usando {provider} (navegador indisponível)
media.quota.exhausted,Monthly quota exhausted,Cuota mensual agotada,Quota mensal esgotada
media.quota.upgrade,Upgrade plan,Mejorar plan,Fazer upgrade
media.diarization.speaker,Speaker {n},Hablante {n},Falante {n}
... (~40 chaves no total)
```

UX-57 (audit de strings hardcoded) cobre rejeição de PRs sem essas
três colunas.

---

## 12. Priorização

| #       | Feature                                                | Impacto | Esforço | Prioridade |
| ------- | ------------------------------------------------------ | ------- | ------- | ---------- |
| IA-1    | Camada `services/media/` + Protocols                   | Crítico | Médio   | **P1**     |
| IA-2    | `image_generate` tool + render `image_preview`         | Alto    | Médio   | **P1**     |
| IA-4    | `audio_transcribe` tool + render `transcript`          | Alto    | Médio   | **P1**     |
| IA-7    | STT remoto fallback (Cohere/Whisper via MediaRecorder) | Alto    | Médio   | **P1**     |
| 3.2     | Atualizar registry: Gemini 3.5 family                  | Médio   | Pequeno | **P1**     |
| IA-9    | Node `media_intent` (routing automático)               | Alto    | Médio   | **P2**     |
| IA-5    | `audio_synthesize` tool                                | Médio   | Pequeno | **P2**     |
| IA-8    | TTS streaming de respostas longas (botão 🔊)           | Alto    | Médio   | **P2**     |
| §8      | Storage de assets + tabela + GC                        | Crítico | Médio   | **P2**     |
| §9      | Quotas + tier gates + HITL por custo                   | Crítico | Médio   | **P2**     |
| 3.1     | Aya Expanse 32B/8B + Aya Tiny no registry              | Médio   | Pequeno | **P2**     |
| §10.1   | Aba "Mídia" no Settings                                | Alto    | Médio   | **P2**     |
| 7.1–7.5 | Componentes UI (ImagePreview, AudioPlayer, Transcript) | Alto    | Médio   | **P2**     |
| IA-3    | `image_edit` tool                                      | Médio   | Médio   | **P3**     |
| IA-6    | `audio_translate`, `audio_summarize` (composição)      | Médio   | Pequeno | **P3**     |
| 7.6     | Screenshot capture (Electron) + edit com IA            | Médio   | Médio   | **P3**     |
| §10.4   | REST API v1 `/v1/media/*`                              | Médio   | Médio   | **P3**     |
| §10.3   | MCP exposure das tools de mídia                        | Médio   | Pequeno | **P3**     |
| §10.2   | CLI `vectora media …`                                  | Médio   | Médio   | **P3**     |
| 7.7     | Polish do microfone (provider badge + toggle)          | Médio   | Pequeno | **P3**     |
| IA-10   | `media_agent` subagent dedicado                        | Baixo   | Grande  | **P5**     |

---

## 13. Sequência de implementação recomendada

```
Sprint M1 — Foundation (2 semanas)
  IA-1       services/media/ Protocols + factories
  3.2        registry Gemini 3.5 (modelos chat + image + audio)
  §8 base    tabela vectora_assets + endpoints /v1/assets
  IA-2       image_generate tool (provider: Gemini nano-banana-pro)
  7.1        <ImagePreview> + <ImageGrid> + dispatcher render hint

Sprint M2 — STT completo (1.5 semanas)
  IA-4       audio_transcribe tool (provider: Cohere Transcribe)
  IA-7       fallback remoto MediaRecorder → /v1/media/transcribe
  7.4        <Transcript> com diarização opcional
  7.7        polish do mic no chat-input + provider badge
  3.1        Aya Expanse/Tiny no registry (em paralelo, low-risk)

Sprint M3 — TTS + auto-routing (1.5 semanas)
  IA-5       audio_synthesize tool (provider: Gemini speech)
  IA-8       botão 🔊 + streaming chunks via MediaSource
  IA-9       node media_intent (classifier rápido)
  7.3        <AudioPlayer> + waveform lazy
  7.5        toggle auto-leitura em Settings → Voz

Sprint M4 — Custo & governança (1 semana — bloqueia lançamento)
  §9         quotas + tier gates + HITL por custo
  §10.1      aba "Mídia" no Settings
  i18n       ~40 chaves novas em 3 idiomas
  pricing    chat/lib/config/media-prices.ts versionado

Sprint M5 — Edição & extensões (1 semana)
  IA-3       image_edit tool + UI "✏️ Editar"
  IA-6       audio_translate + audio_summarize (composições)
  7.6        screenshot capture Electron

Sprint M6 — API & integração (1 semana)
  §10.4      REST /v1/media/*
  §10.3      MCP exposure das tools
  §10.2      CLI vectora media
  Atualizar  pitch_deck.md (remover "sem áudio") + products.md

Sprint M7 — Polish & v2 (opcional)
  IA-10      media_agent subagent (se métricas justificarem)
  Diarização avançada — rename de speakers persistido
  TTS voice cloning (Gemini suporta — opt-in, gate de tier)
```

---

## 14. Notas de arquitetura

### 14.1 Multimodal native ≠ tool

Gemini 3.5 vê imagens e ouve áudio **direto** no input — sem precisar
chamar tool. Quando o user anexa `audio.mp3` ao chat, duas alternativas:

1. **Passar como input multimodal** ao LLM (Gemini ou Anthropic 4
   suportam). LLM "ouve" o áudio e responde sobre ele.
2. **Chamar `audio_transcribe` tool** primeiro, depois passar
   transcript como texto.

Quando usar cada um? Heurística no `media_intent`:

- User pediu "transcreve isso" / "passa pra texto" → **tool**
  (resultado é o transcript em si).
- User pediu "resume essa reunião" / "o que essa pessoa falou" →
  **multimodal** (LLM consome áudio direto).

Image gen é sempre tool — LLMs não geram imagem como output direto
(exceto Gemini com `gemini-3.5-flash-image`, mas mesmo nesse caso
encapsulamos via tool por consistência de pipeline).

### 14.2 Assets como cidadãos de primeira classe

Assets gerados (imagem, áudio, transcript) **não** são strings JSON
embutidas em mensagens — são **entidades persistidas** com `asset_id`.
Mensagem carrega referência (`asset_id`), não conteúdo. Vantagens:

- Re-render barato (não re-baixa o blob).
- Compartilhamento (share thread expõe URL do asset, não embed).
- GC granular (apagar 1 asset não toca o resto da thread).
- Streaming (TTS chunks vão por canal SSE separado, não inflam o
  histórico).

Mesmo padrão do `ArtifactCard` (B+) — generalizar para "media asset".

### 14.3 Cohere é parceiro, não monopolista

A parceria com Cohere cobre embedding + reranker (RAG core). Adicionar
**Cohere Transcribe** é coerente — outra peça do mesmo provider.
**Não** adicionar Cohere onde eles são fracos (eles não têm image gen
nem TTS competitivos hoje). Gemini cobre essas lacunas naturalmente.

Política: sempre que Cohere lançar produto novo numa modalidade que
temos, **avaliar como provider primário** dessa modalidade, mas não
forçar (qualidade fala mais alto que parceria).

### 14.4 BYOK é o escape para power users

Tudo que tem quota tem BYOK opcional. User cola sua chave Gemini/OpenAI
em Settings → Envs → quotas não se aplicam. Justifica preços baixos do
Plus/Pro — "está pesado? pague direto ao provider, sem markup nosso".

Mesmo argumento que o Chat de hoje (LLM key opcional). Estender para
mídia.

### 14.5 Streaming TTS é o teste de fogo

Cada outra modalidade é request/response. TTS é stream — backend
empurra chunks PCM/MP3 enquanto o LLM ainda está gerando texto.
Implicações:

- SSE adapter precisa suportar `tts_chunk` events sem bloquear o
  stream principal de tokens.
- Frontend precisa MediaSource Buffer com fila pequena (latency-first;
  jitter > 200ms é audível).
- Cancelamento (user clica ⏸) precisa propagar até o provider para
  não desperdiçar tokens TTS gerados depois.

Recomendação: implementar streaming TTS por **último** (Sprint M3),
quando o resto do stack estiver maduro. MVP pode ser request/response
(gera áudio inteiro, depois toca) — funcional embora menos polished.

### 14.6 Image gen como vetor de spam/abuso

Image generation é o único produto que **gera conteúdo arbitrário a
custo real**. Vetores de abuso:

- User com Plus Trial gera 30 imagens em 1 hora para revender em outro
  serviço.
- User pede imagens NSFW / com pessoas reais (deepfake) — provider
  filtra, mas log fica no Vectora.

Mitigação:

- Rate limit agressivo independente da quota mensal (`5 imagens / 5 min`
  por user, configurável admin).
- Tools de mídia logam **prompt + asset_id** em
  `vectora_media_audit` (separado do tracer geral) para auditoria
  forense.
- Termos de uso (`docs/...`) explicitamente proíbem geração de:
  deepfakes, conteúdo sexual envolvendo menores, conteúdo de ódio.
  Violação → revogação de token sem reembolso (mesma cláusula de
  abuso de OEM em `docs/oem.md`).

### 14.7 Não geramos vídeo — decisão explícita

Repetir aqui o que o user definiu: **vídeo está fora de escopo**.
Razões:

- Custo 20–100× maior que imagem.
- Latência inviável para UX de chat (3–10 min por vídeo curto).
- Qualidade ainda inconsistente (out of distribution em prompts
  técnicos).
- Nenhum dos providers do nosso stack atual tem vídeo competitivo.

Quando reabrir? Apenas se Cohere ou Gemini lançar vídeo
sub-30-segundos com latência < 30s e custo < $0.10. Hoje (junho 2026),
nenhum cumpre esses três simultaneamente.

---

## 15. Documentação a atualizar quando este plano for aprovado

| Arquivo              | Mudança                                                             |
| -------------------- | ------------------------------------------------------------------- |
| `docs/pitch_deck.md` | Remover seção "Não há áudio/voz"; adicionar "6 modalidades de IA"   |
| `docs/products.md`   | Tier 1 ganha TTS/STT/image gen como capabilities default            |
| `docs/plan.md`       | Bloco H (ou H+ novo) referencia este documento                      |
| `docs/ux.md`         | UX-32, UX-33 marcados como "implementados em Sprint M2/M3"          |
| `docs/apoiadores.md` | Cohere ganha menção de Transcribe; Gemini ganha menção de speech    |
| `docs/oem.md`        | OEM license cobre uso de tools de mídia (passa pelas mesmas quotas) |
| `chat-first.md`      | Render hints novos (`image_preview`, `audio_player`, `transcript`)  |
