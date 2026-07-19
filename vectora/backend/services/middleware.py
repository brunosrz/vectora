"""Middleware stack canônico do Vectora (deepagents/langchain AgentMiddleware).

Monta e expõe o conjunto de middlewares usados em ``create_deep_agent``.
Cada middleware é lazy-importado para evitar carregamento desnecessário em
contextos que não instanciam o grafo (CLI, testes unitários).

HITL dinâmico (por request, não por compilação):
    Um único ``HumanInTheLoopMiddleware`` cobre todas as tools destrutivas.
    O predicate ``when=_dynamic_hitl_when`` lê ``runtime.context.permission_mode``
    (``VectoraContext``, populado do ``configurable`` por request via
    ``ctx_from_config`` no handler de chat) e aplica a política do modo em tempo
    de execução. Assim o MESMO grafo compilado atende os 5 modos — trocar o modo
    no meio da sessão passa a valer no turno seguinte sem recompilar.

Middlewares disponíveis em deepagents (usados aqui):
    - ``SummarizationMiddleware`` — adicionado incondicionalmente pelo
      ``create_deep_agent`` (não duplicar aqui).
    - ``HumanInTheLoopMiddleware`` — pausa tools destrutivas para aprovação.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from langchain.agents.middleware.human_in_the_loop import (
        DecisionType,  # type: ignore[import-untyped]
    )
    from langchain.agents.middleware.types import ToolCallRequest

# ---------------------------------------------------------------------------
# HITL: política canônica por permission_mode
# ---------------------------------------------------------------------------

#: Tools destrutivas candidatas a pausar o grafo para aprovação.
_REQUIRE_APPROVAL: frozenset[str] = frozenset(
    {"terminal", "terminal_tool", "file_write", "file_write_tool"}
)

#: Tools auto-aprovadas no modo "accept_edits" (edições de arquivo passam sem
#: pausa; só o terminal interrompe).
_ACCEPT_EDITS_AUTO: frozenset[str] = frozenset({"file_write", "file_write_tool"})

#: Modos que NUNCA interrompem (rodam autônomos). ``auto`` e ``bypass`` têm o
#: mesmo comportamento no grafo (sem pausa); a diferença é de UX/observabilidade
#: no frontend (banner "automático" vs "permissões ignoradas"), não de HITL.
_NON_INTERRUPTING_MODES: frozenset[str] = frozenset({"auto", "bypass"})

#: Decisions permitidas no interrupt (todas — o predicate decide SE pausa; uma
#: vez pausado, o revisor tem o leque completo de ações).
_ALL_DECISIONS: list[DecisionType] = cast(  # type: ignore[assignment]
    "list[DecisionType]", ["approve", "edit", "reject", "respond"]
)


def _plan_mode_should_interrupt(req: ToolCallRequest) -> bool:
    """Predicate do modo ``"plan"``: interrompe só a 1ª tool destrutiva do turno.

    Diferente de ``"ask"`` (interrompe TODA tool destrutiva, em toda rodada de
    tool-calling), o modo plan pausa uma vez só por turno — depois de aprovada,
    as tools destrutivas seguintes na MESMA resposta ao usuário (mesmo turno)
    rodam sem pausas novas. Detecta "turno atual" varrendo ``state["messages"]``
    de trás pra frente até a última ``HumanMessage``: se já existe um
    ``ToolMessage`` de uma tool destrutiva DEPOIS dela, o gate já foi passado
    neste turno — não interrompe de novo.
    """
    from langchain_core.messages import HumanMessage, ToolMessage

    state = req.state
    messages = state.get("messages", []) if isinstance(state, dict) else []

    last_human_idx = -1
    for idx, msg in enumerate(messages):
        if isinstance(msg, HumanMessage):
            last_human_idx = idx

    for msg in messages[last_human_idx + 1 :]:
        if isinstance(msg, ToolMessage) and msg.name in _REQUIRE_APPROVAL:
            return False  # gate já passado neste turno — segue sem novo interrupt

    return True  # primeira tool destrutiva do turno — pausa pra aprovação


def _mode_should_interrupt(mode: str, tool_name: str, req: ToolCallRequest) -> bool:
    """Política canônica dos 5 modos — fonte única de verdade do HITL.

    - ``ask`` (manual): interrompe TODA tool destrutiva, em toda rodada.
    - ``accept_edits`` (aceitar permissões): auto-aprova edições de arquivo;
      só ``terminal`` interrompe.
    - ``plan`` (plano): interrompe só a 1ª tool destrutiva do turno
      (``_plan_mode_should_interrupt``) — aprovado uma vez, o resto do turno
      roda sem novas pausas.
    - ``auto`` (automático) / ``bypass`` (ignorar permissões): nunca interrompe.

    ``tool_name`` fora de ``_REQUIRE_APPROVAL`` nunca interrompe (o interrupt_on
    já restringe as tools cobertas, mas a checagem torna a função correta se
    chamada isolada).
    """
    if tool_name not in _REQUIRE_APPROVAL:
        return False
    if mode in _NON_INTERRUPTING_MODES:
        return False
    if mode == "accept_edits":
        return tool_name not in _ACCEPT_EDITS_AUTO
    if mode == "plan":
        return _plan_mode_should_interrupt(req)
    return True  # "ask" ou desconhecido → mais restritivo


def _mode_from_runtime(req: ToolCallRequest) -> str:
    """Extrai ``permission_mode`` do ``runtime.context`` (VectoraContext).

    Defensivo: se o runtime/context não estiver disponível (ex.: tool invocada
    fora do grafo), cai em ``"ask"`` — o modo mais restritivo.
    """
    runtime = getattr(req, "runtime", None)
    context = getattr(runtime, "context", None)
    mode = getattr(context, "permission_mode", "") if context is not None else ""
    return mode or "ask"


def _dynamic_hitl_when(req: ToolCallRequest) -> bool:
    """Predicate único do HITL dinâmico: lê o modo do runtime e aplica a política.

    Chamado pelo ``HumanInTheLoopMiddleware`` para cada tool call destrutiva.
    Lê ``permission_mode`` do ``runtime.context`` (por request) em vez de depender
    de um grafo compilado por modo.
    """
    tool_call = getattr(req, "tool_call", {}) or {}
    tool_name = tool_call.get("name", "") if isinstance(tool_call, dict) else ""
    mode = _mode_from_runtime(req)
    return _mode_should_interrupt(mode, tool_name, req)


def build_middleware_stack() -> list[Any]:
    """Monta o stack de middleware para ``create_deep_agent(middleware=...)``.

    Um único ``HumanInTheLoopMiddleware`` cobre todas as tools de
    ``_REQUIRE_APPROVAL`` com o predicate dinâmico ``_dynamic_hitl_when``, que lê
    o ``permission_mode`` do ``runtime.context`` em tempo de execução. O grafo
    compilado é o mesmo para todos os modos — a decisão de pausar acontece por
    request.

    Returns:
        Lista de ``AgentMiddleware`` prontos para passar ao ``create_deep_agent``.

    Nota: ``create_deep_agent`` já adiciona um ``SummarizationMiddleware`` ao
    stack base incondicionalmente — adicionar outro aqui causa
    ``AssertionError: Please remove duplicate middleware instances``.
    """
    from deepagents.middleware.subagents import (
        HumanInTheLoopMiddleware,  # type: ignore[attr-defined]
        InterruptOnConfig,  # type: ignore[attr-defined]
    )

    # ``dict[str, Any]`` porque ``HumanInTheLoopMiddleware`` aceita
    # ``dict[str, bool | InterruptOnConfig]`` (dict é invariante no valor).
    interrupt_on: dict[str, Any] = {
        name: InterruptOnConfig(
            allowed_decisions=_ALL_DECISIONS, when=_dynamic_hitl_when
        )
        for name in _REQUIRE_APPROVAL
    }
    stack: list[Any] = [HumanInTheLoopMiddleware(interrupt_on=interrupt_on)]

    logger.debug(
        "middleware: stack montado (HITL dinâmico) → %d middlewares", len(stack)
    )
    return stack
