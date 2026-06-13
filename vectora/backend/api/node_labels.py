"""Mapeamento de nome interno de nó do grafo → label legível para o usuário.

Usado pelo frontend para mostrar progresso semântico durante o streaming:
  "Analisando..." em vez de "orchestrator"
  "Pesquisando na web…" em vez de "search_agent"
"""

from __future__ import annotations

NODE_LABELS: dict[str, str] = {
    # Nós deepagents (E.B-1+)
    "model": "Analisando...",
    "tools": "Executando ferramentas…",
    "vectora": "Processando…",
    # Nós legacy (src/graph.py — mantidos até E5 cleanup)
    "orchestrator": "Analisando...",
    "invoke_llm": "Gerando resposta…",
    "search_agent": "Pesquisando na web…",
    "rag_agent": "Consultando base de documentos…",
    "coder_agent": "Escrevendo código…",
    "finalize": "Finalizando…",
    "hitl": "Aguardando aprovação…",
    "rag_subgraph": "Recuperando documentos relevantes…",
    "web_curation": "Filtrando resultados…",
    "parallel_executor": "Executando tarefas em paralelo…",
    "results_aggregator": "Agregando resultados…",
}

# Labels para quando o orchestrator decidiu delegar para um agente específico
_ROUTING_LABELS: dict[str, str] = {
    "search_agent": "Roteando para busca web…",
    "rag_agent": "Roteando para base de conhecimento…",
    "coder_agent": "Roteando para agente de código…",
    "finalize": "Finalizando…",
}

_GENERIC_LABEL = "Processando…"


def get_node_label(node: str) -> str:
    """Retorna o label legível para um nó do grafo."""
    return NODE_LABELS.get(node, _GENERIC_LABEL)


def get_routing_label(delegate_to: str) -> str:
    """Retorna o label de roteamento quando o orchestrator delega para um agente."""
    return _ROUTING_LABELS.get(delegate_to, f"Roteando para {delegate_to}…")
