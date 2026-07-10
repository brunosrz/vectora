---
title: First Workspace
weight: 5
---

Un **workspace** es una carpeta en tu sistema de archivos registrada en Vectora. Es la unidad alrededor de la cual el agente organiza el contexto: RAG, Context Graph, git, terminal y el editor de archivos operan todos dentro del workspace activo.

## Agregar un workspace

En el selector de workspace (parte superior del chat), elige "Agregar workspace" y apunta a una carpeta local. No hay límite de workspaces registrados — cambia entre ellos en cualquier momento sin perder el historial de conversación.

## Confiar en una carpeta

Por defecto, un workspace recién agregado es **no confiable**: el agente puede leer archivos, pero **no puede** escribir, ejecutar comandos de terminal ni ejecutar git. Esto existe para evitar que el agente ejecute comandos arbitrarios en una carpeta que solo querías explorar.

Haz clic en "Confiar en esta carpeta" para desbloquear:

- Escritura de archivos (`file_write`, `file_edit`)
- Terminal (PTY real)
- Operaciones de git que cambian estado (commit, push, checkout)

La confianza es por carpeta, no global — abrir una carpeta nueva siempre empieza sin confianza.

## Carpetas seguras (admin)

Los administradores pueden configurar una lista de **carpetas seguras** en **Configuración → Administración → Carpetas Seguras** — rutas que requieren aprobación extra incluso después de ser confiables, útil para proteger directorios sensibles en un servidor compartido.

## Git

Si la carpeta ya es un repositorio git, Vectora lo detecta automáticamente y habilita la pestaña **Diff (Git)** en el workbench. Si no, puedes pedirle al agente que ejecute `git init`, o hacerlo tú mismo antes de confiar en la carpeta.

## `.vectoraignore`

Un archivo `.vectoraignore` en la raíz del workspace (misma sintaxis que `.gitignore`) oculta rutas de todo Vectora — RAG, Context Graph, sistema de archivos y chat. Úsalo para excluir `node_modules/`, salidas de build, secretos, etc.

## Siguiente paso

→ [Usando el chat](../../guides/using-the-chat)
