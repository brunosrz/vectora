---
title: MCP Client
weight: 5
---

Vectora se conecta a servidores MCP de terceros como cliente — no se expone a sí mismo como servidor MCP para otros harnesses. Configura conectores en **Configuración → Entorno → Plugins**, con soporte para transportes `stdio`, `sse` y `http`.

## Instalando un conector

La tab **Library** del workbench lista un marketplace de conectores MCP con curación — instala/desinstala directamente ahí, o registra un servidor MCP personalizado manualmente en **Configuración → Entorno → Plugins**.

## Cómo lo usa el agente

Una vez instalado el conector, el agente puede descubrir y llamar a sus herramientas directamente en la conversación — sujeto al mismo modo de permisos y confirmaciones que protegen cualquier otra acción del chat.

Ver [Usando la configuración](../../guides/using-settings) para detalles de configuración por workspace.
