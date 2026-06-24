"""Context Graph — grafo de conhecimento/contexto nativo do Vectora.

**Nome.** "Grafo" é ambíguo no mundo de IA/LangChain (LangGraph, grafos de
execução, etc.). Este é um **grafo de contexto**: estrutura e relações extraídas
de um corpus (código/docs/papers) — quem chama quem, implements/cites, god nodes,
o "porquê" das decisões. Por isso o nome específico `context_graph` (e a workbench
"Context Graph"), interna e externamente.

**Inspiração / crédito.** A base é o **graphify** (MIT, Safi Shamsi —
https://github.com/safishamsi/graphify): o pipeline puro (AST via tree-sitter,
build NetworkX, clustering Leiden/Louvain, analyze, report, export) foi copiado e
está sendo **nativizado** — refatorado para a arquitetura do Vectora (async, LLM
próprio via `load_llm`, storage por workspace). A workbench credita "inspirado no
graphify". Enquanto a refatoração não termina, o pacote fica fora dos gates
estritos (ruff/ty/bandit) — ver pyproject e .pre-commit-config.

**Relação com o RAG (GraphRAG).** Complementa, não substitui, o RAG vetorial
(LanceDB) do Vectora. O RAG acha trechos por similaridade; o context graph dá
relações estruturais. A união (`graph_query`): vector search acha os nós-semente,
o grafo expande a vizinhança → contexto rico e barato em tokens.

A extração semântica (pass 3) NÃO usa o `llm.py` do graphify: passa pelo LLM ativo
do Vectora em `semantic.py`.
"""
