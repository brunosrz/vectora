"""``get_native_agent`` e o fallback nativo-primeiro de
``aget_thread_messages``/``aget_thread_pending_interrupt`` — a superfície de
``backend/services/agent_factory.py`` que ``backend/api/handlers/chat.py``
consome no dispatch de produção (StreamChat/ResumeChat).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.persistence.native.session_store import SessionStore
from backend.services import agent_factory as af
from backend.storage.sqlite.pool import AsyncConnectionPool
from backend.vtypes.message import MessageRole, ToolCall, VMessage, text_message


@pytest.fixture(autouse=True)
def _limpa_cache_native_agent():
    af._native_agents.clear()
    yield
    af._native_agents.clear()


@pytest.fixture
async def session_store(tmp_path):
    pool = AsyncConnectionPool(str(tmp_path / "native.db"), min_size=1, max_size=2)
    await pool.open()
    store = SessionStore(pool)
    await store.setup()
    try:
        yield store
    finally:
        await pool.close()


class TestGetNativeAgent:
    async def test_dev_mode_inclui_delegate_to_subagent_e_catalogo_de_souls(self):
        agent = await af.get_native_agent(user_id="local", chat_mode=False)

        nomes = {t.name for t in agent.tool_registry.all()}
        assert "file_read" in nomes
        assert "web_search" in nomes
        assert "delegate_to_subagent" in nomes

        assert set(agent.subagent_catalog) == {
            "coder",
            "search",
            "reviewer",
            "tester",
            "devops",
            "writer-docs",
            "data-analyst",
            "security-auditor",
            "browser-qa",
            "planner",
        }
        coder = agent.subagent_catalog["coder"]
        assert any(t.name == "file_write" for t in coder.tools)
        # ask_parent_agent só faz sentido dentro de uma delegação.
        assert any(t.name == "ask_parent_agent" for t in coder.tools)

    async def test_chat_mode_restringe_tools_e_nao_tem_subagentes(self):
        agent = await af.get_native_agent(user_id="local", chat_mode=True)

        nomes = {t.name for t in agent.tool_registry.all()}
        assert "web_search" in nomes
        assert "file_write" not in nomes
        assert "delegate_to_subagent" not in nomes
        assert agent.subagent_catalog == {}

    async def test_cache_por_user_chat_mode_workspace(self):
        a1 = await af.get_native_agent(user_id="alice", chat_mode=False)
        a2 = await af.get_native_agent(user_id="alice", chat_mode=False)
        a3 = await af.get_native_agent(user_id="bob", chat_mode=False)

        assert a1 is a2
        assert a1 is not a3


class TestAgetThreadMessagesNativePrimeiro:
    async def test_thread_com_historico_nativo_usa_sessionstore(
        self, session_store: SessionStore
    ):
        await session_store.create_session("thread-nativa", user_id="alice")
        await session_store.append_message(
            "thread-nativa", text_message(MessageRole.SYSTEM, "prompt de sistema")
        )
        id_user = await session_store.append_message(
            "thread-nativa", text_message(MessageRole.USER, "oi")
        )
        await session_store.append_message(
            "thread-nativa",
            text_message(MessageRole.ASSISTANT, "olá!"),
            parent_message_id=id_user,
        )

        with patch.object(
            af, "get_session_store", AsyncMock(return_value=session_store)
        ):
            pairs = await af.aget_thread_messages("thread-nativa")

        assert [p[:2] for p in pairs] == [("human", "oi"), ("assistant", "olá!")]
        # checkpoint_id nativo é o id da mensagem (fork target de
        # SessionStore.set_branch_head), não um uuid do checkpointer LangGraph.
        assert pairs[0][2] == str(id_user)

    async def test_filtra_mensagens_de_tool_e_system(self, session_store: SessionStore):
        await session_store.create_session("thread-2", user_id="alice")
        assistente = VMessage(
            role=MessageRole.ASSISTANT,
            content=[],
            tool_calls=[ToolCall(id="call_1", name="somar", args={"a": 1})],
        )
        id_a = await session_store.append_message("thread-2", assistente)
        await session_store.append_message(
            "thread-2",
            VMessage(
                role=MessageRole.TOOL,
                content=[],
                tool_call_id="call_1",
                name="somar",
            ),
            parent_message_id=id_a,
        )

        with patch.object(
            af, "get_session_store", AsyncMock(return_value=session_store)
        ):
            pairs = await af.aget_thread_messages("thread-2")

        # Mensagem do assistente sem texto (só tool_calls) e o resultado de
        # tool nunca aparecem no histórico exibido ao usuário.
        assert pairs == []

    async def test_thread_sem_mensagem_nativa_devolve_lista_vazia(
        self, session_store: SessionStore
    ):
        """Sem checkpointer LangGraph legado a consultar, uma thread sem
        nenhum registro no SessionStore devolve lista vazia direto."""
        with patch.object(
            af, "get_session_store", AsyncMock(return_value=session_store)
        ):
            pairs = await af.aget_thread_messages("thread-inexistente")

        assert pairs == []


class TestAgetThreadPendingInterruptNativePrimeiro:
    async def test_pendencia_nativa_e_devolvida_do_session_store(
        self, session_store: SessionStore
    ):
        await session_store.create_session("thread-hitl", user_id="alice")
        await session_store.put_pending_approval(
            "thread-hitl",
            interrupt_id="intr-1",
            tool_name="file_write",
            tool_call_id="call_1",
            args={"path": "a.py"},
        )

        with patch.object(
            af, "get_session_store", AsyncMock(return_value=session_store)
        ):
            pending = await af.aget_thread_pending_interrupt("thread-hitl")

        assert pending == {
            "tool_name": "file_write",
            "args": {"path": "a.py"},
            "interrupt_id": "intr-1",
        }

    async def test_sem_pendencia_nativa_devolve_none(self, session_store: SessionStore):
        with patch.object(
            af, "get_session_store", AsyncMock(return_value=session_store)
        ):
            pending = await af.aget_thread_pending_interrupt("thread-sem-pendencia")

        assert pending is None
