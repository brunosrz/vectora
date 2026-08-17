"""Construção, cache e fallback de LLM/embeddings/reranker por provider.

Tudo relacionado a "como o Vectora fala com o provider de LLM": montagem do
``CompositeBackend`` (``backends.py``), cache global (``cache_llm.py``),
wrappers de fallback entre providers em caso de quota/erro
(``fallback_chat_client.py``, ``fallback_embeddings.py``,
``fallback_reranker.py``, ``provider_fallback.py``), e o cache auxiliar de
LLM já bindado por usuário (``llm_tools.py``).

Lazy imports (``__getattr__``) — mesmo padrão de ``backend.mcp`` — evitam
puxar LangChain/provider SDKs no import do pacote quando só um submódulo
específico é necessário.
"""

from __future__ import annotations

__all__ = [
    "build_backend_lazy",
    "init_llm_cache",
]


def __getattr__(name: str) -> object:
    if name == "build_backend_lazy":
        from backend.llm.backends import build_backend_lazy

        return build_backend_lazy
    if name == "init_llm_cache":
        from backend.llm.cache_llm import init_llm_cache

        return init_llm_cache
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
