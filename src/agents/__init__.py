"""Vectora Agents — Orchestrator principal + sub-agents especializados.

Cada agent possui LLM próprio, ferramentas específicas e system prompt dedicado.
"""

from src.agents.coder import coder
from src.agents.orchestrator import orchestrator
from src.agents.search import search

__all__ = ["coder", "orchestrator", "search"]
