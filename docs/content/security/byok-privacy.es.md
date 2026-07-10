---
title: BYOK & Privacy
weight: 4
---

## Qué garantiza realmente "autoalojado"

Tus datos nunca pasan por un servidor intermediario de Vectora Company. El agente se conecta **directamente** a las APIs que configuraste (Gemini, OpenAI, Anthropic, Cohere, Tavily) y a los servidores MCP que instalaste. Vectora Company nunca ve el contenido de tus conversaciones, tu código, ni tus archivos.

## Qué esto no significa

Autoalojado **no es** cifrado de extremo a extremo en el sentido clásico de SaaS. El servidor que ejecuta Vectora (tu servidor) necesita ver el contenido en claro para llamar al LLM e indexarlo para RAG — hoy no hay forma de procesar contenido cifrado homomórficamente con LLMs. Si accedes a tu propio Vectora en un VPS desde casa, los datos están protegidos por TLS en tránsito, hash de contraseñas fuerte, JWTs firmados, una bóveda AES-256 para secretos — pero **no** hay cifrado tal que tú mismo (el operador del VPS) no puedas leer tus propias conversaciones. Ese no es el modelo de amenazas.

## BYOK (Trae tu propia key)

Free y Pro funcionan con tus propias API keys — LLM, Cohere/VoyageAI (embeddings), Tavily (búsqueda web). Vectora nunca ve ni almacena esas keys en texto plano (viven en la [bóveda](../secrets-vault)); la llamada a la API ocurre directamente desde tu servidor al proveedor elegido.

## LGPD/GDPR

La responsabilidad por el manejo de los datos enviados a los proveedores de LLM/embeddings es entre **tú** (el operador) y **cada proveedor conectado** — Vectora no es parte de esa relación de datos. Los Términos de Uso de Vectora Company describen exactamente qué viaja por cada integración.

## Auditoría

Los clientes Pro+ reciben el binario compilado y documentación completa de arquitectura. La auditoría de código fuente bajo NDA está disponible para clientes Enterprise.
