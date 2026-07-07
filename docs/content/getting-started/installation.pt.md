---
title: Instalação
weight: 2
---

Vectora é distribuído como um **app desktop nativo** (Electron + backend Python compilado) para Windows, macOS e Linux, com auto-update embutido. Não existe uma "imagem Docker única" do produto — o Docker, quando usado, sobe só a infraestrutura opcional (Postgres/Redis/Qdrant do modo complete), nunca o Vectora em si.

## Opção 1 — Instalador nativo (recomendado)

Baixe o instalador do seu sistema operacional:

| SO      | Formato                                  | Assinatura                             |
| ------- | ---------------------------------------- | -------------------------------------- |
| Windows | `.msi` ou `.exe` (NSIS)                  | Certificado EV (Azure Trusted Signing) |
| macOS   | `.dmg` (builds separados Intel e Apple Silicon) | Apple Developer ID + notarizado |
| Linux   | `.AppImage`, `.deb` ou `.rpm`            | sem assinatura                         |

Instale normalmente (duplo clique / `dpkg -i` / `rpm -i`). O app abre com o backend já embutido — não precisa instalar Python, Node, nem nenhuma dependência separada.

Atualizações futuras chegam automaticamente via auto-update (servido por `updates.vectora.company`).

## Opção 2 — A partir do código-fonte (dev)

Para contribuir ou rodar em modo desenvolvimento:

**Pré-requisitos**: Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js 24+, `pnpm`.

```bash
git clone https://github.com/vectora-company/vectora.git
cd vectora/vectora

uv sync                          # dependências Python
pnpm --dir frontend install       # dependências do frontend

cp .env.example .env
# edite o .env: GOOGLE_API_KEY (ou outro provider), COHERE_API_KEY, TAVILY_API_KEY
```

Duas janelas de terminal:

```bash
# Terminal 1 — backend completo + MCP (/mcp) + SPA (porta 8080)
uv run vectora start --port 8080

# Terminal 2 — frontend dev (Vite, porta 3000, faz proxy pra API)
pnpm --dir frontend dev
```

Abra `http://localhost:3000`. O primeiro usuário a se cadastrar vira administrador root.

## Chaves de API necessárias

| Chave                                                                | Obrigatória? | Para quê                                      |
| -------------------------------------------------------------------- | ------------ | --------------------------------------------- |
| Um provedor LLM (Gemini, OpenAI, Anthropic, Cohere, ou Ollama local) | Sim          | Chat, geração de código, síntese de respostas |
| `COHERE_API_KEY` (ou VoyageAI)                                       | Sim, pro RAG | Embeddings + reranking                        |
| `TAVILY_API_KEY`                                                     | Opcional     | Busca web                                     |

O seletor de modelo no chat só mostra os providers com chave configurada — sem chave, sem provider na lista.

## Licença

O app funciona **sem licença** no modo Free (100% local). Para desbloquear os recursos Pro (chat web multi-usuário, storage complete, webhooks, API REST com rate limit maior), você precisa de um `VECTORA_TOKEN`, obtido no [dashboard](https://vectora.company/dashboard) após assinar um plano pago.

## Próximo passo

→ [Início rápido](../quick-start)
