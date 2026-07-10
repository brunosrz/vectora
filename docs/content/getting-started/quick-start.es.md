---
title: Quick Start
weight: 3
---

Esta guía te lleva de cero a la primera respuesta del agente en unos minutos.

## 1. Inicia Vectora

Después de [instalar](../installation), abre la app (o `uv run vectora start --port 8080` + `pnpm --dir frontend dev` en modo dev). La primera visita te pide registrarte — el primer usuario en registrarse se convierte en el **administrador root** de la instancia.

## 2. Configura un proveedor de LLM

Abre **Configuración → Preferencias → General** y elige un proveedor (Google Gemini, OpenAI, Anthropic, Cohere, u Ollama local). Sin una API key configurada para ningún proveedor, el selector de modelos del chat queda vacío.

Si prefieres configurar vía variable de entorno en lugar de la UI, edita `.env` (dev) o `~/.vectora/.env` (instalación nativa):

```env
LLM_PROVIDER=google-genai
GOOGLE_API_KEY=tu_clave_aqui
COHERE_API_KEY=tu_clave_aqui   # requerida para RAG
```

## 3. Crea tu primer workspace

Un workspace es una carpeta en tu sistema de archivos que Vectora puede leer (y, si confías en ella, editar y ejecutar comandos). En el chat, usa el selector de workspace en la parte superior para apuntar a un directorio de proyecto.

La primera vez que abres una carpeta no confiable, Vectora pide confirmación explícita ("Confiar en esta carpeta") antes de desbloquear el acceso de escritura y la terminal — ver [Primer workspace](../first-workspace).

## 4. Envía tu primer mensaje

Prueba algo concreto, no genérico:

```text
Explica la arquitectura de este proyecto leyendo package.json / pyproject.toml
```

```text
Ejecuta los tests y dime qué está fallando
```

El orquestador decide por su cuenta si responde directamente o delega al sub-agente `coder` (archivos/git/terminal) o `search` (búsqueda web/RAG). Las acciones potencialmente destructivas (escribir un archivo, ejecutar un comando, `git push`) se pausan para tu aprobación — el modo HITL (human-in-the-loop).

## 5. Indexa conocimiento para RAG (opcional, pero recomendado)

Arrastra una carpeta de documentación al chat, o usa el panel **Memoria (RAG)** del workbench para indexar archivos manualmente. Después de eso, las preguntas sobre ese contenido vuelven con citas `[1] [2]` rastreables hasta la fuente.

## Siguientes pasos

- [Usando el chat](../../guides/using-the-chat) — modos, selector de modelos, modos de permiso
- [Usando el workbench](../../guides/using-the-workbench) — las 9 pestañas del workbench
- [Conceptos: RAG y Context Graph](../../concepts/rag) — cómo funciona la recuperación de contexto por debajo
