"""Tests for vectora/services/memory.py"""

from __future__ import annotations

import pytest

from vectora.services.memory import MemoryStore


@pytest.fixture
async def store():
    s = MemoryStore()
    await s.initialize()
    return s


class TestMemoryStore:
    @pytest.mark.asyncio
    async def test_save_and_get_all(self, store):
        await store.save("user1", "nome", "Bruno")
        memories = await store.get_all("user1")
        keys = [m["key"] for m in memories]
        assert "nome" in keys

    @pytest.mark.asyncio
    async def test_get_all_unknown_user_empty(self, store):
        memories = await store.get_all("user_xyz_desconhecido_99")
        assert memories == []

    @pytest.mark.asyncio
    async def test_delete_removes_key(self, store):
        await store.save("user2", "chave", "valor")
        await store.delete("user2", "chave")
        memories = await store.get_all("user2")
        keys = [m["key"] for m in memories]
        assert "chave" not in keys

    @pytest.mark.asyncio
    async def test_save_overwrites_existing(self, store):
        await store.save("user3", "pref", "A")
        await store.save("user3", "pref", "B")
        memories = await store.get_all("user3")
        pref = next((m for m in memories if m["key"] == "pref"), None)
        assert pref is not None
        assert pref["content"] == "B"

    @pytest.mark.asyncio
    async def test_get_returns_saved_content(self, store):
        await store.save("user4", "chave_get", "valor_get")
        result = await store.get("user4", "chave_get")
        assert result is not None
        assert result["content"] == "valor_get"

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_none(self, store):
        result = await store.get("user_none", "inexistente")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, store):
        result = await store.delete("user_none", "key_none")
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_removes_nothing_when_no_expired(self, store):
        removed = await store.cleanup_expired()
        assert isinstance(removed, int)
        assert removed >= 0

    @pytest.mark.asyncio
    async def test_save_with_ttl_and_cleanup(self, store):
        """TTL=0 gera expires_at no passado; cleanup remove o registro."""
        from datetime import UTC, datetime, timedelta

        import aiosqlite

        await store.save("user_ttl", "key_ttl", "conteudo", ttl_days=1)
        # Força expires_at para o passado diretamente no banco
        past = (datetime.now(UTC) - timedelta(days=2)).isoformat()
        async with aiosqlite.connect(store.db_dsn) as db:
            await db.execute(
                "UPDATE memories SET expires_at=? WHERE user_id=? AND key=?",
                (past, "user_ttl", "key_ttl"),
            )
            await db.commit()
        removed = await store.cleanup_expired()
        assert removed >= 1

    def test_raises_if_no_dsn_configured(self):
        from unittest.mock import patch

        from vectora.services.memory import MemoryStore

        with patch("vectora.services.memory.settings") as ms:
            ms.db_dsn = None
            with pytest.raises(ValueError, match="db_dsn"):
                MemoryStore()

    def test_strips_file_prefix(self, tmp_path):
        from vectora.services.memory import MemoryStore

        db = tmp_path / "mem.db"
        store = MemoryStore(f"file:///{db}")
        assert not store.db_dsn.startswith("file:///")
