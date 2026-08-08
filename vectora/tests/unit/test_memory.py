"""Tests — Per-User Memory isolation.

Verifica:
- _user_id_from_config retorna o user_id cru quando há user_id no configurable
  (o prefixo de namespace vem de _memory_namespace, que envolve em
  ("user", <id>, "memories"))
- fallback para workspace_<id> quando não há user_id mas há workspace
- fallback para session_<thread_id> como último recurso
- "local" quando não há nenhum identificador (config None / configurable vazio)
- endpoints REST existem e têm assinaturas corretas
- ids distintos (user/workspace/session) não colidem
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.store.memory import InMemoryStore

# ---------------------------------------------------------------------------
# N1 — _user_id_from_config prioridade
# ---------------------------------------------------------------------------


class TestUserIdFromConfig:
    """_user_id_from_config deve priorizar user_id autenticado."""

    def test_returns_user_namespace_when_user_id_present(self):
        from backend.tools.memory import _user_id_from_config

        config: Any = {"configurable": {"user_id": "abc123", "thread_id": "t1"}}
        result = _user_id_from_config(config)
        assert result == "abc123"

    def test_returns_workspace_namespace_when_no_user_id(self):
        from backend.tools.memory import _user_id_from_config

        config: Any = {"configurable": {"workspace_id": "ws1", "thread_id": "t1"}}
        result = _user_id_from_config(config)
        assert result == "workspace_ws1"

    def test_workspace_takes_precedence_over_thread_when_no_user(self):
        from backend.tools.memory import _user_id_from_config

        config: Any = {
            "configurable": {
                "workspace_id": "ws1",
                "thread_id": "t1",
                # sem user_id
            }
        }
        result = _user_id_from_config(config)
        assert result == "workspace_ws1"

    def test_user_id_takes_precedence_over_workspace(self):
        """user_id autenticado supera workspace quando ambos presentes."""
        from backend.tools.memory import _user_id_from_config

        config: Any = {
            "configurable": {
                "user_id": "user_abc",
                "workspace_id": "ws1",
                "thread_id": "t1",
            }
        }
        result = _user_id_from_config(config)
        assert result == "user_abc"

    def test_returns_session_namespace_when_only_thread_id(self):
        from backend.tools.memory import _user_id_from_config

        config: Any = {"configurable": {"thread_id": "thread-xyz"}}
        result = _user_id_from_config(config)
        assert result == "session_thread-xyz"

    def test_returns_default_when_config_is_none(self):
        from backend.tools.memory import _user_id_from_config

        result = _user_id_from_config(None)
        assert result == "local"

    def test_returns_default_when_configurable_is_empty(self):
        from backend.tools.memory import _user_id_from_config

        result = _user_id_from_config({"configurable": {}})
        assert result == "local"

    def test_user_namespace_format(self):
        """Com user_id, o id retornado é o valor cru (sem prefixo); o prefixo
        de namespace ("user", <id>, "memories") vem de _memory_namespace."""
        from backend.tools.memory import _memory_namespace, _user_id_from_config

        config: Any = {"configurable": {"user_id": "user-99"}}
        assert _user_id_from_config(config) == "user-99"
        assert _memory_namespace(config) == ("user", "user-99", "memories")


# ---------------------------------------------------------------------------
# N2 — handler REST de memória
# ---------------------------------------------------------------------------


class TestMemoryHandlerExists:
    """src/api/handlers/memory.py deve existir com os endpoints esperados."""

    def test_memory_handler_module_exists(self):
        import backend.api.handlers.memory as mem_mod

        assert mem_mod is not None

    def test_router_exists(self):
        from backend.api.handlers.memory import router

        assert router is not None

    def test_list_memories_route_registered(self):
        from backend.api.handlers.memory import router

        routes = [r.path for r in router.routes]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert any("/memory" in r for r in routes)

    def test_delete_memory_route_registered(self):
        from backend.api.handlers.memory import router

        routes = [r.path for r in router.routes]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert any("/memory" in r for r in routes)


# ---------------------------------------------------------------------------
# N3 — isolamento de namespaces
# ---------------------------------------------------------------------------


class TestNamespaceIsolation:
    """Namespaces user:, workspace_, session_ são distintos e não se sobrepõem."""

    def test_user_namespace_not_equal_to_session_namespace(self):
        from backend.tools.memory import _user_id_from_config

        user_config: Any = {"configurable": {"user_id": "u1", "thread_id": "t1"}}
        session_config: Any = {"configurable": {"thread_id": "t1"}}

        user_ns = _user_id_from_config(user_config)
        session_ns = _user_id_from_config(session_config)

        assert user_ns != session_ns

    def test_user_namespace_not_equal_to_workspace_namespace(self):
        from backend.tools.memory import _user_id_from_config

        user_config: Any = {"configurable": {"user_id": "u1", "workspace_id": "ws1"}}
        workspace_config: Any = {"configurable": {"workspace_id": "ws1"}}

        user_ns = _user_id_from_config(user_config)
        workspace_ns = _user_id_from_config(workspace_config)

        assert user_ns != workspace_ns

    def test_different_users_have_different_namespaces(self):
        from backend.tools.memory import _user_id_from_config

        config_a: Any = {"configurable": {"user_id": "alice"}}
        config_b: Any = {"configurable": {"user_id": "bob"}}

        assert _user_id_from_config(config_a) != _user_id_from_config(config_b)


# ---------------------------------------------------------------------------
# Sprint 16 WS3 — save_memory/get_memory com `category` (gotcha/decision/
# preference/rule): campo opcional, persistido dentro do `value` já
# existente no BaseStore — sem migração de schema.
# ---------------------------------------------------------------------------


@pytest.fixture
def store(monkeypatch):
    real_store = InMemoryStore()
    monkeypatch.setattr("backend.tools.memory._get_store", lambda: real_store)
    return real_store


class TestSaveMemoryCategory:
    async def test_category_e_persistida_e_volta_no_get(self, store):
        from backend.tools.memory import get_memory, save_memory

        config: RunnableConfig = {"configurable": {"user_id": "u1"}}
        await save_memory.ainvoke(
            {"key": "pref_lang", "content": "PT-BR", "category": "preference"},
            config=config,
        )

        out = json.loads(await get_memory.ainvoke({"key": "pref_lang"}, config=config))

        assert out["category"] == "preference"

    async def test_sem_category_fica_none_retrocompativel(self, store):
        """Chamadas existentes sem `category` continuam funcionando —
        parâmetro é opcional, não quebra nenhum caller atual."""
        from backend.tools.memory import get_memory, save_memory

        config: RunnableConfig = {"configurable": {"user_id": "u1"}}
        await save_memory.ainvoke(
            {"key": "sem_categoria", "content": "conteúdo qualquer"}, config=config
        )

        out = json.loads(
            await get_memory.ainvoke({"key": "sem_categoria"}, config=config)
        )

        assert out["category"] is None

    async def test_category_invalida_e_rejeitada_sem_persistir(self, store):
        """Erro/borda: categoria fora do conjunto válido não é aceita
        silenciosamente. O `Literal["gotcha","decision","preference","rule"]`
        vira schema Pydantic da tool (LangChain `@tool`) — a validação
        acontece ANTES do corpo de `save_memory` rodar, então o erro chega
        como `ValidationError` da própria camada de parsing da tool, não
        como JSON `{"status":"failed"}` (esse é o caminho pra falha DENTRO
        da execução, ex. store indisponível — ver teste de `store` abaixo)."""
        from pydantic import ValidationError

        from backend.tools.memory import save_memory

        config: RunnableConfig = {"configurable": {"user_id": "u1"}}
        with pytest.raises(ValidationError, match="category"):
            await save_memory.ainvoke(
                {
                    "key": "categoria_ruim",
                    "content": "x",
                    "category": "nao_existe",
                },
                config=config,
            )

        # Nada foi persistido — a chave nunca chega a existir no store.
        item = await store.aget(("user", "u1", "memories"), "categoria_ruim")
        assert item is None

    async def test_listar_todas_inclui_category_de_cada_uma(self, store):
        from backend.tools.memory import get_memory, save_memory

        config: RunnableConfig = {"configurable": {"user_id": "u1"}}
        await save_memory.ainvoke(
            {"key": "a", "content": "x", "category": "gotcha"}, config=config
        )
        await save_memory.ainvoke({"key": "b", "content": "y"}, config=config)

        out = json.loads(await get_memory.ainvoke({}, config=config))

        by_key = {m["key"]: m["category"] for m in out["memories"]}
        assert by_key == {"a": "gotcha", "b": None}


class TestListFactContents:
    """`list_fact_contents` — acessor simples usado por `remember_trigger.py`
    (fora do wrapper `@tool`, que exige `RunnableConfig`) pra buscar os
    fatos já salvos de um usuário antes de propor duplicatas."""

    async def test_retorna_conteudo_de_todos_os_fatos_do_usuario(self, store):
        from backend.tools.memory import list_fact_contents, save_memory

        config: RunnableConfig = {"configurable": {"user_id": "u1"}}
        await save_memory.ainvoke({"key": "a", "content": "Fato A"}, config=config)
        await save_memory.ainvoke({"key": "b", "content": "Fato B"}, config=config)

        result = await list_fact_contents("u1")

        assert sorted(result) == ["Fato A", "Fato B"]

    async def test_usuario_sem_nenhum_fato_retorna_lista_vazia(self, store):
        from backend.tools.memory import list_fact_contents

        result = await list_fact_contents("usuario-novo")

        assert result == []
