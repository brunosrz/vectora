---
title: Hybrid RAG
weight: 1
---

RAG (Retrieval-Augmented Generation) es el mecanismo por el cual Vectora responde según lo que fue **indexado**, no según lo que el modelo "cree" que es cierto. Es un pilar central de la arquitectura, no una función secundaria — hay un sub-agente dedicado (`search`) y un conjunto de herramientas (`vector_search`, `embedding`, `ingest_docs`, `manage_retriever`) construidas alrededor de él.

## Pipeline

```text
consulta del usuario
      │
      ▼
 expansión de consulta (multi-query por LLM)
      │
      ▼
 búsqueda híbrida:  BM25 (sparse/léxica)  +  búsqueda vectorial densa (LanceDB/Qdrant)
      │
      ▼
 puerta de score
      │
   ┌──┴──────────────┬─────────────────────┐
   │ score ≥ 0.7      │ 0.4 ≤ score < 0.7   │ score < 0.4
   ▼                  ▼                     ▼
 inyecta            reranking (Cohere/     recae en búsqueda web (Tavily),
 directo al          VoyageAI) → inyecta    resultado curado antes de indexar
 contexto
```

- La **recuperación híbrida** combina BM25 (bueno para términos exactos, nombres de funciones, identificadores) con búsqueda vectorial densa (buena para similitud semántica) — ninguno de los dos por sí solo cubre bien ambos casos.
- El **reranking** (Cohere `rerank-multilingual-v3.0` o VoyageAI) reordena los candidatos por relevancia real antes de que entren al contexto, evitando que el ruido semántico haga surgir resultados equivocados.
- **Fallback a búsqueda web**: cuando el score de recuperación local es bajo, Vectora no fuerza una mala respuesta — busca en la web (Tavily) y **cura** el resultado (reranker + juez LLM) antes de siquiera considerar indexarlo, de modo que tu base de conocimiento nunca se contamina con basura.

## Embeddings

Cohere `embed-multilingual-v3.0` (1024 dimensiones) es el embedder por defecto — cubre múltiples idiomas en el mismo vector store. VoyageAI es la alternativa configurable.

## Citas

Toda respuesta basada en RAG cita fuentes (`[1] [2]`), rastreables hasta el chunk original y el archivo/URL fuente — eso es lo que separa "el agente respondió" de "el agente respondió basado en algo verificable".

## Indexación

- Arrastra una carpeta al chat, o usa `/rag add`.
- La pestaña **Memoria (RAG)** del workbench muestra qué ya está indexado, te deja configurar reranker activado/desactivado, top_k, proveedor de embedding/rerank y gestionar colecciones.
- La indexación se ejecuta en una cola asíncrona (`embedding_queue.db`) — no bloquea el chat mientras procesa.

## Ver también

- [Context Graph](../context-graph) — contexto estructural que complementa el RAG
- [Usando el workbench](../../guides/using-the-workbench) — el panel Memoria (RAG) en la práctica
