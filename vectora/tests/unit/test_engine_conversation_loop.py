"""``run_conversation`` — loop de conversa nativo (Sprint 14 WS5). `ChatClient`
mockado com uma sequência de turnos controlada (`finish_reason` por
chamada): parada normal, `max_iterations`, tool_calls sequenciais, tool_calls
paralelos não-destrutivos, e interrupção HITL no meio de um lote misto.
"""

from __future__ import annotations

import pytest

from backend.engine.conversation_loop import LoopConfig, run_conversation
from backend.engine.stream_events import (
    EngineEvent,
    HitlRequested,
    MessageBreak,
    MessageChunk,
    ToolResult,
)
from backend.persistence.native.session_store import SessionStore
from backend.storage.sqlite.pool import AsyncConnectionPool
from backend.tools.context import ToolContext
from backend.tools.registry import TOOL_REGISTRY, ToolExtras, ToolRegistry, vtool
from backend.vtypes.message import ToolCallChunk, VMessageChunk


def _register(registry: ToolRegistry, nome: str) -> None:
    spec = TOOL_REGISTRY.get(nome)
    assert spec is not None
    registry.register(spec)


class _ScriptedChatClient:
    """`astream` devolve um turno por chamada, na ordem do script — cada
    turno é a lista de `VMessageChunk` que o iteração daquela volta do loop
    deve produzir."""

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
        msg = "não usado pelo loop (astream-only)"
        raise NotImplementedError(msg)


@pytest.fixture
async def session_store(tmp_path):
    pool = AsyncConnectionPool(str(tmp_path / "loop.db"), min_size=1, max_size=2)
    await pool.open()
    store = SessionStore(pool)
    await store.setup()
    await store.create_session("thread-1", user_id="alice")
    try:
        yield store
    finally:
        await pool.close()


@pytest.fixture
def ctx() -> ToolContext:
    return ToolContext(user_id="alice", thread_id="thread-1")


def _texto_chunk(texto: str) -> VMessageChunk:
    return VMessageChunk(delta_text=texto)


def _tool_call_chunk(*, index: int, id: str, name: str, args: str) -> VMessageChunk:  # noqa: A002
    return VMessageChunk(
        tool_call_chunks=[
            ToolCallChunk(index=index, id=id, name=name, args_fragment=args)
        ]
    )


class TestParadaNormal:
    async def test_sem_tool_calls_para_no_primeiro_turno(self, session_store, ctx):
        client = _ScriptedChatClient([[_texto_chunk("olá!")]])
        resultado = await run_conversation(
            session_store=session_store,
            chat_client=client,
            tool_registry=ToolRegistry(),
            ctx=ctx,
            thread_id="thread-1",
            config=LoopConfig(),
        )

        assert resultado.stopped_reason == "stop"
        assert resultado.final_message is not None
        assert resultado.final_message.text() == "olá!"
        assert client.chamadas == 1

        historico = await session_store.get_history("thread-1")
        assert [m.text() for m in historico] == ["olá!"]


class TestMaxIterations:
    async def test_estoura_o_teto_sem_nunca_parar_naturalmente(
        self, session_store, ctx
    ):
        @vtool(extras=ToolExtras())
        async def loop_tool(ctx: ToolContext) -> str:
            """tool que sempre é chamada de novo."""
            return "ok"

        registry = ToolRegistry()
        _register(registry, "loop_tool")

        turno = [_tool_call_chunk(index=0, id="call_1", name="loop_tool", args="{}")]
        client = _ScriptedChatClient([turno, turno, turno])

        resultado = await run_conversation(
            session_store=session_store,
            chat_client=client,
            tool_registry=registry,
            ctx=ctx,
            thread_id="thread-1",
            config=LoopConfig(max_iterations=3),
        )

        assert resultado.stopped_reason == "max_iterations"
        assert client.chamadas == 3


