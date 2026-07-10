---
title: RBAC & Permissions
weight: 2
---

## Roles

| Rol      | Descripción                                                                          |
| -------- | --------------------------------------------------------------------------------------- |
| `root`   | el primer usuario registrado en la instancia; acceso total, incluida Administración     |
| `admin`  | gestiona usuarios, herramientas globales, carpetas seguras y configuración del servidor |
| `member` | uso normal del chat, workspaces y el workbench                                          |
| `viewer` | acceso de solo lectura                                                                   |

Gestionado en **Configuración → Administración → Usuarios**, con invitaciones por email/enlace y un TTL configurable (1–720h).

## Política de herramientas (ABAC)

Más allá del rol, cada herramienta puede habilitarse/deshabilitarse globalmente (**Configuración → Administración → Herramientas**) o por servidor MCP individual (**Configuración → Entorno → Plugins → Política de Herramientas**) — control de acceso basado en atributos, no solo en roles.

## Carpeta confiable

Independiente del RBAC, cada **workspace** tiene su propio estado de confianza — un `member` con acceso normal aún necesita confiar explícitamente en una carpeta antes de que el agente pueda escribir en ella o ejecutar comandos. Ver [Primer workspace](../../getting-started/first-workspace).

## Carpetas seguras

Los administradores pueden marcar rutas específicas como **carpetas seguras**, requiriendo aprobación extra incluso después de ser confiables — útil en servidores compartidos donde no todo `member` debería tener acceso irrestricto a ciertos directorios.

## Ver también

- [Authentication](../authentication)
- [Usando la configuración](../../guides/using-settings) — la pestaña Administración en detalle
