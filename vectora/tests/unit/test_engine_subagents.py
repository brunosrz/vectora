"""``run_subagent``/``spawn_subagent_background`` — delegação de
subagentes nativa. Cada subagente é uma instância nova do motor
(`run_conversation`) numa sub-thread isolada com `parent_thread_id`
gravado — testado com o mesmo `_ScriptedChatClient` de
`test_engine_conversation_loop.py`.
"""

from __future__ import annotations

import asyncio

import pytest

from backend.engine.guardrails import LoopCapConfig, TurnBudget
from backend.engine.stream_events import SubagentOutput
from backend.engine.subagents import (
    SubagentSpec,
    run_subagent,
    spawn_subagent_background,
)
from backend.persistence.native.session_store import SessionStore
from backend.storage.sqlite.pool import AsyncConnectionPool
from backend.tools.context import ToolContext
from backend.tools.registry import TOOL_REGISTRY, ToolExtras, vtool
from backend.vtypes.message import ToolCallChunk, VMessageChunk


class _ScriptedChatClient:
    def __init__(self, turnos: list[list[VMessageChunk]]) -> None:
        self._turnos = turnos
        self.chamadas = 0

    async def astream(self, messages, *, tools=None, temperature=None, max_tokens=None):
        turno = self._turnos[self.chamadas]
        self.chamadas += 1
        for chunk in turno:
            yield chunk

    async def agenerate(
        self, messages, *, tools=None, temperature=None, max_tokens=None
    ):
        msg = "não usado (astream-only)"
        raise NotImplementedError(msg)


def _texto_chunk(texto: str) -> VMessageChunk:
    return VMessageChunk(delta_text=texto)


def _tool_call_chunk(*, index: int, id: str, name: str, args: str) -> VMessageChunk:  # noqa: A002
    return VMessageChunk(
        tool_call_chunks=[
            ToolCallChunk(index=index, id=id, name=name, args_fragment=args)
        ]
    )


@pytest.fixture
async def session_store(tmp_path):
    pool = AsyncConnectionPool(str(tmp_path / "subagents.db"), min_size=1, max_size=2)
    await pool.open()
    store = SessionStore(pool)
    await store.setup()
    await store.create_session("thread-pai", user_id="alice")
    try:
        yield store
    finally:
        await pool.close()


@pytest.fixture
def ctx() -> ToolContext:
    return ToolContext(user_id="alice", thread_id="thread-pai", permission_mode="ask")


def _spec(nome: str = "coder", tools=None) -> SubagentSpec:
    return SubagentSpec(
        name=nome,
        description="agente de teste",
        system_prompt="você é um agente de teste",
        tools=tools or [],
    )


