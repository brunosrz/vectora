"""Middleware stack — HITL DINÂMICO: um grafo só, política por request.

O HITL deixou de ser compile-time (um grafo por permission_mode) e passou a ler
``runtime.context.permission_mode`` em tempo de execução via o predicate único
``_dynamic_hitl_when``. Um único ``HumanInTheLoopMiddleware`` cobre todas as
tools destrutivas; a decisão de pausar acontece por request, conforme o modo
selecionado na appbar. Estes testes fixam a política canônica dos 5 modos
(manual/ask, aceitar/accept_edits, plano/plan, automático/auto, ignorar/bypass)
e os edges (runtime ausente, modo desconhecido).
"""

from __future__ import annotations

from types import SimpleNamespace

from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from backend.services.middleware import (
    _dynamic_hitl_when,
    _mode_should_interrupt,
    _plan_mode_should_interrupt,
    build_middleware_stack,
)


def _req(
    tool_name: str = "file_write",
    mode: str | None = "ask",
    messages: list | None = None,
) -> ToolCallRequest:
    """Request com ``runtime.context.permission_mode`` — como o grafo entrega.

    ``mode=None`` simula runtime/context ausente (tool fora do grafo).
    """
    runtime = None
    if mode is not None:
        runtime = SimpleNamespace(context=SimpleNamespace(permission_mode=mode))
    return ToolCallRequest(
        tool_call={"name": tool_name, "args": {}, "id": "x"},
        tool=None,
        state={"messages": messages or [HumanMessage(content="apague x")]},
        runtime=runtime,  # ty: ignore[invalid-argument-type]
    )


# ── Política canônica dos 5 modos (via _dynamic_hitl_when, ponta a ponta) ────


def test_ask_mode_interrompe_toda_tool_destrutiva():
    # manual: file_write E terminal pausam.
    assert _dynamic_hitl_when(_req("file_write", "ask")) is True
    assert _dynamic_hitl_when(_req("terminal", "ask")) is True


def test_accept_edits_auto_aprova_edicao_mas_pausa_terminal():
    # aceitar permissões: file_write roda sem pausa; terminal ainda pausa.
    assert _dynamic_hitl_when(_req("file_write", "accept_edits")) is False
    assert _dynamic_hitl_when(_req("terminal", "accept_edits")) is True


def test_auto_e_bypass_nunca_interrompem():
    # automático e ignorar permissões: nenhuma tool destrutiva pausa.
    for mode in ("auto", "bypass"):
        assert _dynamic_hitl_when(_req("file_write", mode)) is False
        assert _dynamic_hitl_when(_req("terminal", mode)) is False


def test_plan_mode_pausa_so_a_primeira_destrutiva_do_turno():
    # plano: 1ª destrutiva do turno pausa…
    assert _dynamic_hitl_when(_req("file_write", "plan")) is True
    # …mas se já houve um ToolMessage destrutivo neste turno, não pausa de novo.
    ja_passou = [
        HumanMessage(content="apague x e y"),
        AIMessage(
            content="", tool_calls=[{"name": "file_write", "args": {}, "id": "1"}]
        ),
        ToolMessage(content="ok", name="file_write", tool_call_id="1"),
    ]
    assert _dynamic_hitl_when(_req("file_write", "plan", messages=ja_passou)) is False


def test_modo_desconhecido_cai_no_mais_restritivo():
    # Erro/borda: modo inesperado → trata como "ask" (interrompe).
    assert _dynamic_hitl_when(_req("file_write", "modo-invalido")) is True


def test_runtime_ausente_cai_em_ask():
    # Erro/borda: sem runtime/context (tool fora do grafo) → "ask" (interrompe),
    # nunca "auto" silencioso — falha para o lado seguro.
    assert _dynamic_hitl_when(_req("file_write", mode=None)) is True


def test_tool_nao_destrutiva_nunca_interrompe():
    # Borda: uma tool fora de _REQUIRE_APPROVAL não pausa em nenhum modo.
    assert _dynamic_hitl_when(_req("web_search", "ask")) is False


# ── _plan_mode_should_interrupt isolado (reuso pelo modo plan) ───────────────


