---
title: Installation
weight: 2
---

Vectora se distribuye como una **app de escritorio nativa** (Electron + un backend Python compilado) para Windows, macOS y Linux, con auto-actualización integrada. No existe una "imagen Docker única" del producto — Docker, cuando se usa, solo levanta infraestructura opcional (Postgres/Redis/Qdrant para el modo completo), nunca Vectora en sí.

## Opción 1 — Instalador nativo (recomendado)

Descarga el instalador para tu sistema operativo:

| SO      | Formato                                  | Firma                                  |
| ------- | ----------------------------------------- | --------------------------------------- |
| Windows | `.msi` o `.exe` (NSIS)                    | Certificado EV (Azure Trusted Signing)  |
| macOS   | `.dmg` (solo Apple Silicon)               | Apple Developer ID + notarizado         |
| Linux   | `.AppImage`, `.deb` o `.rpm`              | sin firmar                              |

Instala normalmente (doble clic / `dpkg -i` / `rpm -i`). La app se abre con el backend ya embebido — no hay que instalar Python, Node ni ninguna otra dependencia por separado.

Las futuras actualizaciones llegan automáticamente vía auto-actualización (servida por `updates.vectora.company`).

## Opción 2 — Desde el código fuente (dev)

Para contribuir o ejecutar en modo desarrollo:

**Requisitos**: Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js 24+, `pnpm`.

```bash
git clone https://github.com/vectora-company/vectora.git
cd vectora/vectora

uv sync                          # dependencias de Python
pnpm --dir frontend install       # dependencias del frontend

cp .env.example .env
# edita .env: GOOGLE_API_KEY (u otro proveedor), COHERE_API_KEY, TAVILY_API_KEY
```

Dos ventanas de terminal:

```bash
# Terminal 1 — backend completo + SPA (puerto 8080)
uv run vectora start --port 8080

# Terminal 2 — servidor dev del frontend (Vite, puerto 3000, hace proxy a la API)
pnpm --dir frontend dev
```

Abre `http://localhost:3000`. El primer usuario en registrarse se convierte en el administrador root.

## API keys requeridas

| Key                                                                     | ¿Requerida?   | Para                                        |
| ------------------------------------------------------------------------ | ------------- | -------------------------------------------- |
| Un proveedor de LLM (Gemini, OpenAI, Anthropic, Cohere, u Ollama local) | Sí            | Chat, generación de código, síntesis de respuestas |
| `COHERE_API_KEY` (o VoyageAI)                                           | Sí, para RAG  | Embeddings + reranking                       |
| `TAVILY_API_KEY`                                                        | Opcional      | Búsqueda web                                 |

El selector de modelos en el chat solo muestra proveedores con una key configurada — sin key, no hay proveedor en la lista.

## Licencia

La app funciona **sin licencia** en modo Free (100% local). Para desbloquear las funciones Pro (chat web multiusuario, almacenamiento completo, automatizaciones disparadas por webhook), necesitas un `VECTORA_TOKEN`, obtenido en el [dashboard](https://vectora.company/dashboard) tras suscribirte a un plan de pago.

## Siguiente paso

→ [Inicio rápido](../quick-start)
