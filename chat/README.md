# <img src="../assets/vectora.svg" width="28" height="28"> Vectora Chat

Interface web do **Vectora Agent** — construída com Next.js + Hono (TypeScript) e conectada ao agente via ConnectRPC.

> **Origem:** fork do [chat-langchain](https://github.com/langchain-ai/chat-langchain) (LangChain AI). O backend Python original (LangGraph Cloud + LangSmith + FastAPI) foi removido integralmente e substituído por um backend TypeScript com Hono integrado ao Next.js, que se conecta ao Vectora Agent via `vectora server`.

---

## Arquitetura

```
Browser
  ↓ HTTP (Server-Sent Events)
Next.js App (chat/)
  ├── app/              — UI React + App Router
  └── app/api/**        — Hono backend (mesmo processo, mesma porta)
        ↓ ConnectRPC (server-streaming)
  Vectora Agent (vectora server chat | headless)
        ↓ LangGraph
  graph.py:build_graph()
```

O Hono roda como um route handler do App Router (`app/api/[[...route]]/route.ts`), eliminando a necessidade de servidor separado.

---

## Pré-requisitos

- [Node.js 20+](https://nodejs.org/) e [pnpm](https://pnpm.io/)
- Vectora Agent rodando (`vectora server chat` ou `vectora server headless`)

---

## Desenvolvimento

```bash
# 1. Instale as dependências
pnpm install

# 2. Configure o ambiente
cp .env.example .env.local
# NEXT_PUBLIC_VECTORA_API_URL=http://localhost:8080

# 3. Inicie o Vectora Agent em outro terminal
vectora server headless   # ou: uv run vectora server headless

# 4. Inicie o chat
pnpm dev
```

Acesse `http://localhost:3000`.

---

## Estrutura do Projeto

```
chat/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                   # entrada principal
│   └── api/
│       └── [[...route]]/
│           └── route.ts           # mount do Hono app
├── server/                        # backend Hono (TypeScript)
│   ├── index.ts                   # Hono app factory
│   └── routes/
│       ├── chat.ts                # proxy ConnectRPC → src/api
│       ├── threads.ts             # CRUD de threads
│       └── health.ts              # /health + /metrics
├── lib/
│   ├── types/                     # módulo de tipos (espelha o proto + schema do agente)
│   │   ├── events.ts              # StreamEvent (union discriminada)
│   │   ├── messages.ts            # MessageSchema
│   │   ├── tools.ts               # ToolSchema, ToolCallSchema
│   │   ├── render.ts              # RenderHint, ToolCategory
│   │   └── thread.ts              # Thread, HistoryMessage
│   ├── gen/                       # stubs ConnectRPC gerados (build-time, não commitado)
│   ├── hooks/
│   │   ├── chat/
│   │   └── threads/
│   └── utils/
├── components/
│   ├── message/
│   │   └── Message.tsx            # componente único — adapta por role
│   ├── tool-call/
│   │   └── ToolCall.tsx           # dispatch por render_hint
│   ├── chat/
│   ├── layout/
│   └── ui/                        # Radix UI / shadcn
├── public/
├── next.config.ts
└── package.json
```

---

## Schema-driven rendering

O Vectora Agent expõe um endpoint `/api/tools/schema` com os metadados de cada tool:

```json
{
  "tools": [
    {
      "name": "file_edit",
      "render_hint": "diff",
      "category": "filesystem",
      "destructive": true,
      "icon": "file-edit"
    }
  ]
}
```

O chat usa esses metadados para renderizar cada tool call sem componentes hardcoded por nome. Um único `<ToolCall>` despacha para o renderer correto via `render_hint`:

| render_hint       | Renderer        | Usado por                              |
| ----------------- | --------------- | -------------------------------------- |
| `diff`            | `DiffViewer`    | `file_edit`, `git_diff`                |
| `code_block`      | `CodeBlock`     | `file_read`, `file_write`              |
| `terminal_output` | `TerminalBlock` | `terminal`                             |
| `search_results`  | `SearchResults` | `vector_search`, `web_search`          |
| `table`           | `DataTable`     | `grep`, `list_dir`, `manage_retriever` |
| `queue_progress`  | `QueueProgress` | `ingest_docs`                          |
| `artifact`        | `ArtifactCard`  | `create_artifact`                      |
| `json`            | `JsonViewer`    | fallback universal                     |

Adicionar uma nova tool no agente com `metadata={"render_hint": "table"}` funciona no chat sem nenhuma mudança no TypeScript.

---

## Variáveis de Ambiente

| Variável                      | Descrição            | Padrão                  |
| ----------------------------- | -------------------- | ----------------------- |
| `NEXT_PUBLIC_VECTORA_API_URL` | URL do Vectora Agent | `http://localhost:8080` |

---

## Tecnologias

| Camada           | Tecnologia                                                                       |
| ---------------- | -------------------------------------------------------------------------------- |
| Framework        | [Next.js 16](https://nextjs.org/) (App Router)                                   |
| Backend TS       | [Hono](https://hono.dev/) (integrado ao Next.js)                                 |
| Protocolo        | [ConnectRPC](https://connectrpc.com/) (server-streaming)                         |
| UI               | [Radix UI](https://www.radix-ui.com/) + [Tailwind CSS](https://tailwindcss.com/) |
| Geração de tipos | [buf](https://buf.build/) (proto → TypeScript)                                   |

---

## Relacionado

- [Vectora Agent](../README.md) — o agente que o chat consome
- `vectora server chat` — serve agent + chat estático em um único processo
- `vectora server headless` — serve só o agent (sem static files)
