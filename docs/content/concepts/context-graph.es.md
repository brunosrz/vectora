---
title: Context Graph
weight: 2
---

El Context Graph es un **grafo de conocimiento nativo del workspace** — complementa el RAG con contexto estructural que los embeddings solos no pueden capturar (quién llama a quién, qué depende de qué, qué conceptos se relacionan entre sí).

## Cómo se construye

1. **Parsing AST** vía [tree-sitter](https://tree-sitter.github.io/), con gramáticas para Python, JavaScript, TypeScript, Go, Rust, Java, C, C++ y JSON.
2. **Extracción semántica** por LLM sobre el resultado del parsing — identifica conceptos, relaciones y la importancia relativa de los nodos.
3. **Detección de comunidades y "god nodes"** — archivos/símbolos excesivamente acoplados, que tienden a ser puntos de riesgo durante refactors.
4. **Preguntas sugeridas** — el grafo sugiere qué vale la pena preguntar sobre el workspace, basado en su topología.

## Modos de indexación

Configurables en la pestaña **Context Graph** del workbench:

- **Por tipo de archivo** — código, documentos, papers — eliges qué entra en el grafo (ej.: solo markdown, dejando el código al RAG puro).
- **Semántico vs. AST** — AST es más rápido y estructural; el semántico se apoya más en el LLM para capturar relaciones que la sintaxis sola no muestra.

## Build pausable

Construir el grafo para un workspace grande consume llamadas al LLM. El build es **pausable y reanudable** por cuota — si alcanzas un límite de tasa/costo a mitad del proceso, continúa donde se quedó en lugar de empezar de nuevo.

## Dónde viven los artefactos

`.vectora/context-graph/` dentro del propio workspace — los mismos archivos que `.vectoraignore` oculta del resto de Vectora también quedan fuera del grafo.

## Etapas visuales (workbench)

Mientras el grafo se construye, cada archivo muestra un indicador de etapa:

| Etapa     | Color (oscuro / claro)                | Significa                       |
| --------- | -------------------------------------- | -------------------------------- |
| AST       | azul claro `#4a9eff` / azul `#1f6feb` | parsing estructural en progreso  |
| Semántico | morado `#b66dff` / morado `#8957e5`   | extracción por LLM en progreso   |
| Listo     | verde `#5ec26a` / verde `#2da44e`     | archivo procesado                |

## Ver también

- [RAG híbrido](../rag) — recuperación por similitud, complementaria al grafo
- [Usando el workbench](../../guides/using-the-workbench) — la pestaña Context Graph en detalle
