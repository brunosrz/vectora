"""Mapeamento de nome interno de nó do grafo → label legível para o usuário.

Usado pelo frontend para mostrar progresso semântico durante o streaming:
  "Analisando..." em vez de "model"
  "Executando ferramentas…" em vez de "tools"

Os nós são os do deep-agent (``create_deep_agent``): o nó do modelo, o nó de
tools, o agente principal (``vectora``) e os sub-agents (``coder``/``search``).
"""

from __future__ import annotations

NODE_LABELS: dict[str, str] = {
    "model": "Analisando...",
    "tools": "Executando ferramentas…",
    "vectora": "Processando…",
    "coder": "Escrevendo código…",
    "search": "Pesquisando…",
}

# Labels para quando o agente principal delega a um sub-agent via `task`.
_ROUTING_LABELS: dict[str, str] = {
    "search": "Roteando para busca…",
    "coder": "Roteando para agente de código…",
}

_GENERIC_LABEL = "Processando…"


def get_node_label(node: str) -> str:
    """Retorna o label legível para um nó do grafo."""
    return NODE_LABELS.get(node, _GENERIC_LABEL)


def get_routing_label(delegate_to: str) -> str:
    """Retorna o label de roteamento quando o agente delega a um sub-agent."""
    return _ROUTING_LABELS.get(delegate_to, f"Roteando para {delegate_to}…")
