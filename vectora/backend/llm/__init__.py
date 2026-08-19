"""Construção, cache e fallback de LLM/embeddings/reranker por provider.

Tudo relacionado a "como o Vectora fala com o provider de LLM": montagem do
``CompositeBackend`` (``backends.py``), wrappers de fallback entre providers
em caso de quota/erro (``fallback_chat_client.py``,
``fallback_embeddings.py``, ``fallback_reranker.py``,
``provider_fallback.py``), e o cache auxiliar de LLM já bindado por usuário
(``llm_tools.py``).

Lazy imports (``__getattr__``) — mesmo padrão de ``backend.mcp`` — evitam
puxar LangChain/provider SDKs no import do pacote quando só um submódulo
específico é necessário.
"""

from __future__ import annotations

__all__ = [
    "build_backend_lazy",
]


def __getattr__(name: str) -> object:
    if name == "build_backend_lazy":
        from backend.llm.backends import build_backend_lazy

        return build_backend_lazy
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
