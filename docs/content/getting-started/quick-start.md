---
title: Início Rápido
weight: 3
---

Este guia leva do zero à primeira resposta do agente em poucos minutos.

## 1. Suba o Vectora

Depois de [instalado](../installation), abra o app (ou `uv run vectora start --port 8080` + `pnpm --dir frontend dev` em dev). O primeiro acesso pede cadastro — o primeiro usuário a se cadastrar vira **administrador root** da instância.

## 2. Configure um provedor de LLM

Abra **Configurações → Preferências → Geral** e escolha um provedor (Google Gemini, OpenAI, Anthropic, Cohere ou Ollama local). Sem chave de API configurada em nenhum provedor, o seletor de modelo do chat fica vazio.

Se você prefere configurar por variável de ambiente em vez da UI, edite `.env` (dev) ou `~/.vectora/.env` (instalação nativa):

```env
LLM_PROVIDER=google-genai
GOOGLE_API_KEY=sua_chave_aqui
COHERE_API_KEY=sua_chave_aqui   # obrigatório para RAG
```

## 3. Crie seu primeiro workspace

Um workspace é uma pasta do seu sistema de arquivos que o Vectora pode ler (e, se você confiar nela, editar e executar comandos). No chat, use o seletor de workspace no topo pra apontar para um diretório de projeto.

Na primeira vez que abrir uma pasta não confiável, o Vectora pede confirmação explícita ("Confio nesta pasta") antes de liberar escrita e terminal — veja [Primeiro workspace](../first-workspace).

## 4. Mande sua primeira mensagem

Experimente algo concreto, não genérico:

```text
Explique a arquitetura deste projeto olhando o package.json / pyproject.toml
```

```text
Rode os testes e me diga o que está falhando
```

O orchestrator decide sozinho se responde direto ou delega para o subagente `coder` (arquivos/git/terminal) ou `search` (busca web/RAG). Ações potencialmente destrutivas (escrever arquivo, rodar comando, `git push`) pausam pra sua aprovação — o chamado modo HITL (human-in-the-loop).

## 5. Indexe conhecimento pro RAG (opcional, mas recomendado)

Arraste uma pasta de documentação pro chat, ou use o painel **Memory (RAG)** na workbench pra indexar arquivos manualmente. Depois disso, perguntas sobre esse conteúdo vêm com citações `[1] [2]` rastreáveis até a fonte.

## Próximos passos

- [Usando o chat](../../guides/using-the-chat) — modos, seletor de modelo, permission modes
- [Usando a workbench](../../guides/using-the-workbench) — as 9 abas do painel lateral
- [Conceitos: RAG & Context Graph](../../concepts/rag) — como a recuperação de contexto funciona por baixo dos panos
