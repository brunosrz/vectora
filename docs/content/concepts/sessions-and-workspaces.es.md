---
title: Sesiones y Espacios de Trabajo
weight: 6
---

Dos ejes independientes moldean el comportamiento de una conversación: **modo Chat vs Dev** (qué puede hacer el agente) y **modo Asistente vs IDE** (cómo se organiza el workbench). Entender ambos deja claro por qué una sesión a veces tiene un espacio de trabajo y a veces no, y por qué cambiar de modo abre una conversación nueva.

## Modo Chat vs modo Dev

- **Modo Chat** — una sesión conversacional ligera, sin acceso a filesystem, terminal o git. El agente todavía tiene búsqueda web, RAG, memoria e integraciones externas (Slack, Linear, Notion, etc.), solo que sin herramientas de espacio de trabajo ni delegación de subagentes. No hay nada que confiar aquí, así que no se crea ningún espacio de trabajo.
- **Modo Dev** — el agente completo: filesystem, terminal, git, navegador, Context Graph, Library, programación — todo lo cubierto en [Automatización del agente](../../guides/agent-automation) y en el resto de esta doc. Una sesión en modo Dev siempre tiene un espacio de trabajo.

Cambiar entre los dos siempre inicia un **hilo nuevo y vacío** — las sesiones Chat y Dev son pools separados, no dos vistas de la misma conversación. Es un límite deliberado, no una limitación a evitar: el historial de una sesión Chat nunca gana acceso a archivo/terminal silenciosamente solo por cambiar de modo.

## Qué es un espacio de trabajo

Un espacio de trabajo es una carpeta en disco a la que el backend recibió permiso de lectura y escritura. Internamente, el `workspace_id` se deriva de forma determinista de la ruta absoluta de la carpeta, y el registro (persistido localmente) rastrea el estado de confianza por carpeta.

**La confianza** es lo que restringe las herramientas destructivas (`file_write`, `terminal`, operaciones git): un espacio de trabajo debe ser confiado explícitamente antes de que el agente pueda tocarlo.

- La carpeta desde donde se **inició** el backend ya viene confiada automáticamente — si ya tienes una shell ahí, ya tienes control total, así que pedir confirmación sería teatro.
- Cualquier otra carpeta agregada después (vía el selector de espacio de trabajo) requiere un diálogo explícito de confirmación de confianza antes de que el agente obtenga acceso de escritura.

Cuando inicias una sesión en modo Dev sin elegir una carpeta existente, Vectora crea un espacio de trabajo dedicado y ya confiado para ese hilo, dentro de tu carpeta de Documentos — materializado en disco solo cuando el agente realmente necesita escribir algo, no de forma anticipada al inicio de la sesión.

## Modo Asistente vs modo IDE

Independiente de Chat/Dev, el propio workbench tiene dos layouts, alternados desde el header (solo visible dentro de una sesión activa en modo Dev):

- **Modo Asistente** — el chat es la superficie principal; el workbench (archivos, terminal, diff, etc.) se abre como un panel lateral.
- **Modo IDE** — un layout de editor de código con múltiples pestañas ancladas toma el área principal, con el chat al lado — más cercano a una ventana de IDE tradicional.

Esta alternancia solo afecta el layout, no la capacidad: las mismas herramientas y el mismo espacio de trabajo están disponibles en ambos.

## Ver también

- [Sandbox](../sandbox) — cómo se puede aislar el acceso a terminal/archivo de un espacio de trabajo
- [Usando el Workbench](../../guides/using-the-workbench) — las pestañas disponibles en una sesión en modo Dev
- [Automatización del agente](../../guides/agent-automation) — Delegate, Schedule, Remember, Connect
