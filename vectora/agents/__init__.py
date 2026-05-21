"""Vectora Agents — Orchestrator principal + sub-agents especializados.

Cada agent possui LLM próprio, ferramentas específicas e system prompt dedicado.
"""

from vectora.agents.coder import coder
from vectora.agents.orchestrator import orchestrator
from vectora.agents.search import search

__all__ = ["coder", "orchestrator", "search"]
