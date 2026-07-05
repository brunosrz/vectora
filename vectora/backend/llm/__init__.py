"""Construção, cache e fallback de LLM/embeddings/reranker por provider.

Tudo relacionado a "como o Vectora fala com o provider de LLM": montagem do
``CompositeBackend`` (``backends.py``), cache global (``cache_llm.py``),
wrappers de fallback entre providers em caso de quota/erro
(``fallback_chat_model.py``, ``fallback_embeddings.py``,
``fallback_reranker.py``, ``provider_fallback.py``), e o cache auxiliar de
LLM já bindado por usuário (``llm_tools.py``).
"""