class TestToolCallsSequenciais:
    async def test_chama_tool_depois_para_no_turno_seguinte(self, session_store, ctx):
        @vtool(extras=ToolExtras())
        async def somar(a: int, b: int, ctx: ToolContext) -> str:
            """soma dois números.
            Args:
                a: primeiro
                b: segundo
            """
            return str(a + b)

        registry = ToolRegistry()
        _register(registry, "somar")

        client = _ScriptedChatClient(
            [
                [
                    _tool_call_chunk(
                        index=0, id="call_1", name="somar", args='{"a":1,"b":2}'
                    )
                ],
                [_texto_chunk("a soma é 3")],
            ]
        )

        resultado = await run_conversation(
            session_store=session_store,
            chat_client=client,
            tool_registry=registry,
            ctx=ctx,
            thread_id="thread-1",
            config=LoopConfig(),
        )

        assert resultado.stopped_reason == "stop"
        assert resultado.final_message is not None
        assert resultado.final_message.text() == "a soma é 3"
        assert client.chamadas == 2

        historico = await session_store.get_history("thread-1")
        assert historico[0].tool_calls[0].name == "somar"
        assert historico[1].role.value == "tool"
        assert historico[1].text() == "3"
        assert historico[2].text() == "a soma é 3"


class TestToolCallsParalelos:
    async def test_duas_tools_nao_destrutivas_executam_e_retornam(
        self, session_store, ctx
    ):
        @vtool(extras=ToolExtras(destructive=False))
        async def ler_a(ctx: ToolContext) -> str:
            """lê a."""
            return "conteudo-a"

        @vtool(extras=ToolExtras(destructive=False))
        async def ler_b(ctx: ToolContext) -> str:
            """lê b."""
            return "conteudo-b"

        registry = ToolRegistry()
        _register(registry, "ler_a")
        _register(registry, "ler_b")

        client = _ScriptedChatClient(
            [
                [
                    _tool_call_chunk(index=0, id="call_1", name="ler_a", args="{}"),
                    _tool_call_chunk(index=1, id="call_2", name="ler_b", args="{}"),
                ],
                [_texto_chunk("terminei")],
            ]
        )

        resultado = await run_conversation(
            session_store=session_store,
            chat_client=client,
            tool_registry=registry,
            ctx=ctx,
            thread_id="thread-1",
            config=LoopConfig(),
        )

        assert resultado.stopped_reason == "stop"
        historico = await session_store.get_history("thread-1")
        resultados_tool = [m.text() for m in historico if m.role.value == "tool"]
        assert set(resultados_tool) == {"conteudo-a", "conteudo-b"}


class TestHitl:
    async def test_lote_misto_com_uma_tool_sensivel_pausa_sem_executar_nenhuma(
        self, session_store, ctx
    ):
        @vtool(extras=ToolExtras(destructive=False))
        async def ler_arquivo(ctx: ToolContext) -> str:
            """lê um arquivo."""
            return "nunca deveria rodar"

        @vtool(extras=ToolExtras(destructive=True))
        async def escrever_arquivo(ctx: ToolContext) -> str:
            """escreve um arquivo."""
            return "nunca deveria rodar"

        registry = ToolRegistry()
        _register(registry, "ler_arquivo")
        _register(registry, "escrever_arquivo")

        client = _ScriptedChatClient(
            [
                [
                    _tool_call_chunk(
                        index=0, id="call_1", name="ler_arquivo", args="{}"
                    ),
                    _tool_call_chunk(
                        index=1, id="call_2", name="escrever_arquivo", args="{}"
                    ),
                ]
            ]
        )

        def should_require_approval(nome, _ctx, _args, _history):
            return nome == "escrever_arquivo"

        resultado = await run_conversation(
            session_store=session_store,
            chat_client=client,
            tool_registry=registry,
            ctx=ctx,
            thread_id="thread-1",
            config=LoopConfig(),
            should_require_approval=should_require_approval,
        )

        assert resultado.stopped_reason == "interrupted"
        # Nenhuma tool do lote foi executada — só a mensagem do assistente
        # (com as tool_calls propostas) está no histórico.
        historico = await session_store.get_history("thread-1")
        assert [m.role.value for m in historico] == ["assistant"]
        assert len(historico[0].tool_calls) == 2

    async def test_sem_should_require_approval_nunca_pausa(self, session_store, ctx):
        @vtool(extras=ToolExtras(destructive=True))
        async def deletar(ctx: ToolContext) -> str:
            """deleta algo."""
            return "deletado"

        registry = ToolRegistry()
        _register(registry, "deletar")

        client = _ScriptedChatClient(
            [
                [_tool_call_chunk(index=0, id="call_1", name="deletar", args="{}")],
                [_texto_chunk("feito")],
            ]
        )

        resultado = await run_conversation(
            session_store=session_store,
            chat_client=client,
            tool_registry=registry,
            ctx=ctx,
            thread_id="thread-1",
            config=LoopConfig(),
        )

        assert resultado.stopped_reason == "stop"
        assert client.chamadas == 2


