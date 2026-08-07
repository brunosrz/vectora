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


class TestNativeRedisCacheRoundtrip:
    """Round-trip real contra Redis — cache exato e semântico nativos
    (`backend/llm/native_redis_cache.py`). fakeredis não implementa `FT.*`,
    então esta cobertura só existe aqui (contra `redis-stack-server`)."""

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_cache_exato_roundtrip(self, _storage_stack_ok, redis_url):
        if not _storage_stack_ok:
            pytest.skip("Docker indisponível — Redis não iniciado")

        from langchain_core.outputs import Generation

        from backend.llm.native_redis_cache import NativeRedisCache

        cache = NativeRedisCache(redis_url=redis_url, ttl=30)
        gens = [Generation(text="resposta de teste")]

        await cache.aupdate("prompt exato", "llm-config-a", gens)
        result = await cache.alookup("prompt exato", "llm-config-a")
        assert result is not None
        assert result[0].text == "resposta de teste"

        # Erro/borda: prompt diferente é sempre miss, mesmo logo após o hit.
        miss = await cache.alookup("prompt totalmente diferente", "llm-config-a")
        assert miss is None

        await cache.aclear()
        assert await cache.alookup("prompt exato", "llm-config-a") is None

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_cache_semantico_hit_e_miss_por_threshold(
        self, _storage_stack_ok, redis_url
    ):
        if not _storage_stack_ok:
            pytest.skip("Docker indisponível — Redis não iniciado")

        from langchain_core.outputs import Generation

        from backend.llm.native_redis_cache import NativeRedisSemanticCache

        class _FixedEmbeddings:
            """Embeddings determinísticos — mesmo vetor pra prompts
            'próximos', vetor ortogonal pra prompts 'distantes', sem
            depender de credencial Cohere real no ambiente de teste."""

            async def aembed_query(self, text: str) -> list[float]:
                if "clima" in text:
                    return [1.0, 0.0, 0.0, 0.0]
                return [0.0, 1.0, 0.0, 0.0]

            def embed_query(self, text: str) -> list[float]:
                return [1.0, 0.0, 0.0, 0.0] if "clima" in text else [0.0, 1.0, 0.0, 0.0]

        cache = NativeRedisSemanticCache(
            embeddings=_FixedEmbeddings(),
            redis_url=redis_url,
            distance_threshold=0.1,
            ttl=30,
        )
        gens = [Generation(text="vai chover amanhã")]
        await cache.aupdate("como está o clima hoje", "llm-config-b", gens)

        # Hit: mesmo vetor (prompt semanticamente "igual" pro embeddings fake).
        hit = await cache.alookup("qual é o clima agora", "llm-config-b")
        assert hit is not None
        assert hit[0].text == "vai chover amanhã"

        # Erro/borda: vetor ortogonal (distância 1.0) fica muito acima do
        # threshold 0.1 — precisa ser miss, não um falso positivo.
        miss = await cache.alookup("me conte uma piada", "llm-config-b")
        assert miss is None

        # Erro/borda: mesmo vetor, mas llm_string diferente (outro modelo)
        # nunca deve dar hit — cada config tem seu próprio espaço via TAG.
        other_llm = await cache.alookup("qual é o clima agora", "llm-config-outro")
        assert other_llm is None

        await cache.aclear()
