"""Tests for src/services/memory.py e GET/POST/PUT/DELETE /memory (HTTP)."""

from __future__ import annotations

import os

import pytest

from backend.services.memory import MemoryStore


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

        from backend.services.memory import MemoryStore

        with patch("backend.services.memory.settings") as ms:
            ms.db_dsn = None
            with pytest.raises(ValueError, match="db_dsn"):
                MemoryStore()

    def test_strips_file_prefix(self, tmp_path):
        from backend.services.memory import MemoryStore

        db = tmp_path / "mem.db"
        store = MemoryStore(f"file:///{db}")
        assert not store.db_dsn.startswith("file:///")


# ── HTTP API (/memory) com SQLite real ───────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_memory_singleton():
    import backend.services.memory as mem_mod
    mem_mod._memory_store = None
    yield
    mem_mod._memory_store = None


@pytest.fixture
def memory_client(tmp_path):
    """TestClient com MemoryStore real (tmp SQLite) e auth desabilitada.

    _get_user_id() retorna "user:local" quando request.state.user é None.
    """
    import asyncio

    import backend.services.memory as mem_mod

    db_file = str(tmp_path / "mem_test.db")
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"
    os.environ["VECTORA_DB_FILE"] = db_file

    store = MemoryStore(db_dsn=db_file)
    asyncio.run(store.initialize())
    mem_mod._memory_store = store

    from fastapi.testclient import TestClient

    from backend.api.server import create_app

    app = create_app(serve_static=False)
    yield TestClient(app, raise_server_exceptions=False)

    os.environ.pop("VECTORA_AUTH_REQUIRED", None)
    os.environ.pop("VECTORA_DB_FILE", None)
    mem_mod._memory_store = None


class TestMemoryAPI:
    def test_list_empty(self, memory_client):
        r = memory_client.get("/memory")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["memories"] == []

    def test_list_returns_saved(self, memory_client):
        memory_client.post("/memory", json={"key": "k1", "content": "v1"})
        r = memory_client.get("/memory")
        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert r.json()["memories"][0]["key"] == "k1"

    def test_create_returns_201(self, memory_client):
        r = memory_client.post("/memory", json={"key": "nova", "content": "c"})
        assert r.status_code == 201
        assert r.json()["key"] == "nova"

    def test_create_duplicate_returns_409(self, memory_client):
        memory_client.post("/memory", json={"key": "dup", "content": "a"})
        r = memory_client.post("/memory", json={"key": "dup", "content": "b"})
        assert r.status_code == 409

    def test_update_existing(self, memory_client):
        memory_client.post("/memory", json={"key": "upd", "content": "antes"})
        r = memory_client.put("/memory/upd", json={"content": "depois"})
        assert r.status_code == 200
        r2 = memory_client.get("/memory/upd")
        assert r2.status_code == 200
        assert r2.json()["content"] == "depois"

    def test_update_missing_returns_404(self, memory_client):
        r = memory_client.put("/memory/inexistente", json={"content": "x"})
        assert r.status_code == 404

    def test_delete_key(self, memory_client):
        memory_client.post("/memory", json={"key": "del", "content": "v"})
        r = memory_client.delete("/memory/del")
        assert r.status_code == 200
        assert memory_client.get("/memory/del").status_code == 404

    def test_delete_missing_returns_404(self, memory_client):
        r = memory_client.delete("/memory/nunca_existiu")
        assert r.status_code == 404

    def test_clear_all(self, memory_client):
        for i in range(3):
            memory_client.post("/memory", json={"key": f"c{i}", "content": "x"})
        r = memory_client.delete("/memory")
        assert r.status_code == 200
        assert r.json()["deleted"] == 3
        assert memory_client.get("/memory").json()["total"] == 0

    def test_clear_empty_returns_zero(self, memory_client):
        r = memory_client.delete("/memory")
        assert r.status_code == 200
        assert r.json()["deleted"] == 0
