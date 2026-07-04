---
title: Troubleshooting
weight: 6
---

## O seletor de modelo está vazio

Nenhum provedor de LLM tem chave de API configurada. Vá em **Configurações → Preferências → Geral** (ou edite `.env`/`~/.vectora/.env`) e adicione ao menos uma: `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `COHERE_API_KEY`, ou configure um endpoint Ollama local.

## RAG não retorna resultados / erro de embeddings

O RAG depende de `COHERE_API_KEY` (ou uma chave VoyageAI configurada como alternativa) para gerar embeddings e rerank. Sem isso, a indexação falha silenciosamente ou a busca vetorial não retorna nada. Confirme a chave em **Configurações → Ambiente → Envs**.

## O agente não consegue escrever arquivos / rodar comandos

O workspace provavelmente ainda está **não confiável**. Veja [Primeiro workspace](../first-workspace) — clique em "Confio nesta pasta" pra liberar escrita e terminal.

## Um cliente MCP externo (Claude Code, Claude Desktop) não conecta

Confirme que o Vectora está rodando e que a URL usada é `http://<seu-host>:<porta>/mcp` (não `/mcp/sse` — o servidor é montado direto em `/mcp` via SSE no mesmo processo). Em produção, use a URL HTTPS pública do seu servidor. Veja [Servidor MCP](../../reference/mcp-server).

## `vectora storage complete` não conecta no Postgres/Qdrant/Redis

O modo complete exige que os três serviços estejam acessíveis nos DSNs configurados (`POSTGRES_DSN`, `QDRANT_URL`, `REDIS_URL`). Se você não tem infraestrutura própria, rode `scons docker` (a partir da raiz do monorepo, se estiver rodando do código-fonte) ou use o wizard `vectora storage wizard` pra configurar um provedor gerenciado (Supabase, Neon, Qdrant Cloud). Veja [Storage: lite vs. complete](../../concepts/storage).

## Recursos Pro (chat multi-usuário, storage complete) não desbloqueiam mesmo com assinatura ativa

Confirme que o `VECTORA_TOKEN` do [dashboard](https://vectora.company/dashboard) está configurado e válido — o status de licença é cacheado localmente com TTL curto; force uma revalidação reiniciando o app ou verificando em **Configurações → Administração → Sistema**.

## Erro `command not found: vectora` (instalação a partir do código-fonte)

Rode com `uv run vectora ...` em vez de `vectora ...` direto — o `uv` gerencia o ambiente virtual e o entrypoint sem precisar instalar globalmente.

## Onde reportar um bug

[GitHub Issues](https://github.com/vectora-company/vectora/issues) (público) ou o formulário em [vectora.company/issues](https://vectora.company/issues).
