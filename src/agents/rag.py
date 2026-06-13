"""RAG Agent — Referência de arquitetura para o pipeline RAG do Vectora.

O "agente RAG" do Vectora é implementado como um **subgrafo LangGraph**
de múltiplos nós em `vectora/nodes/rag_subgraph.py`, não como uma função
de agente única (como `coder` e `search`). Isso reflete a diferença
arquitetural: o RAG é um pipeline de recuperação/decisão/reranking/injeção,
não uma sessão LLM em loop.

Fluxo interno do subgrafo:
  START → rag_retrieve → rag_decide_node
            ├── (score ≥ 0.7) → rag_inject → END
            ├── (score ≥ 0.4) → rag_rerank → rag_inject → END
            └── (score < 0.4) → rag_websearch → rag_inject → END

Integração no grafo principal (`graph.py`):
  orchestrator (routing_decision="rag") → rag_subgraph → orchestrator (síntese)

Para construir o subgrafo, use:
  from vectora.nodes.rag_subgraph import build_rag_subgraph
  rag_subgraph = build_rag_subgraph()

O orchestrator delega ao `rag_subgraph` quando `routing_decision == "rag"`.
Após o subgrafo injetar o contexto como SystemMessage(name="rag_context"),
o orchestrator é re-invocado e entra no caminho de síntese determinístico
(`_is_post_rag()` → `_synthesize_after_rag()` → END).
"""

# Re-exporta build_rag_subgraph para importação unificada via agents.*
from vectora.nodes.rag_subgraph import build_rag_subgraph

__all__ = ["build_rag_subgraph"]
