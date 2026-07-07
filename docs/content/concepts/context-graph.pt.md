---
title: Context Graph
weight: 2
---

O Context Graph é um **grafo de conhecimento nativo do workspace** — complementa o RAG com contexto estrutural que embeddings sozinhos não capturam (quem chama quem, o que depende do quê, quais conceitos se relacionam).

## Como é construído

1. **Parsing AST** via [tree-sitter](https://tree-sitter.github.io/), com gramáticas para Python, JavaScript, TypeScript, Go, Rust, Java, C, C++ e JSON.
2. **Extração semântica** por LLM sobre o resultado do parsing — identifica conceitos, relações e importância relativa dos nós.
3. **Detecção de comunidades e "god nodes"** — arquivos/símbolos excessivamente acoplados, que costumam ser pontos de risco em refactors.
4. **Perguntas sugeridas** — o grafo sugere o que vale a pena perguntar sobre o workspace, com base na sua topologia.

## Modos de indexação

Configurável na aba **Context Graph** da workbench:

- **Por tipo de arquivo** — código, documentos, papers — você escolhe o que entra no grafo (ex: só markdown, deixando código pro RAG puro).
- **Semântico vs. AST** — AST é mais rápido e estrutural; semântico usa mais o LLM pra capturar relações que a sintaxe sozinha não mostra.

## Build pausável

Construir o grafo de um workspace grande consome chamadas de LLM. O build é **pausável e retomável** por quota — se você bater um limite de rate/custo no meio do processo, ele continua de onde parou, não recomeça do zero.

## Onde os artefatos ficam

`.vectora/context-graph/` dentro do próprio workspace — os mesmos arquivos que `.vectoraignore` esconde do resto do Vectora também ficam fora do grafo.

## Estágios visuais (workbench)

Enquanto o grafo constrói, cada arquivo mostra um indicador de estágio:

| Estágio   | Cor (dark / light)                    | Significa                       |
| --------- | ------------------------------------- | ------------------------------- |
| AST       | azul-claro `#4a9eff` / azul `#1f6feb` | parsing estrutural em andamento |
| Semântico | roxo `#b66dff` / roxo `#8957e5`       | extração por LLM em andamento   |
| Concluído | verde `#5ec26a` / verde `#2da44e`     | arquivo processado              |

## Veja também

- [RAG Híbrido](../rag) — recuperação por similaridade, complementar ao grafo
- [Usando a workbench](../../guides/using-the-workbench) — aba Context Graph em detalhe
