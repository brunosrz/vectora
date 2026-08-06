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
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from backend.services.middleware import (
    _REQUIRE_APPROVAL,
    _dynamic_hitl_when,
    _mode_should_interrupt,
    _plan_mode_should_interrupt,
    build_middleware_stack,
)


def _req(
    tool_name: str = "file_write",
    mode: str | None = "ask",
    messages: list | None = None,
    workspace_id: str = "ws-1",
    args: dict | None = None,
    background_task_id: str = "",
) -> ToolCallRequest:
    """Request com ``runtime.context.permission_mode`` — como o grafo entrega.

    ``mode=None`` simula runtime/context ausente (tool fora do grafo).
    """
    runtime = None
    if mode is not None:
        runtime = SimpleNamespace(
            context=SimpleNamespace(
                permission_mode=mode,
                workspace_id=workspace_id,
                background_task_id=background_task_id,
            )
        )
    return ToolCallRequest(
        tool_call={"name": tool_name, "args": args or {}, "id": "x"},
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


def test_file_edit_pausa_como_file_write_em_todos_os_modos():
    """Achado da auditoria: file_edit ficava fora de _REQUIRE_APPROVAL — uma
    tool tão destrutiva quanto file_write (sobrescreve trecho existente)
    passava livre em qualquer modo que exigisse aprovação pra escrever."""
    assert _dynamic_hitl_when(_req("file_edit", "ask")) is True
    assert _dynamic_hitl_when(_req("file_edit", "accept_edits")) is False
    for mode in ("auto", "bypass"):
        assert _dynamic_hitl_when(_req("file_edit", mode)) is False


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


def test_install_learned_skill_pausa_como_terminal_file_write():
    # Remember: gravar skill aprendida exige a mesma aprovação HITL de
    # terminal/file_write — nunca persiste silenciosamente.
    assert _dynamic_hitl_when(_req("install_learned_skill", "ask")) is True
    assert _dynamic_hitl_when(_req("install_learned_skill", "auto")) is False


# ── Kanban: kanban_create/kanban_update_status exigem aprovação; kanban_list não ──


def test_kanban_create_e_update_status_estao_em_require_approval():
    assert "kanban_create" in _REQUIRE_APPROVAL
    assert "kanban_update_status" in _REQUIRE_APPROVAL
    assert "kanban_list" not in _REQUIRE_APPROVAL


def test_kanban_create_pausa_em_ask_como_qualquer_mutacao():
    assert _dynamic_hitl_when(_req("kanban_create", "ask")) is True
    assert _dynamic_hitl_when(_req("kanban_create", "auto")) is False


def test_kanban_update_status_pausa_normalmente_para_outra_task():
    # Uma task em segundo plano (background_task_id="t1") mudando o status
    # de OUTRA task ("t2") continua exigindo aprovação normalmente.
    assert (
        _dynamic_hitl_when(
            _req(
                "kanban_update_status",
                "ask",
                args={"task_id": "t2", "status": "blocked"},
                background_task_id="t1",
            )
        )
        is True
    )


def test_kanban_update_status_bypassa_hitl_quando_task_se_auto_atualiza():
    # A mesma task (background_task_id == task_id do argumento) se marcando
    # bloqueada não espera aprovação de si mesma — senão vira loop.
    assert (
        _dynamic_hitl_when(
            _req(
                "kanban_update_status",
                "ask",
                args={"task_id": "t1", "status": "blocked"},
                background_task_id="t1",
            )
        )
        is False
    )


def test_kanban_update_status_fora_de_background_task_exige_aprovacao():
    # Erro/borda: chat síncrono (sem background_task_id) sempre pede
    # aprovação — o bypass só vale dentro de uma run em segundo plano.
    assert (
        _dynamic_hitl_when(
            _req(
                "kanban_update_status",
                "ask",
                args={"task_id": "t1", "status": "blocked"},
                background_task_id="",
            )
        )
        is True
    )


# ── Workspace jailada (0.8): terminal/file_write bypassam HITL redundante ────


def test_workspace_jailada_bypassa_hitl_pra_terminal_e_file_write(monkeypatch):
    import backend.services.middleware as mw

    monkeypatch.setattr(mw, "_workspace_is_jailed", lambda wid: wid == "ws-jail")

    assert _dynamic_hitl_when(_req("terminal", "ask", workspace_id="ws-jail")) is False
    assert (
        _dynamic_hitl_when(_req("file_write", "ask", workspace_id="ws-jail")) is False
    )


def test_workspace_jailada_bypassa_hitl_pra_file_edit(monkeypatch):
    import backend.services.middleware as mw

    monkeypatch.setattr(mw, "_workspace_is_jailed", lambda wid: wid == "ws-jail")

    assert _dynamic_hitl_when(_req("file_edit", "ask", workspace_id="ws-jail")) is False


def test_workspace_nao_jailada_mantem_hitl_normal(monkeypatch):
    import backend.services.middleware as mw

    monkeypatch.setattr(mw, "_workspace_is_jailed", lambda wid: False)

    assert _dynamic_hitl_when(_req("terminal", "ask", workspace_id="ws-1")) is True


def test_bypass_nao_afeta_tools_fora_do_escopo_do_jail(monkeypatch):
    # install_learned_skill não é terminal/file_write — jail não bypassa,
    # continua exigindo aprovação normal mesmo em workspace sandboxada.
    import backend.services.middleware as mw

    monkeypatch.setattr(mw, "_workspace_is_jailed", lambda wid: True)

    assert (
        _dynamic_hitl_when(_req("install_learned_skill", "ask", workspace_id="ws-jail"))
        is True
    )


def test_workspace_is_jailed_le_vectora_toml_da_workspace(tmp_path, monkeypatch):
    from backend.services.middleware import _workspace_is_jailed

    (tmp_path / "vectora.toml").write_text("[sandbox]\nenabled = true\n")
    ws = SimpleNamespace(cwd=str(tmp_path))
    monkeypatch.setattr(
        "backend.workspace.workspace.workspace_registry.get", lambda wid: ws
    )

    assert _workspace_is_jailed("ws-1") is True


def test_workspace_is_jailed_falso_sem_vectora_toml(tmp_path, monkeypatch):
    from backend.services.middleware import _workspace_is_jailed

    ws = SimpleNamespace(cwd=str(tmp_path))
    monkeypatch.setattr(
        "backend.workspace.workspace.workspace_registry.get", lambda wid: ws
    )

    assert _workspace_is_jailed("ws-1") is False


def test_workspace_is_jailed_falso_workspace_desconhecida(monkeypatch):
    from backend.services.middleware import _workspace_is_jailed

    monkeypatch.setattr(
        "backend.workspace.workspace.workspace_registry.get", lambda wid: None
    )

    assert _workspace_is_jailed("ws-inexistente") is False


def test_workspace_is_jailed_falso_workspace_id_vazio():
    from backend.services.middleware import _workspace_is_jailed

    assert _workspace_is_jailed("") is False


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
            next_message = self._next(messages)
            yield ChatGenerationChunk(
                message=AIMessageChunk(**next_message.model_dump())
            )

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


# ── Regressão: HITL propagado pra dentro de uma delegação via task() ────────
#
# Achado real (não hipotético): SubAgent specs do deepagents só herdam o
# `interrupt_on` TOP-LEVEL de `create_deep_agent` — nunca setado pelo
# Vectora — e não o `middleware=` custom do agente pai. Sem passar
# `middleware=middleware` em cada spec (agent_factory._subagent_specs),
# `file_write`/`terminal` chamados DENTRO de um `task()` nunca pausavam pra
# aprovação, mesmo em permission_mode="ask". Este teste prova a lacuna
# fechada, não só a ausência dela — GraphInterrupt tem que vir de dentro do
# subgrafo delegado, não do agente principal.


def _build_hitl_agent_with_subagent():
    from collections.abc import AsyncIterator

    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
    from langchain_core.tools import tool
    from langgraph.checkpoint.memory import InMemorySaver

    from backend.vtypes.context import VectoraContext

    _DELEGATE_MARKER = "delegate-then-write"

    @tool
    def file_write(path: str, content: str) -> str:
        """Escreve um arquivo (dummy de teste)."""
        return f"escrito {path}"

    class FakeModel(BaseChatModel):
        """Um único fake serve tanto o orquestrador quanto o subagent —
        decide pelo conteúdo das mensagens, não por qual grafo o invoca
        (mesma reutilização de modelo que agent_factory faz de verdade)."""

        model_config = {"arbitrary_types_allowed": True}

        @property
        def _llm_type(self) -> str:
            return "fake-tc-delegating"

        def bind_tools(self, tools, **kwargs):
            return self

        def _next(self, messages) -> AIMessage:
            has_tool_result = any(getattr(m, "type", "") == "tool" for m in messages)
            if has_tool_result:
                return AIMessage(content="feito")

            is_inside_subagent = any(
                _DELEGATE_MARKER in str(getattr(m, "content", "")) for m in messages
            )
            if is_inside_subagent:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "file_write",
                            "args": {"path": "/x.txt", "content": "oi"},
                            "id": "call_write",
                        }
                    ],
                )
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "task",
                        "args": {
                            "subagent_type": "writer",
                            "description": _DELEGATE_MARKER,
                        },
                        "id": "call_task",
                    }
                ],
            )

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
            next_message = self._next(messages)
            yield ChatGenerationChunk(
                message=AIMessageChunk(**next_message.model_dump())
            )

    from deepagents import create_deep_agent

    middleware = build_middleware_stack()
    model = FakeModel()

    return create_deep_agent(
        model,
        tools=[],
        system_prompt="orquestrador de teste",
        subagents=[
            {
                "name": "writer",
                "description": "escreve arquivos",
                "system_prompt": "subagent de teste",
                "tools": [file_write],
                "middleware": middleware,
            }
        ],
        middleware=middleware,
        context_schema=VectoraContext,
        checkpointer=InMemorySaver(),
    )


@pytest.mark.asyncio
async def test_subagent_com_middleware_propagado_interrompe_em_ask():
    agent = _build_hitl_agent_with_subagent()
    # Sem middleware propagado (bug original), isso nunca interrompia: a
    # delegação via task() concluía o file_write direto, sem pausa.
    assert await _interrupted(agent, "ask") is True
    assert await _interrupted(agent, "auto") is False
