---
title: Using the Chat
weight: 1
---

## Enviando mensajes

El input del chat acepta texto, archivos arrastrados, imágenes pegadas del portapapeles y `@menciones` de archivos para traer contenido específico al contexto sin tener que describirlo.

## Selector de modelo

Solo muestra proveedores con una API key configurada — Google Gemini, OpenAI, Anthropic, Cohere, u Ollama local. Cambiar de modelo a mitad de conversación no pierde el historial.

## Modos de permiso

Controlan cuán automáticamente actúa el agente antes de pedir tu aprobación:

| Modo               | El agente...                                                                |
| -------------------- | ------------------------------------------------------------------------------ |
| **Siempre preguntar** | se pausa antes de cualquier acción destructiva (escribir un archivo, terminal, git push) |
| **Aceptar ediciones** | aplica ediciones de archivos directamente; terminal y git siguen pausando        |
| **Autónomo**          | no se pausa por nada — úsalo con un workspace en el que ya confías totalmente   |
| **Plan**              | solo planifica, nunca ejecuta una acción real                                   |

Ver [Orchestrator & Subagents](../../concepts/sub-agents) para entender el HITL detrás de esto.

## Pensamiento del orquestador

El bloque de "pensamiento" muestra la decisión del orquestador antes de actuar: responder directamente o delegar a `coder`/`search`, y por qué. Esto es transparencia real, no solo un spinner — puedes ver el razonamiento, no solo esperar el resultado.

## Memoria entre sesiones

Aparece una insignia "🧠 N memorias cargadas" cuando el agente usa memorias persistentes de conversaciones anteriores en esa respuesta. Gestiona las memorias manualmente en **Configuración → Preferencias → Memoria**.

## Citas de RAG

Las respuestas basadas en contenido indexado traen citas clicables `[1] [2]` — haz clic para ver el extracto original y la fuente.

## Multiusuario (Pro)

En modo Pro con chat web multiusuario, los hilos pueden compartirse entre miembros del mismo workspace, con RBAC controlando quién ve qué.

## Ver también

- [Usando el workbench](../using-the-workbench) — el panel lateral que acompaña al chat
- [Usando la configuración](../using-settings) — dónde viven el modelo por defecto, el idioma y el tema