class TestEmissaoDeEventos:
    async def test_token_e_message_break_emitidos_na_ordem(self, session_store, ctx):
        client = _ScriptedChatClient([[_texto_chunk("oi"), _texto_chunk(" tudo bem")]])
        eventos: list[EngineEvent] = []

        async def on_event(event: EngineEvent) -> None:
            eventos.append(event)

        await run_conversation(
            session_store=session_store,
            chat_client=client,
            tool_registry=ToolRegistry(),
            ctx=ctx,
            thread_id="thread-1",
            config=LoopConfig(),
            on_event=on_event,
        )

        assert eventos == [
            MessageChunk(content="oi"),
            MessageChunk(content=" tudo bem"),
            MessageBreak(),
        ]

    async def test_tool_result_emitido_apos_execucao(self, session_store, ctx):
        @vtool(extras=ToolExtras())
        async def somar(a: int, b: int, ctx: ToolContext) -> str:
            """soma dois números.
            Args:
                a: primeiro
                b: segundo
            """
            return str(a + b)

        registry = ToolRegistry()
        _register(registry, "somar")

        client = _ScriptedChatClient(
            [
                [
                    _tool_call_chunk(
                        index=0, id="call_1", name="somar", args='{"a":1,"b":2}'
                    )
                ],
                [_texto_chunk("pronto")],
            ]
        )
        eventos: list[EngineEvent] = []

        async def on_event(event: EngineEvent) -> None:
            eventos.append(event)

        await run_conversation(
            session_store=session_store,
            chat_client=client,
            tool_registry=registry,
            ctx=ctx,
            thread_id="thread-1",
            config=LoopConfig(),
            on_event=on_event,
        )

        resultados_tool = [e for e in eventos if isinstance(e, ToolResult)]
        assert resultados_tool == [
            ToolResult(tool_call_id="call_1", content_json="3", is_error=False)
        ]

    async def test_hitl_requested_emitido_com_argumentos_da_tool(
        self, session_store, ctx
    ):
        @vtool(extras=ToolExtras(destructive=True))
        async def escrever(ctx: ToolContext) -> str:
            """escreve algo."""
            return "nunca roda"

        registry = ToolRegistry()
        _register(registry, "escrever")

        client = _ScriptedChatClient(
            [[_tool_call_chunk(index=0, id="call_1", name="escrever", args="{}")]]
        )
        eventos: list[EngineEvent] = []

        async def on_event(event: EngineEvent) -> None:
            eventos.append(event)

        await run_conversation(
            session_store=session_store,
            chat_client=client,
            tool_registry=registry,
            ctx=ctx,
            thread_id="thread-1",
            config=LoopConfig(),
            on_event=on_event,
            should_require_approval=lambda nome, _ctx, _args, _history: (
                nome == "escrever"
            ),
        )

        hitl_eventos = [e for e in eventos if isinstance(e, HitlRequested)]
        assert len(hitl_eventos) == 1
        assert hitl_eventos[0].tool_name == "escrever"
        assert hitl_eventos[0].args_json == "{}"
        assert hitl_eventos[0].interrupt_id  # gerado, não vazio
