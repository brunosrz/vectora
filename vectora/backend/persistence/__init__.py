"""Persistência de estado: checkpoints, sessões, KV transiente e traces.

``checkpoint.py`` (checkpointer LangGraph + backup/restore de workspace),
``session.py`` (ciclo de vida de sessão de chat), ``kv.py`` (KV genérico
com fallback Redis/SQLite) e ``tracer.py`` (coleta de traces de execução do
grafo para diagnóstico).

Lazy imports (``__getattr__``) — mesmo padrão de ``backend.mcp`` — evitam
puxar aiosqlite/Redis/LangGraph no import do pacote quando só um submódulo
específico é necessário.
"""

from __future__ import annotations

__all__ = [
    "Checkpointer",
    "SessionService",
    "get_kv",
    "tracer",
]


def __getattr__(name: str) -> object:
    if name == "Checkpointer":
        from backend.persistence.checkpoint import Checkpointer

        return Checkpointer
    if name == "SessionService":
        from backend.persistence.session import SessionService

        return SessionService
    if name == "get_kv":
        from backend.persistence.kv import get_kv

        return get_kv
    if name == "tracer":
        from backend.persistence.tracer import tracer

        return tracer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