def test_plan_predicate_reseta_em_novo_turno_humano():
    messages = [
        HumanMessage(content="apague x"),
        AIMessage(
            content="", tool_calls=[{"name": "file_write", "args": {}, "id": "1"}]
        ),
        ToolMessage(content="ok", name="file_write", tool_call_id="1"),
        HumanMessage(content="agora apague y"),
    ]
    assert _plan_mode_should_interrupt(_req("file_write", "plan", messages)) is True


# ── _mode_should_interrupt (política pura, sem runtime) ──────────────────────


def test_mode_should_interrupt_cobre_os_5_modos():
    req = _req("file_write", "ask")
    assert _mode_should_interrupt("ask", "file_write", req) is True
    assert _mode_should_interrupt("accept_edits", "file_write", req) is False
    assert _mode_should_interrupt("accept_edits", "terminal", req) is True
    assert _mode_should_interrupt("auto", "file_write", req) is False
    assert _mode_should_interrupt("bypass", "terminal", req) is False


# ── Stack: um único middleware dinâmico, para qualquer modo ──────────────────


def test_build_middleware_stack_tem_um_hitl_dinamico():
    stack = build_middleware_stack()
    assert len(stack) == 1


# ── E2E: o grafo real gateia por runtime.context.permission_mode ─────────────
#
# HITL é ponto crítico — não basta testar o predicate isolado; o contrato só é
# real se, no grafo compilado (create_deep_agent + build_middleware_stack), o
# MESMO grafo interromper em "ask" e NÃO interromper em "auto" conforme o
# `context` passado por request. Reconstrução pelos testes (§18): este teste
# sozinho descreve o comportamento observável do HITL dinâmico ponta a ponta.


def _build_hitl_agent():
    from collections.abc import AsyncIterator

    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import (
        ChatGeneration,
        ChatGenerationChunk,
        ChatResult,
    )
    from langchain_core.tools import tool
    from langgraph.checkpoint.memory import InMemorySaver

    from backend.vtypes.context import VectoraContext

    @tool
    def file_write(path: str, content: str) -> str:
        """Escreve um arquivo (dummy de teste)."""
        return f"escrito {path}"

    class FakeToolCallingModel(BaseChatModel):
        model_config = {"arbitrary_types_allowed": True}

        @property
        def _llm_type(self) -> str:
            return "fake-tc"

        def bind_tools(self, tools, **kwargs):
            return self

        def _next(self, messages) -> AIMessage:
            has_tool = any(getattr(m, "type", "") == "tool" for m in messages)
            if not has_tool:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "file_write",
                            "args": {"path": "/x.txt", "content": "oi"},
                            "id": "call_1",
                        }
                    ],
                )
            return AIMessage(content="feito")

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            return ChatResult(
                generations=[ChatGeneration(message=self._next(messages))]
            )

        async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
            return ChatResult(
                generations=[ChatGeneration(message=self._next(messages))]
            )

        async def _astream(
            self, messages, stop=None, run_manager=None, **kwargs
        ) -> AsyncIterator[ChatGenerationChunk]:
            yield ChatGenerationChunk(message=self._next(messages))  # type: ignore[arg-type]

    from deepagents import create_deep_agent

    return create_deep_agent(
        FakeToolCallingModel(),
        tools=[file_write],
        system_prompt="teste",
        middleware=build_middleware_stack(),
        context_schema=VectoraContext,
        checkpointer=InMemorySaver(),
    )


async def _interrupted(agent, mode: str) -> bool:
    from langgraph.errors import GraphInterrupt

    config = {"configurable": {"thread_id": f"t-{mode}", "permission_mode": mode}}
    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "escreva"}]},
            config=config,
            context={"permission_mode": mode},
        )
    except GraphInterrupt:
        return True
    return "__interrupt__" in result


import pytest


@pytest.mark.asyncio
async def test_grafo_real_interrompe_em_ask_e_nao_em_auto():
    agent = _build_hitl_agent()
    # ask (manual): a tool destrutiva pausa aguardando aprovação.
    assert await _interrupted(agent, "ask") is True
    # auto (automático): o MESMO grafo roda sem pausa.
    assert await _interrupted(agent, "auto") is False
