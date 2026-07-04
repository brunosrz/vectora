---
title: Hybrid RAG
weight: 1
---

RAG (Retrieval-Augmented Generation) is the mechanism by which Vectora answers based on what was **indexed**, not on what the model "thinks" is true. It's a central pillar of the architecture, not a secondary feature — there's a dedicated subagent (`search`) and a set of tools (`vector_search`, `embedding`, `ingest_docs`, `manage_retriever`) built around it.

## Pipeline

```text
user query
      │
      ▼
 query expansion (LLM multi-query)
      │
      ▼
 hybrid search:  BM25 (sparse/lexical)  +  dense vector search (LanceDB/Qdrant)
      │
      ▼
 score gate
      │
   ┌──┴──────────────┬─────────────────────┐
   │ score ≥ 0.7      │ 0.4 ≤ score < 0.7   │ score < 0.4
   ▼                  ▼                     ▼
 inject directly   rerank (Cohere/         falls back to web search (Tavily),
 into context       VoyageAI) → inject      result curated before indexing
```

- **Hybrid retrieval** combines BM25 (good for exact terms, function names, identifiers) with dense vector search (good for semantic similarity) — neither alone covers both cases well.
- **Reranking** (Cohere `rerank-multilingual-v3.0` or VoyageAI) reorders candidates by actual relevance before they enter context, preventing semantic noise from surfacing the wrong results.
- **Web search fallback**: when the local retrieval score is low, Vectora doesn't force a bad answer — it searches the web (Tavily) and **curates** the result (reranker + LLM judge) before ever considering indexing it, so your knowledge base never gets contaminated with junk.

## Embeddings

Cohere `embed-multilingual-v3.0` (1024 dimensions) is the default embedder — covers multiple languages in the same vector store. VoyageAI is the configurable alternative.

## Citations

Every RAG-based answer cites sources (`[1] [2]`), traceable back to the original chunk and source file/URL — that's what separates "the agent answered" from "the agent answered based on something verifiable".

## Indexing

- Drag a folder into the chat, or use `/rag add`.
- The **Memory (RAG)** tab in the workbench shows what's already indexed, lets you configure reranker on/off, top_k, embedding/rerank provider, and manage collections.
- Indexing runs on an async queue (`embedding_queue.db`) — it doesn't block chat while processing.

## See also

- [Context Graph](../context-graph) — structural context that complements RAG
- [Using the workbench](../../guides/using-the-workbench) — the Memory (RAG) panel in practice
