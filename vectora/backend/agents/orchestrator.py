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
    """Escaneia cwd recursivamente por AGENTS.md, CLAUDE.md, VECTORA.md, GEMINI.md.

    Usa ``iter_files`` (varredura com poda de node_modules/.venv/etc. e
    respeito ao .gitignore) em vez de ``rglob`` puro — em repositórios JS
    grandes o rglob varria centenas de milhares de entradas e congelava o
    primeiro turno do agente (e a suite de testes) por minutos.

    Retorna conteúdo concatenado com cabeçalho por arquivo, ou None se não
    encontrar nada. Limita cada arquivo a 4000 chars e a busca a 10 arquivos
    por nome para não inflar o contexto.
    """
    from backend.services.ignore import iter_files, load_ignore_spec

    targets = ["AGENTS.md", "CLAUDE.md", "VECTORA.md", "GEMINI.md"]
    cwd = Path.cwd()
    spec = load_ignore_spec(cwd)
    sections: list[str] = []

    for name in targets:
        for found in iter_files(cwd, name, spec)[:10]:
            try:
                text = found.read_text(encoding="utf-8", errors="ignore").strip()
                if text:
                    rel = found.relative_to(cwd)
                    sections.append(f"## {name} ({rel})\n\n{text[:4000]}")
            except Exception:
                pass

    return "\n\n---\n\n".join(sections) if sections else None


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
                    manifest = manifest_path.read_text(
                        encoding="utf-8", errors="ignore"
                    ).strip()
                    # Remove frontmatter YAML se presente (--- ... ---)
                    if manifest.startswith("---"):
                        end = manifest.find("---", 3)
                        if end != -1:
                            manifest = manifest[end + 3 :].strip()
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
