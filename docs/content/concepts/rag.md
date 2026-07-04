---
title: RAG Híbrido
weight: 1
---

RAG (Retrieval-Augmented Generation) é o mecanismo pelo qual o Vectora responde com base no que foi **indexado**, não no que o modelo "acha" que é verdade. É um pilar central da arquitetura, não uma feature secundária — existe um subagente (`search`) e um conjunto de tools (`vector_search`, `embedding`, `ingest_docs`, `manage_retriever`) dedicados a isso.

## Pipeline

```text
query do usuário
      │
      ▼
 expansão de query (multi-query via LLM)
      │
      ▼
 busca híbrida:  BM25 (esparsa/lexical)  +  busca vetorial densa (LanceDB/Qdrant)
      │
      ▼
 score gate
      │
   ┌──┴──────────────┬─────────────────────┐
   │ score ≥ 0.7      │ 0.4 ≤ score < 0.7   │ score < 0.4
   ▼                  ▼                     ▼
 injeta direto    rerank (Cohere/         cai pra busca web (Tavily),
 no contexto       VoyageAI) → injeta      resultado curado antes de indexar
```

- **Retrieval híbrido** combina BM25 (bom pra termos exatos, nomes de função, identificadores) com busca vetorial densa (boa pra similaridade semântica) — nenhum dos dois sozinho cobre os dois casos bem.
- **Reranking** (Cohere `rerank-multilingual-v3.0` ou VoyageAI) reordena os candidatos por relevância real antes de entrar no contexto, evitando que ruído semântico solte resultados errados na frente.
- **Fallback pra busca web**: quando o score de recuperação local é baixo, o Vectora não força uma resposta ruim — ele busca na web (Tavily) e **cura** o resultado (reranker + LLM judge) antes de considerar indexar, pra nunca contaminar sua base de conhecimento com lixo.

## Embeddings

Cohere `embed-multilingual-v3.0` (1024 dimensões) é o embedder padrão — cobre múltiplos idiomas na mesma base vetorial. VoyageAI é a alternativa configurável.

## Citações

Toda resposta baseada em RAG cita as fontes (`[1] [2]`), rastreáveis até o chunk original e o arquivo/URL de origem — isso é o que separa "o agente respondeu" de "o agente respondeu com base em algo verificável".

## Indexação

- Arraste uma pasta pro chat, ou use `/rag add`.
- A aba **Memory (RAG)** na workbench mostra o que já foi indexado, deixa configurar reranker on/off, top_k, provider de embedding/rerank, e gerenciar coleções.
- A indexação roda em fila assíncrona (`embedding_queue.db`) — não bloqueia o chat enquanto processa.

## Veja também

- [Context Graph](../context-graph) — contexto estrutural que complementa o RAG
- [Usando a workbench](../../guides/using-the-workbench) — painel Memory (RAG) na prática
