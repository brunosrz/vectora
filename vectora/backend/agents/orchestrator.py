"""Contexto de sessão do orchestrator (deep-agent).

Fornece o carregamento do contexto de projeto/workspace injetado no system
prompt do agente principal: arquivos de instrução (AGENTS.md/CLAUDE.md/…) do cwd
e o MANIFEST.md do workspace ativo.

``_load_session_context`` é consumido por
``agent_factory._build_session_system_prompt``.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_project_docs() -> str | None:
    """Carrega arquivos de instrução do projeto e contexto do .vectora/.

    Coleta (em ordem de prioridade por weight):
    1. Arquivos de instrução na raiz: AGENTS.md, CLAUDE.md, GEMINI.md, VECTORA.md, …
    2. Todos os .md em .vectora/ com enabled=true (exceto MANIFEST.md e subpastas reservadas)

    Frontmatter YAML/Paperclip é parseado — campos weight, inject_when, enabled,
    truncate_at, title, description e tags são respeitados. Arquivos com
    inject_when='on_request' são omitidos do system prompt (disponíveis via tool).

    Retorna conteúdo formatado ou None se não encontrar nada.
    """
    from backend.services.context_files import (
        collect_context_files,
        format_context_files_for_prompt,
    )

    cwd = Path.cwd()
    files = collect_context_files(str(cwd))
    if not files:
        return None

    text = format_context_files_for_prompt(files, include_on_request=False)
    return text or None


def _load_workspaces_overview(active_id: str | None = None) -> str | None:
    """Lista os workspaces registrados para o Vectora ter consciência deles.

    O Vectora gerencia projetos isolados por diretório (workspaces). Injetar a
    lista no system prompt dá conhecimento proativo — o agente sabe quais
    projetos conhece sem precisar chamar `workspace_list`, e pode sugerir trocar
    de workspace quando a pergunta for sobre outro projeto.

    Retorna None se não houver nenhum workspace registrado.
    """
    try:
        from backend.services.workspace import workspace_registry

        workspaces = workspace_registry.list_all()
    except Exception:
        logger.debug("Falha ao listar workspaces para o contexto", exc_info=True)
        return None

    if not workspaces:
        return None

    lines: list[str] = [
        "## Seus Workspaces",
        "",
        "Você gerencia estes projetos isolados (cada um com diretório, base RAG e "
        "MANIFEST.md próprios). O marcado com ◀ é o ativo desta sessão:",
        "",
    ]
    # Limita a 30 entradas para não inflar o contexto; o restante via `workspace_list`.
    for ws in workspaces[:30]:
        marker = " ◀ ativo" if active_id and ws.id == active_id else ""
        git = " · git" if getattr(ws, "is_git_repo", False) else ""
        lines.append(f"- **{ws.name}** (`{ws.id}`) — `{ws.cwd}`{git}{marker}")
    if len(workspaces) > 30:
        lines.append(f"- … e mais {len(workspaces) - 30} (use `workspace_list`).")
    lines.append(
        "\nUse `workspace_describe`/`bucket_summary` para detalhes de um workspace "
        "e `vector_search` para buscar no conhecimento indexado do ativo."
    )
    return "\n".join(lines)


def _load_session_context(workspace_id: str | None = None) -> str | None:
    """Carrega contexto completo da sessão: arquivos de projeto + manifest do workspace.

    Seções:
    1. AGENTS.md / CLAUDE.md / VECTORA.md / GEMINI.md — instrução do projeto
    2. Lista de workspaces registrados (consciência dos projetos do Vectora)
    3. MANIFEST.md do workspace ativo — base de conhecimento indexada

    O manifest é truncado a ~3200 chars para não inflar o contexto. Detalhes
    por bucket ficam disponíveis via `bucket_summary` (tool sob demanda).
    """
    parts: list[str] = []

    project_docs = _load_project_docs()
    if project_docs:
        parts.append(project_docs)

    workspaces_overview = _load_workspaces_overview(workspace_id)
    if workspaces_overview:
        parts.append(workspaces_overview)

    if workspace_id:
        try:
            from backend.services.workspace import workspace_registry

            ws = workspace_registry.get(workspace_id)
            if ws is not None:
                manifest_path = ws.manifest_path()
                if manifest_path.exists():
                    raw_manifest = manifest_path.read_text(
                        encoding="utf-8", errors="ignore"
                    ).strip()
                    from backend.services.context_files import parse_frontmatter

                    _, manifest = parse_frontmatter(raw_manifest)
                    manifest = manifest.strip()
                    # Trunca a ~3200 chars (~800 tokens) para economizar contexto
                    if len(manifest) > 3200:
                        manifest = manifest[:3200] + "\n\n[... manifest truncado ...]"
                    workspace_block = (
                        f"## Workspace Ativo: {ws.name} ({ws.id})\n\n"
                        f"{manifest}\n\n"
                        "Ferramentas disponíveis para este workspace:\n"
                        "- `vector_search` — busca semântica filtrada para este workspace\n"
                        "- `workspace_describe`, `bucket_summary` — detalhes do manifest\n"
                        "- `get_memory` — memórias episódicas (consulte quando perguntarem "
                        "sobre preferências ou decisões anteriores)"
                    )
                    parts.append(workspace_block)
        except Exception:
            logger.debug(
                "Falha ao carregar manifest do workspace %s",
                workspace_id,
                exc_info=True,
            )

    return "\n\n---\n\n".join(parts) if parts else None


# Alias para compatibilidade com código que importa _load_project_context.
_load_project_context = _load_project_docs
