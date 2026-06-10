"""Middleware stack canônico do Vectora (deepagents/langchain AgentMiddleware).

Monta e expõe o conjunto de middlewares usados em ``create_deep_agent``.
Cada middleware é lazy-importado para evitar carregamento desnecessário em
contextos que não instanciam o grafo (CLI, testes unitários).

Middlewares disponíveis em deepagents (usados aqui):
    - ``SummarizationMiddleware`` — comprime contexto quando próximo do limite
    - ``HumanInTheLoopMiddleware`` — pausa execução de tools para aprovação humana

Middlewares do plano sem suporte nativo em deepagents (TODO quando disponíveis):
    - ``ModelCallLimitMiddleware`` — limita chamadas de modelo por turno
    - ``ToolCallLimitMiddleware`` — limita chamadas de tool por turno
    - ``ModelRetryMiddleware`` — retry em falhas do modelo
    - ``ModelFallbackMiddleware`` — fallback para LLM backup
    - ``ToolRetryMiddleware`` — retry em falhas de tool
    - ``ContextEditingMiddleware`` — edição de contexto (sobreposição por E.B-5)

Quando ``create_deep_agent`` recebe ``interrupt_on``, ele usa HITL compile-time.
Esta abordagem funciona bem para o singleton compartilhado (todos os usuários
têm o mesmo gráfico); quando E.B-5 introduzir ``context_schema=VectoraContext``,
o ``_dynamic_hitl_when`` lerá ``runtime.context.permission_mode`` em tempo real
e o ``interrupt_on`` estático poderá ser substituído por lógica dinâmica.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from langchain.agents.middleware.human_in_the_loop import (
        DecisionType,  # type: ignore[import-untyped]
    )

# ---------------------------------------------------------------------------
# HITL: mapeamento permission_mode → interrupt_on
# ---------------------------------------------------------------------------

#: Tools destrutivas que pausam o grafo para aprovação.
_REQUIRE_APPROVAL: frozenset[str] = frozenset(
    {"terminal", "terminal_tool", "file_write", "file_write_tool"}
)

#: Tools auto-aprovadas no modo "accept_edits".
_ACCEPT_EDITS_AUTO: frozenset[str] = frozenset({"file_write", "file_write_tool"})

#: Decisions permitidas no modo "ask" (todas).
_ALL_DECISIONS: list[DecisionType] = cast(  # type: ignore[assignment]
    "list[DecisionType]", ["approve", "edit", "reject", "respond"]
)

#: Decisions permitidas no modo "accept_edits" (sem reject).
_EDITS_DECISIONS: list[DecisionType] = cast(  # type: ignore[assignment]
    "list[DecisionType]", ["approve", "edit", "respond"]
)


def _interrupt_on_for_mode(permission_mode: str) -> dict[str, Any]:
    """Retorna o dict ``interrupt_on`` canônico para o modo de permissão.

    ``permission_mode`` → ``interrupt_on`` dict:

    - ``"bypass"`` / ``"auto"`` → ``{}`` (sem pausas)
    - ``"accept_edits"``        → só terminal interrompe (approve/edit/respond)
    - ``"ask"`` / ``"plan"``    → todas as tools destrutivas interrompem (all decisions)

    O dict retornado é passado diretamente a ``HumanInTheLoopMiddleware`` ou
    ao parâmetro ``interrupt_on`` de ``create_deep_agent``.
    """
    from deepagents.middleware.subagents import (
        InterruptOnConfig,  # type: ignore[attr-defined]
    )

    match permission_mode:
        case "bypass" | "auto":
            return {}
        case "accept_edits":
            # Só terminal interrupts (file_write é auto-aprovado neste modo)
            return {
                name: InterruptOnConfig(allowed_decisions=_EDITS_DECISIONS)
                for name in (_REQUIRE_APPROVAL - _ACCEPT_EDITS_AUTO)
            }
        case _:  # "ask", "plan" ou desconhecido → mais restritivo
            return {
                name: InterruptOnConfig(allowed_decisions=_ALL_DECISIONS)
                for name in _REQUIRE_APPROVAL
            }


def _hitl_middleware(permission_mode: str) -> Any | None:
    """Constrói ``HumanInTheLoopMiddleware`` para o modo de permissão dado.

    Retorna ``None`` quando o modo não requer HITL (bypass/auto), evitando
    adicionar middleware desnecessário ao stack.

    Centraliza o mapeamento ``permission_mode → HumanInTheLoopMiddleware``.
    """
    interrupt_on = _interrupt_on_for_mode(permission_mode)
    if not interrupt_on:
        return None

    from deepagents.middleware.subagents import (
        HumanInTheLoopMiddleware,  # type: ignore[attr-defined]
    )

    return HumanInTheLoopMiddleware(interrupt_on=interrupt_on)


# ---------------------------------------------------------------------------
# Sumarização: compressão de contexto
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Stack completo
# ---------------------------------------------------------------------------


def build_middleware_stack(permission_mode: str = "ask") -> list[Any]:
    """Monta o stack de middleware para ``create_deep_agent(middleware=...)``.

    Args:
        permission_mode: Modo de permissão da sessão ("ask", "accept_edits",
            "auto", "bypass", "plan"). Determina o HITL behavior.

    Returns:
        Lista de ``AgentMiddleware`` prontos para passar ao ``create_deep_agent``.

    Nota: o singleton do factory usa ``permission_mode="ask"`` como padrão
    (mais restritivo). Quando E.B-5 introduzir ``context_schema=VectoraContext``,
    o middleware poderá ler o mode dinamicamente via ``runtime.context``.
    """
    stack: list[Any] = []

    # HITL (pausa ferramentas destrutivas para aprovação humana). Note que
    # ``create_deep_agent`` já adiciona um ``SummarizationMiddleware`` ao
    # stack base incondicionalmente — adicionar outro aqui causa
    # ``AssertionError: Please remove duplicate middleware instances``.
    hitl = _hitl_middleware(permission_mode)
    if hitl is not None:
        stack.append(hitl)

    logger.debug(
        "middleware: stack montado para mode=%s → %d middlewares",
        permission_mode,
        len(stack),
    )
    return stack
