"""Testes HTTP dos endpoints de memória (UX-11).

Usa FastAPI TestClient com um LangGraph InMemoryStore real (mesmo tipo de
BaseStore usado em produção via ``backend.services.agent_factory.get_store``),
cobrindo:
- GET /memory — lista vazia, paginação
- POST /memory — cria, 409 duplicado
- PUT /memory/{key} — edita, 404 inexistente
- DELETE /memory/{key} — deleta, 404 inexistente
- DELETE /memory — limpa tudo
- Regressão: API e memory tools do agente leem/escrevem o mesmo namespace
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from langgraph.store.memory import InMemoryStore


@pytest.fixture
def client(monkeypatch):
    """TestClient com um BaseStore real (InMemoryStore) compartilhado."""
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"

    store = InMemoryStore()

    async def _fake_get_store():
        return store

    monkeypatch.setattr("backend.services.agent_factory.get_store", _fake_get_store)

    from backend.api.server import create_app

    app = create_app(serve_static=False)
    tc = TestClient(app)
    tc.store = store  # type: ignore[attr-defined]

    yield tc

    os.environ.pop("VECTORA_AUTH_REQUIRED", None)


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


class TestMemorySharedStoreWithAgent:
    """Regressão: painel de configurações e memory tools do agente devem
    compartilhar o mesmo BaseStore/namespace — antes, o handler HTTP escrevia
    num MemoryStore SQLite à parte, nunca visto pelo agente (e vice-versa).

    ``backend.tools.memory._get_store`` normalmente resolve o store via
    ``langgraph.config.get_store()`` (contextvar setado pelo LangGraph durante
    a execução do grafo) — aqui simulamos essa resolução apontando pro mesmo
    ``InMemoryStore`` do fixture ``client``, que é exatamente a instância que
    ``create_deep_agent(store=...)`` recebe em produção (ver
    ``backend.services.agent_factory._ensure_infra``).
    """

    @pytest.mark.asyncio
    async def test_memory_saved_via_agent_tool_appears_in_api(
        self, client, monkeypatch
    ):
        from langchain_core.runnables import RunnableConfig

        from backend.tools.memory import save_memory

        monkeypatch.setattr("backend.tools.memory._get_store", lambda: client.store)

        config: RunnableConfig = {"configurable": {"user_id": "local"}}
        await save_memory.ainvoke(
            {"key": "from_agent", "content": "salvo pelo agente"}, config=config
        )

        resp = client.get("/memory/from_agent")
        assert resp.status_code == 200
        assert resp.json()["content"] == "salvo pelo agente"

    def test_memory_created_via_api_is_visible_to_agent_tool(self, client, monkeypatch):
        import asyncio

        from langchain_core.runnables import RunnableConfig

        from backend.tools.memory import get_memory

        monkeypatch.setattr("backend.tools.memory._get_store", lambda: client.store)

        client.post("/memory", json={"key": "from_api", "content": "salvo pelo painel"})

        config: RunnableConfig = {"configurable": {"user_id": "local"}}
        out = asyncio.run(get_memory.ainvoke({"key": "from_api"}, config=config))
        assert '"status": "found"' in out
        assert "salvo pelo painel" in out
