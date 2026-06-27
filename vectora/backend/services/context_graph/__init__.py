"""Context Graph — grafo de conhecimento/contexto nativo do Vectora.

**Nome.** "Grafo" é ambíguo no mundo de IA/LangChain (LangGraph, grafos de
execução, etc.). Este é um **grafo de contexto**: estrutura e relações extraídas
de um corpus (código/docs/papers) — quem chama quem, implements/cites, god nodes,
o "porquê" das decisões. Por isso o nome específico `context_graph` (e a workbench
"Context Graph"), interna e externamente.

**Pipeline.** Extração AST via tree-sitter, build NetworkX, clustering
Leiden/Louvain, analyze, report e export. A extração semântica (pass 3) passa
pelo LLM ativo do Vectora (`load_llm` + `ainvoke` async em `semantic.py`), com
storage por workspace.

**Relação com o RAG (GraphRAG).** Complementa, não substitui, o RAG vetorial
(LanceDB) do Vectora. O RAG acha trechos por similaridade; o context graph dá
relações estruturais. A união (`graph_query`): vector search acha os nós-semente,
o grafo expande a vizinhança → contexto rico e barato em tokens.
"""
