"""Vectora Agents — Orchestrator principal + sub-agents especializados.

Cada agent possui LLM próprio, ferramentas específicas e system prompt dedicado.
"""

from backend.agents.coder import coder
from backend.agents.orchestrator import orchestrator
from backend.agents.search import search

__all__ = ["coder", "orchestrator", "search"]
