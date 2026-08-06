---
title: MCP Client
weight: 5
---

O Vectora se conecta a servidores MCP de terceiros como cliente — não expõe a si mesmo como servidor MCP para outros harnesses. Configure conectores em **Configurações → Ambiente → Plugins**, com suporte a transporte `stdio`, `sse` e `http`.

## Instalando um conector

A tab **Library** do workbench lista um marketplace de conectores MCP com curadoria — instale/desinstale direto por ali, ou registre um servidor MCP customizado manualmente em **Configurações → Ambiente → Plugins**.

## Como o agente usa

Depois de instalado o conector, o agente pode descobrir e chamar as tools dele direto na conversa — sujeito ao mesmo modo de permissão e confirmações que protegem qualquer outra ação do chat.

Veja [Usando as configurações](../../guides/using-settings) pra detalhes de configuração por workspace.
