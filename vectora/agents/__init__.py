"""Vectora Agents — Subagents especializados do sistema multi-agente.

Cada agent possui LLM próprio, ferramentas específicas e system prompt dedicado.
"""

from vectora.agents.coder import coder
from vectora.agents.direct import direct
from vectora.agents.search import search
from vectora.agents.supervisor import classify_intent, supervisor

__all__ = ["classify_intent", "coder", "direct", "search", "supervisor"]