class TestRunSubagentSincrono:
    async def test_devolve_o_texto_final_do_subagente(self, session_store, ctx):
        client = _ScriptedChatClient([[_texto_chunk("resultado do subagente")]])

        resultado = await run_subagent(
            _spec(),
            "faça algo",
            session_store=session_store,
            chat_client=client,
            ctx=ctx,
            parent_thread_id="thread-pai",
        )

        assert resultado == "resultado do subagente"

    async def test_sub_thread_isolada_com_parent_thread_id_gravado(
        self, session_store, ctx
    ):
        client = _ScriptedChatClient([[_texto_chunk("ok")]])

        await run_subagent(
            _spec(nome="search"),
            "pesquise algo",
            session_store=session_store,
            chat_client=client,
            ctx=ctx,
            parent_thread_id="thread-pai",
        )

        async with session_store._pool.acquire() as conn:
            cur = await conn.execute(
                "SELECT thread_id, parent_thread_id, mode FROM sessions "
                "WHERE parent_thread_id = ?",
                ("thread-pai",),
            )
            row = await cur.fetchone()

        assert row is not None
        thread_id, parent_thread_id, mode = row
        assert parent_thread_id == "thread-pai"
        assert mode == "subagent"
        assert thread_id.startswith("thread-pai:search:")
        assert thread_id != "thread-pai"

    async def test_historico_do_subagente_nao_herda_o_do_pai(self, session_store, ctx):
        # Popula o histórico do pai antes de delegar.
        from backend.vtypes.message import MessageRole, text_message

        await session_store.append_message(
            "thread-pai", text_message(MessageRole.USER, "mensagem do pai")
        )
        client = _ScriptedChatClient([[_texto_chunk("resposta isolada")]])

        await run_subagent(
            _spec(),
            "tarefa nova",
            session_store=session_store,
            chat_client=client,
            ctx=ctx,
            parent_thread_id="thread-pai",
        )

        historico_pai = await session_store.get_history("thread-pai")
        assert [m.text() for m in historico_pai] == ["mensagem do pai"]

    async def test_emite_subagent_output_running_e_complete(self, session_store, ctx):
        client = _ScriptedChatClient([[_texto_chunk("feito")]])
        eventos: list[SubagentOutput] = []

        async def on_event(event):
            if isinstance(event, SubagentOutput):
                eventos.append(event)

        await run_subagent(
            _spec(nome="coder"),
            "faça algo",
            session_store=session_store,
            chat_client=client,
            ctx=ctx,
            parent_thread_id="thread-pai",
            on_event=on_event,
        )

        assert [e.status for e in eventos] == ["running", "complete"]
        assert eventos[-1].content == "feito"

    async def test_hitl_dentro_do_subagente_pausa_sem_emitir_complete(
        self, session_store, ctx
    ):
        @vtool(extras=ToolExtras(destructive=True))
        async def escrever_no_subagente(ctx: ToolContext) -> str:
            """escreve algo."""
            return "nunca roda"

        spec = TOOL_REGISTRY.get("escrever_no_subagente")
        assert spec is not None

        client = _ScriptedChatClient(
            [
                [
                    _tool_call_chunk(
                        index=0,
                        id="call_1",
                        name="escrever_no_subagente",
                        args="{}",
                    )
                ]
            ]
        )
        eventos: list[SubagentOutput] = []

        async def on_event(event):
            if isinstance(event, SubagentOutput):
                eventos.append(event)

        resultado = await run_subagent(
            _spec(tools=[spec]),
            "escreva algo",
            session_store=session_store,
            chat_client=client,
            ctx=ctx,
            parent_thread_id="thread-pai",
            on_event=on_event,
            should_require_approval=lambda *_a: True,
        )

        assert resultado == ""
        assert [e.status for e in eventos] == ["running"]


class TestSpawnSubagentBackground:
    async def test_roda_em_background_e_pode_ser_esperada_depois(
        self, session_store, ctx
    ):
        client = _ScriptedChatClient([[_texto_chunk("resultado em background")]])

        task = spawn_subagent_background(
            _spec(),
            "faça em background",
            session_store=session_store,
            chat_client=client,
            ctx=ctx,
            parent_thread_id="thread-pai",
        )

        assert isinstance(task, asyncio.Task)
        resultado = await task
        assert resultado == "resultado em background"


class TestTurnBudgetDoTurnoPai:
    async def test_spawn_recusado_quando_teto_do_turno_pai_ja_estourou(
        self, session_store, ctx
    ):
        """`turn_budget` é o mesmo objeto do turno do agente pai — se já
        estourou (por qualquer dimensão), o spawn é recusado sem gastar
        nenhum recurso: nenhuma sessão criada, nenhuma chamada ao chat
        client."""
        budget = TurnBudget(config=LoopCapConfig(max_subagent_spawns_per_turn=0))
        client = _ScriptedChatClient([[_texto_chunk("nunca deveria rodar")]])

        resultado = await run_subagent(
            _spec(),
            "faça algo",
            session_store=session_store,
            chat_client=client,
            ctx=ctx,
            parent_thread_id="thread-pai",
            turn_budget=budget,
        )

        assert "não foi disparado" in resultado
        assert client.chamadas == 0
        assert budget.subagent_spawns == 0

    async def test_spawn_dentro_do_teto_incrementa_o_budget_do_pai(
        self, session_store, ctx
    ):
        budget = TurnBudget(config=LoopCapConfig(max_subagent_spawns_per_turn=2))
        client = _ScriptedChatClient([[_texto_chunk("ok")]])

        resultado = await run_subagent(
            _spec(),
            "faça algo",
            session_store=session_store,
            chat_client=client,
            ctx=ctx,
            parent_thread_id="thread-pai",
            turn_budget=budget,
        )

        assert resultado == "ok"
        assert budget.subagent_spawns == 1
        assert budget.exceeded is None
