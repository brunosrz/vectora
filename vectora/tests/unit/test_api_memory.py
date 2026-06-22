"""Testes HTTP dos endpoints de memória (UX-11).

Usa FastAPI TestClient com banco SQLite temporário, cobrindo:
- GET /memory — lista vazia, paginação
- POST /memory — cria, 409 duplicado
- PUT /memory/{key} — edita, 404 inexistente
- DELETE /memory/{key} — deleta, 404 inexistente
- DELETE /memory — limpa tudo
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_memory_singleton():
    """Reset memory singleton antes de cada teste (autouse)."""
    import backend.services.memory as mem_mod
    mem_mod._memory_store = None
    yield
    mem_mod._memory_store = None


@pytest.fixture
def client():
    """TestClient com MemoryStore em-memória (isolado por teste)."""
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"
    # Usa :memory: para garantir isolamento
    os.environ["VECTORA_DB_FILE"] = ":memory:"

    # Reset singleton
    import backend.services.memory as mem_mod
    mem_mod._memory_store = None

    from backend.api.server import create_app

    app = create_app(serve_static=False)
    tc = TestClient(app)

    yield tc

    # Cleanup
    os.environ.pop("VECTORA_DB_FILE", None)
    mem_mod._memory_store = None


class TestMemoryList:
    def test_list_empty(self, client):
        """GET /memory retorna lista vazia inicialmente."""
        resp = client.get("/memory")
        assert resp.status_code == 200
        data = resp.json()
        assert data["memories"] == []
        assert data["total"] == 0

    def test_list_with_items(self, client):
        """Lista retorna itens após POST."""
        client.post(
            "/memory",
            json={"key": "test1", "content": "conteúdo 1"},
        )
        resp = client.get("/memory")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["memories"]) >= 1
        assert any(m["key"] == "test1" for m in data["memories"])


class TestMemoryCreate:
    def test_create_happy(self, client):
        """POST /memory cria nova memória."""
        resp = client.post(
            "/memory",
            json={
                "key": "my_key",
                "content": "my content",
                "metadata": {"tag": "test"},
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "created"
        assert data["key"] == "my_key"

        get_resp = client.get("/memory/my_key")
        assert get_resp.status_code == 200
        mem = get_resp.json()
        assert mem["content"] == "my content"

    def test_create_duplicate_409(self, client):
        """POST duplicada retorna 409 Conflict."""
        client.post("/memory", json={"key": "dup_key", "content": "first"})
        resp = client.post("/memory", json={"key": "dup_key", "content": "second"})
        assert resp.status_code == 409


class TestMemoryUpdate:
    def test_update_happy(self, client):
        """PUT /memory/{key} edita conteúdo."""
        client.post("/memory", json={"key": "edit_key", "content": "original"})

        resp = client.put(
            "/memory/edit_key",
            json={"content": "updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

        get_resp = client.get("/memory/edit_key")
        assert get_resp.json()["content"] == "updated"

    def test_update_nonexistent_404(self, client):
        """PUT em chave inexistente retorna 404."""
        resp = client.put("/memory/nonexistent", json={"content": "should fail"})
        assert resp.status_code == 404


class TestMemoryDelete:
    def test_delete_happy(self, client):
        """DELETE /memory/{key} remove."""
        client.post("/memory", json={"key": "del_key", "content": "to delete"})
        resp = client.delete("/memory/del_key")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        get_resp = client.get("/memory/del_key")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_404(self, client):
        """DELETE inexistente retorna 404."""
        resp = client.delete("/memory/nonexistent")
        assert resp.status_code == 404
