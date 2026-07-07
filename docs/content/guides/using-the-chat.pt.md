---
title: Usando o Chat
weight: 1
---

## Enviando mensagens

O input do chat aceita texto, arquivos arrastados (drag-and-drop), colar imagens do clipboard, e `@menções` de arquivo pra trazer conteúdo específico pro contexto sem precisar descrevê-lo.

## Seletor de modelo

Mostra só os providers com chave de API configurada — Google Gemini, OpenAI, Anthropic, Cohere, ou Ollama local. Trocar de modelo no meio de uma conversa não perde o histórico.

## Modos de permissão

Controlam o quão automático o agente age antes de pedir sua aprovação:

| Modo                 | O agente...                                                                    |
| -------------------- | ------------------------------------------------------------------------------ |
| **Perguntar sempre** | pausa antes de qualquer ação destrutiva (escrever arquivo, terminal, git push) |
| **Aceitar edições**  | aplica edições de arquivo direto; terminal e git ainda pausam                  |
| **Autônomo**         | não pausa pra nada — use com um workspace que você já confia plenamente        |
| **Plano**            | só planeja, nunca executa uma ação real                                        |

Veja [Orchestrator & Subagentes](../../concepts/sub-agents) pra entender o HITL por trás disso.

## Thinking / raciocínio do orchestrator

O bloco de "pensando" mostra a decisão do orchestrator antes de agir: responder direto ou delegar pra `coder`/`search`, e por quê. Isso é transparência de verdade, não só um spinner — dá pra ver o raciocínio, não só esperar o resultado.

## Memória entre sessões

Um badge "🧠 N memórias carregadas" aparece quando o agente usa memórias persistentes de conversas anteriores nessa resposta. Gerencie memórias manualmente em **Configurações → Preferências → Memória**.

## Citações RAG

Respostas baseadas em conteúdo indexado trazem citações `[1] [2]` clicáveis — clique pra ver o trecho original e a fonte.

## Multi-usuário (Pro)

No modo Pro com chat web multi-usuário, threads podem ser compartilhadas entre membros do mesmo workspace, com RBAC controlando quem vê o quê.

## Veja também

- [Usando a workbench](../using-the-workbench) — o painel lateral que acompanha o chat
- [Usando as configurações](../using-settings) — onde ficam modelo padrão, idioma, tema
