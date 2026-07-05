"""Testes de integração — Redis (conectividade, cache LLM, chat history).

Requer Redis rodando (vectora-redis via docker).
Os fixtures de conftest.py sobem o container automaticamente se Docker estiver
disponível; do contrário, todos os testes são pulados.
"""

from __future__ import annotations

import pytest


class TestRedisConnectivity:
    """Conectividade básica ao Redis."""

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_ping(self, redis_client):
        result = await redis_client.ping()
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_set_get(self, redis_client):
        await redis_client.set("_vtest_key", "hello", ex=30)
        val = await redis_client.get("_vtest_key")
        assert val == b"hello"
        await redis_client.delete("_vtest_key")

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_set_get_error_incr_on_list(self, redis_client):
        """Erro: INCR em chave que é uma lista levanta ResponseError."""
        import redis.asyncio

        await redis_client.delete("_vtest_list")
        await redis_client.rpush("_vtest_list", "item")
        with pytest.raises(redis.asyncio.ResponseError):
            await redis_client.incr("_vtest_list")
        await redis_client.delete("_vtest_list")

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_key_expiry(self, redis_client):
        """Chaves com TTL expiram após o tempo configurado."""
        import asyncio

        await redis_client.set("_vtest_expire", "val", px=150)
        before = await redis_client.get("_vtest_expire")
        assert before == b"val"
        await asyncio.sleep(0.3)
        after = await redis_client.get("_vtest_expire")
        assert after is None

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_delete(self, redis_client):
        await redis_client.set("_vtest_del", "x")
        await redis_client.delete("_vtest_del")
        val = await redis_client.get("_vtest_del")
        assert val is None

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_error_get_nonexistent_returns_none(self, redis_client):
        """GET em chave inexistente retorna None, não levanta exceção."""
        await redis_client.delete("_vtest_nonexistent_xyz")
        val = await redis_client.get("_vtest_nonexistent_xyz")
        assert val is None


class TestRedisLLMCache:
    """Cache LLM via Redis (init_llm_cache)."""

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_init_llm_cache_complete_mode(self, redis_url, monkeypatch):
        """init_llm_cache() em storage_mode=complete retorna instância de cache."""
        import backend.settings as _s
        from backend.llm.cache_llm import init_llm_cache, reset_llm_cache

        monkeypatch.setattr(_s.settings, "storage_mode", "complete")
        monkeypatch.setattr(_s.settings, "redis_url", redis_url)
        monkeypatch.setattr(_s.settings, "cache_llm_enabled", True)
        monkeypatch.setattr(_s.settings, "cache_semantic", False)

        try:
            cache = init_llm_cache()
            assert cache is not None
        finally:
            reset_llm_cache()

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_init_llm_cache_disabled_returns_none(self, redis_url, monkeypatch):
        """init_llm_cache() com cache_llm_enabled=False retorna None."""
        import backend.settings as _s
        from backend.llm.cache_llm import init_llm_cache, reset_llm_cache

        monkeypatch.setattr(_s.settings, "cache_llm_enabled", False)

        try:
            result = init_llm_cache()
            assert result is None
        finally:
            reset_llm_cache()

    @pytest.mark.storage
    def test_init_llm_cache_lite_mode_uses_inmemory(self, monkeypatch):
        """Modo lite sempre usa InMemoryCache independente de redis_url."""
        from langchain_core.caches import InMemoryCache

        import backend.settings as _s
        from backend.llm.cache_llm import init_llm_cache, reset_llm_cache

        monkeypatch.setattr(_s.settings, "storage_mode", "lite")
        monkeypatch.setattr(_s.settings, "cache_llm_enabled", True)

        try:
            cache = init_llm_cache()
            assert isinstance(cache, InMemoryCache)
        finally:
            reset_llm_cache()


class TestRedisChatHistory:
    """RedisChatMessageHistory via get_chat_history()."""

    @pytest.mark.storage
    def test_get_chat_history_wrong_backend_returns_none(self, monkeypatch):
        """get_chat_history() retorna None quando backend != redis."""
        import backend.settings as _s
        from backend.storage.redis.chat_history import get_chat_history

        monkeypatch.setattr(_s.settings, "cache_history_backend", "default")
        result = get_chat_history("session-abc")
        assert result is None

    @pytest.mark.storage
    def test_get_chat_history_no_redis_url_returns_none(self, monkeypatch):
        """Erro: sem redis_url configurado, retorna None mesmo com backend=redis."""
        import backend.settings as _s
        from backend.storage.redis.chat_history import get_chat_history

        monkeypatch.setattr(_s.settings, "cache_history_backend", "redis")
        monkeypatch.setattr(_s.settings, "redis_url", None)
        result = get_chat_history("session-abc")
        assert result is None

    @pytest.mark.storage
    def test_get_chat_history_returns_history_object(
        self, _storage_stack_ok, redis_url, monkeypatch
    ):
        """Com backend=redis e Redis acessível, retorna RedisChatMessageHistory."""
        if not _storage_stack_ok:
            pytest.skip("Docker indisponível — Redis não iniciado")

        # Pré-checa conectividade autenticada. A porta pode estar aberta com um
        # Redis legado sem --requirepass (o probe de _storage_stack_ok só testa
        # o socket), e aí a URL default com senha falharia no AUTH. Isso é
        # desconfiguração de ambiente, não bug — pula com motivo. Em setup limpo
        # (compose recriou o Redis com senha) o ping passa e o teste roda.
        import redis as _redis
        from redis.exceptions import RedisError

        _probe = _redis.from_url(redis_url)
        try:
            _probe.ping()
        except RedisError as exc:
            pytest.skip(f"Redis local incompatível com a URL default: {exc}")
        finally:
            _probe.close()

        from langchain_redis import RedisChatMessageHistory

        import backend.settings as _s
        from backend.storage.redis.chat_history import get_chat_history

        monkeypatch.setattr(_s.settings, "cache_history_backend", "redis")
        monkeypatch.setattr(_s.settings, "redis_url", redis_url)

        result = get_chat_history("session-test-xyz")
        assert isinstance(result, RedisChatMessageHistory)
