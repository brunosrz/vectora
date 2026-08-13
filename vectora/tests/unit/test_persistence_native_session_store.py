"""``SessionStore`` — persistência simplificada de sessões/mensagens
(Sprint 14 WS4). Mesmo padrão de fixture de
`test_persistence_native_sqlite_checkpointer.py`: pool real sobre
`tmp_path`, sem mock."""

from __future__ import annotations

import pytest

from backend.persistence.native.session_store import SessionStore
from backend.storage.sqlite.pool import AsyncConnectionPool
from backend.vtypes.message import (
    ContentBlock,
    MessageRole,
    ToolCall,
    VMessage,
    text_message,
)


@pytest.fixture
async def store(tmp_path):
    pool = AsyncConnectionPool(str(tmp_path / "sessions.db"), min_size=1, max_size=2)
    await pool.open()
    store = SessionStore(pool)
    await store.setup()
    try:
        yield store
    finally:
        await pool.close()


class TestCreateSession:
    async def test_cria_sessao_com_campos_obrigatorios(self, store: SessionStore):
        await store.create_session("thread-1", user_id="alice")

        async with store._pool.acquire() as conn:
            cur = await conn.execute(
                "SELECT user_id, mode, permission_mode FROM sessions WHERE thread_id = ?",
                ("thread-1",),
            )
            row = await cur.fetchone()

        assert row is not None
        assert tuple(row) == ("alice", "chat", "ask")

    async def test_criar_duas_vezes_a_mesma_thread_nao_falha(self, store: SessionStore):
        await store.create_session("thread-1", user_id="alice")
        await store.create_session("thread-1", user_id="alice")  # idempotente

        async with store._pool.acquire() as conn:
            cur = await conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE thread_id = ?", ("thread-1",)
            )
            fetched = await cur.fetchone()
            assert fetched is not None
            (total,) = fetched

        assert total == 1


class TestAppendMessageEGetHistory:
    async def test_round_trip_preserva_ordem_e_conteudo(self, store: SessionStore):
        await store.create_session("thread-1", user_id="alice")
        id1 = await store.append_message(
            "thread-1", text_message(MessageRole.USER, "oi")
        )
        await store.append_message(
            "thread-1",
            text_message(MessageRole.ASSISTANT, "olá!"),
            parent_message_id=id1,
        )

        historico = await store.get_history("thread-1")

        assert [m.text() for m in historico] == ["oi", "olá!"]
        assert [m.role for m in historico] == [MessageRole.USER, MessageRole.ASSISTANT]

    async def test_thread_sem_mensagem_devolve_lista_vazia(self, store: SessionStore):
        await store.create_session("thread-vazia", user_id="alice")

        assert await store.get_history("thread-vazia") == []

    async def test_preserva_tool_calls_e_tool_call_id(self, store: SessionStore):
        await store.create_session("thread-1", user_id="alice")
        assistente = VMessage(
            role=MessageRole.ASSISTANT,
            content=[ContentBlock(kind="text", text="chamando tool")],
            tool_calls=[ToolCall(id="call_1", name="somar", args={"a": 1})],
        )
        id_assistente = await store.append_message("thread-1", assistente)
        await store.append_message(
            "thread-1",
            VMessage(
                role=MessageRole.TOOL,
                content=[ContentBlock(kind="text", text="2")],
                tool_call_id="call_1",
            ),
            parent_message_id=id_assistente,
        )

        historico = await store.get_history("thread-1")

        assert historico[0].tool_calls == [
            ToolCall(id="call_1", name="somar", args={"a": 1})
        ]
        assert historico[1].tool_call_id == "call_1"

    async def test_fork_via_up_to_message_id_rele_branch_antiga_sem_apagar(
        self, store: SessionStore
    ):
        await store.create_session("thread-1", user_id="alice")
        id1 = await store.append_message(
            "thread-1", text_message(MessageRole.USER, "primeira pergunta")
        )
        await store.append_message(
            "thread-1",
            text_message(MessageRole.ASSISTANT, "primeira resposta"),
            parent_message_id=id1,
        )
        # Fork: edita a mensagem original e gera uma nova branch a partir dela.
        await store.append_message(
            "thread-1",
            text_message(MessageRole.USER, "pergunta editada"),
            parent_message_id=id1,
        )

        branch_ativa = await store.get_history("thread-1")
        branch_antiga = await store.get_history("thread-1", up_to_message_id=id1)

        assert [m.text() for m in branch_ativa] == [
            "primeira pergunta",
            "pergunta editada",
        ]
        assert [m.text() for m in branch_antiga] == ["primeira pergunta"]


class TestSetBranchHead:
    async def test_reaponta_a_branch_ativa_sem_apagar_mensagens(
        self, store: SessionStore
    ):
        await store.create_session("thread-1", user_id="alice")
        id1 = await store.append_message(
            "thread-1", text_message(MessageRole.USER, "pergunta")
        )
        id2 = await store.append_message(
            "thread-1",
            text_message(MessageRole.ASSISTANT, "resposta"),
            parent_message_id=id1,
        )
        await store.append_message(
            "thread-1",
            text_message(MessageRole.USER, "pergunta editada"),
            parent_message_id=id1,
        )

        await store.set_branch_head("thread-1", id2)
        historico = await store.get_history("thread-1")

        assert [m.text() for m in historico] == ["pergunta", "resposta"]

    async def test_apontar_para_mensagem_de_outra_thread_nao_afeta_historico(
        self, store: SessionStore
    ):
        await store.create_session("thread-1", user_id="alice")
        await store.create_session("thread-2", user_id="alice")
        id_thread2 = await store.append_message(
            "thread-2", text_message(MessageRole.USER, "outra thread")
        )

        # Nenhuma linha bate (thread_id errado) — não deve corromper thread-1.
        await store.set_branch_head("thread-1", id_thread2)

        assert await store.get_history("thread-1") == []
        assert [m.text() for m in await store.get_history("thread-2")] == [
            "outra thread"
        ]


class TestPendingApprovals:
    async def test_round_trip_put_get_clear(self, store: SessionStore):
        await store.create_session("thread-1", user_id="alice")
        await store.put_pending_approval(
            "thread-1",
            interrupt_id="int-1",
            tool_name="file_write",
            tool_call_id="call_1",
            args={"path": "a.py", "content": "x"},
            reasoning="editar arquivo",
        )

        pendente = await store.get_pending_approval("thread-1")
        assert pendente is not None
        assert pendente["tool_name"] == "file_write"
        assert pendente["args"] == {"path": "a.py", "content": "x"}
        assert pendente["reasoning"] == "editar arquivo"

        await store.clear_pending_approval("thread-1")
        assert await store.get_pending_approval("thread-1") is None

    async def test_thread_sem_pendencia_devolve_none(self, store: SessionStore):
        await store.create_session("thread-1", user_id="alice")

        assert await store.get_pending_approval("thread-1") is None

    async def test_segunda_chamada_de_put_sobrescreve_a_pendencia_anterior(
        self, store: SessionStore
    ):
        await store.create_session("thread-1", user_id="alice")
        await store.put_pending_approval(
            "thread-1",
            interrupt_id="int-1",
            tool_name="file_write",
            tool_call_id="call_1",
            args={},
        )
        await store.put_pending_approval(
            "thread-1",
            interrupt_id="int-2",
            tool_name="terminal",
            tool_call_id="call_2",
            args={"cmd": "ls"},
        )

        pendente = await store.get_pending_approval("thread-1")
        assert pendente is not None
        assert pendente["interrupt_id"] == "int-2"
        assert pendente["tool_name"] == "terminal"
