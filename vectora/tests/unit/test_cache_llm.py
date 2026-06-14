"""Seleção do cache LLM em ``cache_llm.init_llm_cache``.

Valida a escolha entre RedisCache/RedisSemanticCache/InMemoryCache sem Redis
real — o caminho Redis é exercido nos testes de integração.
"""

from __future__ import annotations

import pytest

from backend.services import cache_llm
from backend.settings import settings


@pytest.fixture(autouse=True)
def _reset():
    cache_llm.reset_llm_cache()
    yield
    cache_llm.reset_llm_cache()


def test_lite_usa_inmemory(monkeypatch: pytest.MonkeyPatch) -> None:
    from langchain_core.caches import InMemoryCache

    monkeypatch.setattr(settings, "storage_mode", "lite")
    monkeypatch.setattr(settings, "cache_llm_enabled", True)
    cache = cache_llm.init_llm_cache()
    assert isinstance(cache, InMemoryCache)
    assert cache_llm.active_cache_name() == "InMemoryCache"


def test_desativado_retorna_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "cache_llm_enabled", False)
    assert cache_llm.init_llm_cache() is None
    assert cache_llm.active_cache_name() == "none"


def test_complete_redis_inacessivel_cai_para_inmemory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from langchain_core.caches import InMemoryCache

    monkeypatch.setattr(settings, "storage_mode", "complete")
    monkeypatch.setattr(settings, "cache_llm_enabled", True)
    # Porta 9 (discard) — nada escutando; probe falha rápido.
    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:9/0")
    cache = cache_llm.init_llm_cache()
    assert isinstance(cache, InMemoryCache)


def test_complete_redis_acessivel_usa_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    monkeypatch.setattr(settings, "storage_mode", "complete")
    monkeypatch.setattr(settings, "cache_llm_enabled", True)
    monkeypatch.setattr(settings, "redis_url", "redis://localhost:6379/0")
    # Evita conexão real: stub do builder Redis e do probe de módulos.
    monkeypatch.setattr(cache_llm, "_build_redis_cache", lambda url: sentinel)
    monkeypatch.setattr(cache_llm, "_redis_supports_cache", lambda url: True)
    # redis_reachable é importado de kv dentro de _build_cache.
    from backend.services import kv

    monkeypatch.setattr(kv, "redis_reachable", lambda *a, **k: True)
    assert cache_llm._build_cache() is sentinel


def test_redis_sem_modulos_cai_para_inmemory(monkeypatch: pytest.MonkeyPatch) -> None:
    from langchain_core.caches import InMemoryCache

    monkeypatch.setattr(settings, "storage_mode", "complete")
    monkeypatch.setattr(settings, "cache_llm_enabled", True)
    monkeypatch.setattr(settings, "redis_url", "redis://localhost:6379/0")
    monkeypatch.setattr(cache_llm, "_redis_supports_cache", lambda url: False)
    from backend.services import kv

    monkeypatch.setattr(kv, "redis_reachable", lambda *a, **k: True)
    assert isinstance(cache_llm._build_cache(), InMemoryCache)


def test_semantic_sem_embeddings_cai_para_exato(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "cache_semantic", True)
    monkeypatch.setattr(settings, "redis_url", "redis://localhost:6379/0")
    # Sem embeddings Cohere → deve usar RedisCache exato (não RedisSemanticCache).
    from backend.storage import factory

    monkeypatch.setattr(factory, "_build_lc_embeddings", lambda: None)

    captured: dict = {}

    class _FakeRedisCache:
        def __init__(self, redis_url: str, ttl=None):
            captured["redis_url"] = redis_url

    import langchain_redis

    monkeypatch.setattr(langchain_redis, "RedisCache", _FakeRedisCache)
    out = cache_llm._build_redis_cache("redis://localhost:6379/0")
    assert isinstance(out, _FakeRedisCache)
    assert captured["redis_url"] == "redis://localhost:6379/0"
