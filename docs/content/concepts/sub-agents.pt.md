---
title: Orchestrator & Subagentes
weight: 3
---

O agente do Vectora é construído sobre `create_deep_agent` (LangGraph + [deepagents](https://github.com/langchain-ai/deepagents)) — não um orchestrator manual por nós. Isso dá acesso a middleware nativo (HITL configurável), backends de filesystem plugáveis, e um supervisor que delega pra subagentes especializados via uma tool `task` interna.

## Orchestrator

O supervisor decide, a cada turno: responde direto (perguntas simples, conversas gerais) ou delega pra um subagente com uma instrução explícita. Não há hop de roteamento desnecessário — se a pergunta não precisa de arquivo, terminal ou busca, o orchestrator responde na hora.

## Os dois subagentes

| Subagente  | Especialidade                                           | Tools principais                                                                     |
| ---------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **coder**  | Filesystem, terminal, git — geração e revisão de código | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`, tools de git |
| **search** | Busca web em tempo real + RAG                           | `web_search`, `web_fetch`, `vector_search`, `embedding`, `ingest_docs`               |

Não existe um terceiro subagente dedicado a RAG — a recuperação de contexto é uma responsabilidade do `search`, não um subagente separado.

## HITL (Human-in-the-Loop)

Antes de qualquer ação destrutiva (escrever arquivo, rodar comando no terminal, `git push`), o grafo **pausa** e pede sua aprovação — via `HumanInTheLoopMiddleware` nativo do harness, não um `interrupt()` cru. O comportamento muda pelo **modo de permissão** ativo:

| Modo             | Comportamento                                               |
| ---------------- | ----------------------------------------------------------- |
| Perguntar sempre | toda ação destrutiva pausa                                  |
| Aceitar edições  | edições de arquivo passam direto; terminal/git ainda pausam |
| Autônomo         | nada pausa (uso avançado/confiável)                         |
| Plano            | o agente só planeja, nunca executa                          |

## Por que isso importa na prática

Você não precisa confiar cegamente no agente: toda tool call é rastreável, toda ação de risco passa por você antes de acontecer, e a decisão de "responder direto vs. delegar" é visível na UI (o bloco de "thinking" do chat mostra o raciocínio do orchestrator).

## Veja também

- [Usando o chat](../../guides/using-the-chat) — modos de permissão na prática
- [Referência de Agents](../../reference/agents) — specs completas dos subagentes
