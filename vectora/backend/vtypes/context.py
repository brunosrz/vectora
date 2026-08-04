"""Context de execução do agente Vectora (runtime, imutável por turno).

``VectoraContext`` é o ``context_schema`` passado a ``create_deep_agent``.
O LangGraph popula os campos automaticamente a partir de ``configurable``
(chaves com o mesmo nome) no início de cada run.

Isso substitui o padrão artesanal ``config["configurable"]["user_id"]``
presente nas tools — as tools podem acessar ``runtime.context.user_id``
de forma tipada via ``ToolRuntime[VectoraContext]``.

Tools que ainda não recebem ``runtime: ToolRuntime[VectoraContext]`` por
injeção automática continuam lendo ``configurable`` diretamente; o helper
``ctx_from_config`` constrói o mesmo ``VectoraContext`` a partir desse dict
para quem precisa da forma tipada sem a injeção do LangGraph.

Campos intencionalmente simples (str/None) para compatibilidade com o
serializer de ``configurable`` do LangGraph (não aceita tipos complexos).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VectoraContext:
    """Contexto imutável de run injetado pelo LangGraph em todas as tools.

    Campos populados a partir de ``configurable`` no request de cada turno.
    Todos os campos são opcionais para compatibilidade retroativa com requests
    que não incluem algum campo no ``configurable``.
    """

    user_id: str = "local"
    """ID do usuário autenticado. 'local' em modo CLI/anônimo."""

    workspace_id: str = ""
    """ID do workspace ativo na sessão."""

    permission_mode: str = "ask"
    """Modo de permissão: 'ask' | 'accept_edits' | 'auto' | 'bypass' | 'plan'."""

    org_id: str = ""
    """ID da organização (multi-tenant). Vazio em modo single-user."""

    locale: str = ""
    """Locale do usuário (ex: 'pt_BR', 'en_US'). Vazio se não detectado."""

    model: str = ""
    """Provider:model ativo (ex: 'anthropic:claude-sonnet-4-6'). Vazio se padrão."""

    thread_id: str = ""
    """ID da thread/conversa corrente."""

    # Campos extras reservados para futuras extensões
    _extra: dict = field(default_factory=dict, repr=False, compare=False)


def ctx_from_config(config: dict | None) -> VectoraContext:
    """Cria VectoraContext a partir de um RunnableConfig (fallback legado).

    Usado em tools que ainda não recebem ``runtime: ToolRuntime[VectoraContext]``
    via injeção automática do LangGraph. Permite migração gradual sem quebrar
    tools existentes.

    Args:
        config: RunnableConfig dict. Aceita ``None`` (retorna context padrão).

    Returns:
        ``VectoraContext`` com campos populados do ``configurable``, ou defaults.
    """
    c = (config or {}).get("configurable") or {}
    return VectoraContext(
        user_id=str(c.get("user_id") or "local"),
        workspace_id=str(c.get("workspace_id") or ""),
        permission_mode=str(c.get("permission_mode") or "ask"),
        org_id=str(c.get("org_id") or ""),
        locale=str(c.get("language") or c.get("locale") or ""),
        model=str(c.get("model") or ""),
        thread_id=str(c.get("thread_id") or ""),
    )
