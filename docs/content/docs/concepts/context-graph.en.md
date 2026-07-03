---
title: Context Graph
weight: 2
---

The Context Graph is a **native workspace knowledge graph** — it complements RAG with structural context that embeddings alone can't capture (who calls whom, what depends on what, which concepts relate to each other).

## How it's built

1. **AST parsing** via [tree-sitter](https://tree-sitter.github.io/), with grammars for Python, JavaScript, TypeScript, Go, Rust, Java, C, C++, and JSON.
2. **Semantic extraction** by LLM on top of the parsing result — identifies concepts, relationships, and the relative importance of nodes.
3. **Community and "god node" detection** — excessively coupled files/symbols, which tend to be risk points during refactors.
4. **Suggested questions** — the graph suggests what's worth asking about the workspace, based on its topology.

## Indexing modes

Configurable in the workbench's **Context Graph** tab:

- **By file type** — code, documents, papers — you choose what enters the graph (e.g., markdown only, leaving code to pure RAG).
- **Semantic vs. AST** — AST is faster and structural; semantic leans more on the LLM to capture relationships syntax alone doesn't show.

## Pausable build

Building the graph for a large workspace consumes LLM calls. The build is **pausable and resumable** by quota — if you hit a rate/cost limit mid-process, it picks up where it left off instead of starting over.

## Where artifacts live

`.vectora/context-graph/` inside the workspace itself — the same files `.vectoraignore` hides from the rest of Vectora also stay out of the graph.

## Visual stages (workbench)

While the graph builds, each file shows a stage indicator:

| Stage    | Color (dark / light)                  | Means                          |
| -------- | ------------------------------------- | ------------------------------ |
| AST      | light blue `#4a9eff` / blue `#1f6feb` | structural parsing in progress |
| Semantic | purple `#b66dff` / purple `#8957e5`   | LLM extraction in progress     |
| Done     | green `#5ec26a` / green `#2da44e`     | file processed                 |

## See also

- [Hybrid RAG](../rag) — similarity retrieval, complementary to the graph
- [Using the workbench](../../guides/using-the-workbench) — the Context Graph tab in detail
