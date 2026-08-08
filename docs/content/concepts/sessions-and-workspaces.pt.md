---
title: Sessões e Workspaces
weight: 6
---

Dois eixos independentes moldam o comportamento de uma conversa: **modo Chat vs Dev** (o que o agente pode fazer) e **modo Assistente vs IDE** (como o workbench é organizado). Entender os dois deixa claro por que uma sessão às vezes tem um workspace e às vezes não, e por que trocar de modo abre uma conversa nova.

## Modo Chat vs modo Dev

- **Modo Chat** — uma sessão conversacional leve, sem acesso a filesystem, terminal ou git. O agente ainda tem busca web, RAG, memória e integrações externas (Slack, Linear, Notion, etc.), só não tem tools de workspace nem delegação de subagente. Não há nada a confiar aqui, então nenhum workspace é criado.
- **Modo Dev** — o agente completo: filesystem, terminal, git, navegador, Context Graph, Library, agendamento — tudo coberto em [Automação do agente](../../guides/agent-automation) e no restante desta doc. Uma sessão em modo Dev sempre tem um workspace.

Trocar entre os dois sempre inicia uma **thread nova e vazia** — sessões Chat e Dev são pools separados, não duas visões da mesma conversa. É uma fronteira deliberada, não uma limitação a contornar: o histórico de uma sessão Chat nunca ganha acesso a arquivo/terminal silenciosamente só por trocar de modo.

## O que é um workspace

Um workspace é uma pasta em disco que o backend recebeu permissão pra ler e escrever. Internamente, o `workspace_id` é derivado deterministicamente do caminho absoluto da pasta, e o registro (persistido localmente) rastreia o estado de confiança por pasta.

**Confiança** é o que restringe as tools destrutivas (`file_write`, `terminal`, operações git): um workspace precisa ser explicitamente confiado antes do agente poder tocá-lo.

- A pasta de onde o backend foi **iniciado** já vem confiada automaticamente — se você já tem um shell ali, você já tem controle total, então pedir confirmação seria teatro.
- Qualquer outra pasta adicionada depois (via o seletor de workspace) exige um diálogo explícito de confirmação de confiança antes do agente ganhar acesso de escrita.

Quando você inicia uma sessão em modo Dev sem escolher uma pasta existente, o Vectora cria um workspace dedicado e já confiado pra essa thread, dentro da sua pasta de Documentos — materializado em disco só quando o agente realmente precisa escrever algo, não de forma antecipada no início da sessão.

## Modo Assistente vs modo IDE

Independente de Chat/Dev, o próprio workbench tem dois layouts, alternados a partir do header (só visível dentro de uma sessão ativa em modo Dev):

- **Modo Assistente** — o chat é a superfície principal; o workbench (arquivos, terminal, diff, etc.) abre como um painel lateral.
- **Modo IDE** — um layout de editor de código com múltiplas abas ancoradas toma a área principal, com o chat ao lado — mais próximo de uma janela de IDE tradicional.

Essa alternância só afeta o layout, não a capacidade: as mesmas tools e o mesmo workspace estão disponíveis nos dois.

## Veja também

- [Sandbox](../sandbox) — como o acesso a terminal/arquivo de um workspace pode ser isolado
- [Usando o Workbench](../../guides/using-the-workbench) — as abas disponíveis numa sessão em modo Dev
- [Automação do agente](../../guides/agent-automation) — Delegate, Schedule, Remember, Connect
