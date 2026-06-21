"""Testes HTTP do endpoint /memory com SQLite real (UX-11a/b).

Verifica o fluxo completo: store SQLite temporário, sem mocks de I/O.
Auth desabilitada (VECTORA_AUTH_REQUIRED=false) — user cai em "user:local".
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("VECTORA_AUTH_REQUIRED", "false")


@pytest.fixture(scope="module")
def memory_client(tmp_path_factory):
    """TestClient com MemoryStore real em SQLite temporário."""
    import asyncio

    tmp = tmp_path_factory.mktemp("memory_api")
    db_path = str(tmp / "test_memory.db")

    # Cria e inicializa o store real
    from backend.services.memory import MemoryStore

    store = MemoryStore(db_path)
    asyncio.get_event_loop().run_until_complete(store.initialize())

    import backend.services.memory as mem_mod

    original = mem_mod._memory_store
    mem_mod._memory_store = store

    from fastapi.testclient import TestClient

    from backend.api.server import create_app

    app = create_app(serve_static=False)
    client = TestClient(app, raise_server_exceptions=True)
    yield client

    mem_mod._memory_store = original


class TestListMemories:
    def test_lista_vazia(self, memory_client):
        res = memory_client.get("/memory")
        assert res.status_code == 200
        data = res.json()
        assert data["memories"] == []
        assert data["total"] == 0

    def test_lista_apos_criar(self, memory_client):
        memory_client.post(
            "/memory",
            json={"key": "list_test", "content": "valor para listar"},
        )
        res = memory_client.get("/memory")
        assert res.status_code == 200
        keys = [m["key"] for m in res.json()["memories"]]
        assert "list_test" in keys


class TestCreateMemory:
    def test_cria_memoria(self, memory_client):
        res = memory_client.post(
            "/memory",
            json={"key": "nova_mem", "content": "conteúdo novo"},
        )
        assert res.status_code == 201
        assert res.json()["key"] == "nova_mem"

    def test_chave_duplicada_retorna_409(self, memory_client):
        memory_client.post(
            "/memory",
            json={"key": "dup_key", "content": "primeiro"},
        )
        res = memory_client.post(
            "/memory",
            json={"key": "dup_key", "content": "segundo"},
        )
        assert res.status_code == 409


class TestUpdateMemory:
    def test_edita_memoria(self, memory_client):
        memory_client.post(
            "/memory",
            json={"key": "edit_me", "content": "original"},
        )
        res = memory_client.put(
            "/memory/edit_me",
            json={"content": "editado"},
        )
        assert res.status_code == 200
        assert res.json()["key"] == "edit_me"

    def test_chave_inexistente_retorna_404(self, memory_client):
        res = memory_client.put(
            "/memory/nao_existe_xyz",
            json={"content": "qualquer"},
        )
        assert res.status_code == 404


class TestDeleteMemory:
    def test_deleta_memoria(self, memory_client):
        memory_client.post(
            "/memory",
            json={"key": "del_me", "content": "deletar"},
        )
        res = memory_client.delete("/memory/del_me")
        assert res.status_code == 200

        get_res = memory_client.get("/memory/del_me")
        assert get_res.status_code == 404

    def test_segundo_delete_retorna_404(self, memory_client):
        memory_client.post(
            "/memory",
            json={"key": "del_twice", "content": "x"},
        )
        memory_client.delete("/memory/del_twice")
        res = memory_client.delete("/memory/del_twice")
        assert res.status_code == 404


class TestClearAllMemories:
    def test_limpa_todas_as_memorias(self, memory_client):
        memory_client.post("/memory", json={"key": "c1", "content": "a"})
        memory_client.post("/memory", json={"key": "c2", "content": "b"})

        res = memory_client.delete("/memory")
        assert res.status_code == 200

        lista = memory_client.get("/memory").json()
        assert lista["total"] == 0
        assert lista["memories"] == []
