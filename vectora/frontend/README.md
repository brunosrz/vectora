# <img src="../assets/vectora.svg" width="28" height="28"> Vectora Chat

Interface web do **Vectora** — SPA **Vite + React 19 + TanStack Router** (TypeScript),
servida pelo FastAPI em produção e via proxy do Vite dev em desenvolvimento.

---

## Arquitetura

```
Browser
  ↓ HTTP / SSE / WebSocket (mesmo origin)
FastAPI (vectora start)
  ├── /              — SPA Vite (frontend/dist/ via StaticFiles)
  ├── /auth/*        — autenticação JWT + cookies httpOnly
  ├── /vectora.*     — handlers de chat/threads/workspaces/terminal
  ├── /rag, /models  — settings de RAG, providers configurados
  ├── /workspaces/{id}/context-graph — build/status/query do grafo
  ├── /mcp           — MCP server (sempre-ativo, SSE)
  └── /admin/*       — painel de administração
        ↓ LangGraph (astream_events) → deep-agent
```

Em desenvolvimento, o Vite dev server (`:5173`) faz proxy de `/auth/*`, `/vectora.*`,
`/rag`, `/models`, `/mcp`, etc. para o FastAPI (`:8080`). Em produção, tudo na mesma porta.

---

## Pré-requisitos

- [Node.js 24+](https://nodejs.org/) e [pnpm 11+](https://pnpm.io/)
- Vectora rodando (`vectora start`, ou `vectora start --headless` para só a API)

---

## Desenvolvimento

```bash
# 1. Instale as dependências
pnpm install

# 2. (opcional) configure o ambiente
cp .env.example .env.local
# VITE_VECTORA_API_URL=http://localhost:8080

# 3. Inicie o Vectora em outro terminal
vectora start --headless   # ou: uv run vectora start --headless

# 4. Inicie o dev server (Vite)
pnpm dev
```

Acesse `http://localhost:5173`.

> **i18n:** as mensagens são compiladas pelo Paraglide JS. Rode `pnpm i18n:compile`
> sempre que editar `messages/{en,es,pt}.json` (o módulo gerado em `lib/paraglide/`
> é gitignored). O `pnpm typecheck` já compila antes de checar.

---

## Estrutura do projeto

```
frontend/
├── src/
│   ├── main.tsx                # entrada da SPA
│   ├── router.tsx              # config do TanStack Router
│   ├── styles.css              # theme (tokens CSS) + Tailwind
│   └── routes/                 # rotas (TanStack Router file-based)
│       ├── __root.tsx
│       ├── index.tsx
│       ├── session/$threadId.tsx
│       ├── auth/, integrations/, share/
├── components/
│   ├── chat/                   # composer, mensagens, model selector
│   ├── workbench/              # painel lateral multi-aba (ver abaixo)
│   ├── settings/               # dialogs de preferências/ambiente/admin (lazy)
│   ├── sidebar/, header/, ui/  # shadcn/Radix
├── lib/
│   ├── api/vectora-client.ts   # cliente SSE/REST (StreamEvent union)
│   ├── hooks/                  # use-stream-handler, use-context-graph, etc.
│   ├── stores/                 # Zustand (workbench, workspaces, settings…)
│   └── paraglide/              # i18n gerado (gitignored)
├── messages/{en,es,pt}.json    # fonte das traduções
├── vite.config.ts
└── package.json
```

---

## Workbench (painel lateral)

No modo Code, o chat tem um painel multi-aba que renderiza a partir de dados do
backend. Ordem das abas: **File System → Git → Plan → Segundo plano → Preview →
Memory (RAG) → Context Graph → Terminal**.

- **Memory (RAG)** e **Context Graph** têm settings próprios (gear): o RAG configura
  reranker on/off + top_k, providers (Cohere/Voyage/auto), tipos de arquivo e coleções;
  o Context Graph configura tipos a indexar e o modo (semântico/AST).
- Detalhes de cada aba no [README do Vectora](../README.md#workbench-painel-lateral).

---

## Schema-driven rendering

O backend declara como exibir cada tool via `metadata={"render_hint": ...}`. Um único
`<ToolCall>` despacha para o renderer correto pelo `render_hint` — adicionar uma tool
nova com um hint conhecido funciona no chat sem mudança no TypeScript.

| render_hint       | Usado por                              |
| ----------------- | -------------------------------------- |
| `diff`            | `file_edit`, `git_diff`                |
| `code_block`      | `file_read`, `file_write`              |
| `terminal_output` | `terminal`                             |
| `search_results`  | `vector_search`, `web_search`          |
| `table`           | `grep`, `list_dir`, `manage_retriever` |
| `queue_progress`  | `ingest_docs`                          |
| `artifact`        | `create_artifact`                      |
| `json`            | fallback universal                     |

---

## Variáveis de ambiente

| Variável                     | Descrição                       | Padrão                  |
| ---------------------------- | ------------------------------- | ----------------------- |
| `VITE_VECTORA_API_URL`       | URL do backend Vectora          | `http://localhost:8080` |
| `VITE_VECTORA_AUTH_REQUIRED` | Exige login para acessar o chat | `true`                  |

---

## Tecnologias

| Camada      | Tecnologia                                                                             |
| ----------- | -------------------------------------------------------------------------------------- |
| Build / SPA | [Vite](https://vitejs.dev/) + [React 19](https://react.dev/)                           |
| Roteamento  | [TanStack Router](https://tanstack.com/router)                                         |
| Estado      | [Zustand](https://zustand-demo.pmnd.rs/)                                               |
| UI          | [shadcn/ui](https://ui.shadcn.com/) (Radix) + [Tailwind CSS](https://tailwindcss.com/) |
| i18n        | [Paraglide JS](https://inlang.com/m/gerre34r/library-inlang-paraglideJs)               |
| Testes      | [Vitest](https://vitest.dev/) + Testing Library                                        |

---

## Relacionado

- [Vectora](../README.md) — backend, arquitetura, build e CLI
- `vectora start` — backend + MCP (/mcp) + SPA em um único processo
- `vectora start --headless` — sobe sem janela (bandeja + backend + MCP)
