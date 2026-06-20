"""Testes da API HTTP de memórias (GET/POST/PUT/DELETE /memory/).

Usa SQLite temporário (tmp_path) e auth desabilitada para verificar o fluxo
completo da camada HTTP sem mocks — garante que o endpoint e o MemoryStore
funcionam de ponta a ponta com dados reais.
"""

from __future__ import annotations

import os

import pytest

# ── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def memory_client(tmp_path, monkeypatch):
    """TestClient com MemoryStore real (SQLite temporário) e auth desabilitada.

    O namespace usado é "user:local" — _get_user_id() retorna esse valor
    quando request.state.user é None (sem token válido + auth desabilitada).
    """
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"

    from backend.services import memory as mem_mod
    from backend.services.memory import MemoryStore

    store = MemoryStore(db_dsn=str(tmp_path / "mem_test.db"))
    await store.initialize()
    monkeypatch.setattr(mem_mod, "_memory_store", store)

    from fastapi.testclient import TestClient

    from backend.api.server import create_app

    app = create_app(serve_static=False)
    client = TestClient(app, raise_server_exceptions=False)
    yield client

    os.environ["VECTORA_AUTH_REQUIRED"] = "false"


# ── Testes ────────────────────────────────────────────────────────────────────


class TestListMemories:
    def test_empty_list_for_new_user(self, memory_client):
        r = memory_client.get("/memory")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["memories"] == []

    def test_returns_saved_memory(self, memory_client):
        memory_client.post(
            "/memory",
            json={"key": "list_key", "content": "conteudo teste"},
        )
        r = memory_client.get("/memory")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        keys = [m["key"] for m in body["memories"]]
        assert "list_key" in keys

    def test_pagination_limit(self, memory_client):
        for i in range(5):
            memory_client.post("/memory/", json={"key": f"pag_{i}", "content": f"c{i}"})
        r = memory_client.get("/memory/?limit=2&offset=0")
        assert r.status_code == 200
        body = r.json()
        assert len(body["memories"]) == 2
        assert body["total"] == 5


class TestCreateMemory:
    def test_create_returns_201(self, memory_client):
        r = memory_client.post(
            "/memory", json={"key": "nova_key", "content": "novo conteudo"}
        )
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "created"
        assert body["key"] == "nova_key"

    def test_duplicate_key_returns_409(self, memory_client):
        memory_client.post("/memory/", json={"key": "dup_key", "content": "primeiro"})
        r = memory_client.post("/memory", json={"key": "dup_key", "content": "segundo"})
        assert r.status_code == 409


class TestUpdateMemory:
    def test_update_existing_key(self, memory_client):
        memory_client.post("/memory/", json={"key": "upd_key", "content": "antes"})
        r = memory_client.put("/memory/upd_key", json={"content": "depois"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "updated"
        assert body["key"] == "upd_key"

        r2 = memory_client.get("/memory/upd_key")
        assert r2.status_code == 200
        assert r2.json()["content"] == "depois"

    def test_update_nonexistent_key_returns_404(self, memory_client):
        r = memory_client.put("/memory/inexistente", json={"content": "x"})
        assert r.status_code == 404


class TestDeleteMemory:
    def test_delete_existing_key(self, memory_client):
        memory_client.post("/memory/", json={"key": "del_key", "content": "vai"})
        r = memory_client.delete("/memory/del_key")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "deleted"

        r2 = memory_client.get("/memory/del_key")
        assert r2.status_code == 404

    def test_delete_nonexistent_key_returns_404(self, memory_client):
        r = memory_client.delete("/memory/nunca_existiu")
        assert r.status_code == 404


class TestClearAllMemories:
    def test_clear_removes_all(self, memory_client):
        for i in range(3):
            memory_client.post("/memory/", json={"key": f"clr_{i}", "content": f"c{i}"})

        r = memory_client.delete("/memory")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "deleted"
        assert body["deleted"] == 3

        r2 = memory_client.get("/memory")
        assert r2.json()["total"] == 0

    def test_clear_empty_store_returns_zero(self, memory_client):
        r = memory_client.delete("/memory")
        assert r.status_code == 200
        assert r.json()["deleted"] == 0
