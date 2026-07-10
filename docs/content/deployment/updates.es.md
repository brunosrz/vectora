---
title: Updates
weight: 5
---

## Cómo funciona hoy

La app de escritorio usa `electron-updater`, verificando nuevas versiones contra el worker `services.vectora.company` (`GET /updates/:channel/:os/:arch/latest.yml`). Descargar e instalar la actualización ocurre automáticamente en segundo plano.

## Cuarentena de versiones

Si una versión nueva muestra una tasa de crashes por encima de un umbral en una ventana corta (vía telemetría de actualización), el worker mueve esa versión a una lista de cuarentena y empieza a servir `previous_stable` de nuevo para las nuevas verificaciones — esto no deshace instalaciones ya hechas, pero contiene el radio de impacto para quien todavía no actualizó.

## Canal de actualización

Los binarios y el manifiesto (`latest.yml`, el estándar de `electron-updater`) viven en R2, servidos por las rutas `/updates/*` y `/download/*` del worker — el mismo worker que cubre auth/facturación/licencia de la empresa.

## Roadmap: changelog + aprobación manual + rollback

Un flujo más explícito (ver el changelog antes de descargar, aprobar manualmente la instalación, backup automático antes de aplicar, rollback real a una versión anterior) está diseñado pero **aún no implementado** — el comportamiento actual es auto-actualización sin changelog visible y sin aprobación manual. Esto es roadmap, no una función disponible hoy.

## Cuando desarrollas desde el código fuente

Ejecutando vía `uv run vectora start`, no hay auto-actualización — actualizas con `git pull` + `uv sync` como de costumbre.
