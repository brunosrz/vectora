---
title: Security
weight: 3
---

**¿Mis datos salen de mi servidor?**
No hacia el backend de Vectora Company. Solo salen hacia las APIs que tú mismo configuraste (LLM, Cohere/Voyage, Tavily) y hacia servidores MCP que instalaste.

**¿Vectora tiene cifrado de extremo a extremo?**
No en el sentido clásico de SaaS — ver [BYOK y Privacidad](../../security/byok-privacy) para el modelo de amenazas completo. Las contraseñas son Argon2id, los secretos viven en una bóveda AES-256, pero el contenido de las conversaciones queda en texto plano en tu propio servidor (que tú operas).

**¿Cómo maneja Vectora la inyección de prompts?**
El contenido que viene de herramientas (archivos leídos, páginas web, resultados de llamadas a funciones) **no** lleva la autoridad de un mensaje directo del usuario. Cuando ese contenido contiene una instrucción de alto impacto (borrar, exfiltrar, ejecutar un script), el agente se detiene y pregunta antes de actuar.

**¿Puedo restringir lo que el agente puede hacer?**
Sí — modos de permiso (siempre preguntar / aceptar ediciones / autónomo / plan), política de herramientas por servidor MCP, interruptores globales de herramientas para admins, y el mecanismo de carpeta confiable por workspace.

**¿Dónde reporto una vulnerabilidad?**
`security@vectora.company`, con divulgación responsable.
