"""GitHub CLI tools — operações via `gh` CLI.

G3 — Bloco G: gh_pr_list, gh_pr_create, gh_pr_view, gh_pr_merge,
               gh_issue_list, gh_issue_create, gh_issue_view, gh_issue_comment.

Todas as tools:
- Executam o binário `gh` via subprocess (sem imports do SDK GitHub).
- Retornam JSON estruturado compatível com os render_hints declarados.
- _gh_run() é o helper central: captura stdout/stderr e converte em dict.
- Fallback gracioso quando `gh` não está no PATH.

Requisito de sistema: `gh` CLI instalado e autenticado (`gh auth login`).
"""

from __future__ import annotations

import json
import logging
import subprocess  # nosec B404
from typing import Annotated

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper central
# ---------------------------------------------------------------------------


def _gh_run(
    args: list[str],
    cwd: str | None = None,
    input_data: str | None = None,
) -> dict:
    """Executa `gh <args>` e retorna dict com status + dados.

    - Sucesso: {"status": "ok", "output": "<stdout>"}
    - Erro de processo: {"status": "error", "message": "<stderr>", "code": <int>}
    - gh não encontrado: {"status": "error", "message": "gh not found in PATH"}
    """
    cmd = ["gh", *args]
    try:
        result = subprocess.run(  # noqa: S603  # nosec B603
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            input=input_data,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "gh not found in PATH — install the GitHub CLI: https://cli.github.com",
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "gh command timed out after 30s"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    if result.returncode != 0:
        return {
            "status": "error",
            "message": result.stderr.strip() or result.stdout.strip(),
            "code": result.returncode,
        }

    return {"status": "ok", "output": result.stdout.strip()}


def _resolve_cwd(workspace_id: str | None, config: RunnableConfig | None) -> str | None:
    """Resolve workspace → cwd para passar ao subprocess gh."""
    from vectora.services.workspace import workspace_registry

    wid = workspace_id
    if wid is None and config is not None:
        wid = (config.get("configurable") or {}).get("workspace_id")
    ws = workspace_registry.get(wid) if wid else workspace_registry.get_or_create()
    return ws.cwd if ws else None


# ---------------------------------------------------------------------------
# @tool wrappers (G3)
# ---------------------------------------------------------------------------


@tool(
    extras={
        "render_hint": "table",
        "category": "git",
        "destructive": False,
        "icon": "git-pull-request",
    }
)
async def gh_pr_list(
    state: str = "open",
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lista pull requests do repositório.

    Args:
        state: "open" | "closed" | "merged" | "all" (default: "open").
        workspace_id: ID do workspace.
    """
    cwd = _resolve_cwd(workspace_id, config)
    result = _gh_run(
        [
            "pr",
            "list",
            "--state",
            state,
            "--json",
            "number,title,state,author,createdAt,headRefName,baseRefName",
        ],
        cwd=cwd,
    )
    if result["status"] != "ok":
        return json.dumps(result)
    try:
        prs = json.loads(result["output"])
        return json.dumps({"status": "ok", "prs": prs, "state": state})
    except json.JSONDecodeError:
        return json.dumps({"status": "ok", "output": result["output"]})


@tool(
    extras={
        "render_hint": "code_block",
        "category": "git",
        "destructive": False,
        "icon": "git-pull-request",
    }
)
async def gh_pr_create(
    title: str = "",
    body: str = "",
    base: str = "main",
    draft: bool = False,
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Cria um pull request a partir da branch atual.

    Args:
        title: Título do PR (obrigatório).
        body: Descrição do PR (suporta Markdown).
        base: Branch alvo (default: "main").
        draft: Se True, cria como rascunho.
        workspace_id: ID do workspace.
    """
    cwd = _resolve_cwd(workspace_id, config)
    if not title:
        return json.dumps({"status": "error", "message": "Título do PR é obrigatório."})
    args = ["pr", "create", "--title", title, "--body", body, "--base", base]
    if draft:
        args.append("--draft")
    result = _gh_run(args, cwd=cwd)
    return json.dumps(result)


@tool(
    extras={
        "render_hint": "code_block",
        "category": "git",
        "destructive": False,
        "icon": "git-pull-request",
    }
)
async def gh_pr_view(
    pr_number: int = 0,
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Exibe detalhes de um pull request.

    Args:
        pr_number: Número do PR.
        workspace_id: ID do workspace.
    """
    cwd = _resolve_cwd(workspace_id, config)
    if not pr_number:
        return json.dumps({"status": "error", "message": "Número do PR é obrigatório."})
    result = _gh_run(
        [
            "pr",
            "view",
            str(pr_number),
            "--json",
            "number,title,state,body,author,createdAt,files,reviews",
        ],
        cwd=cwd,
    )
    if result["status"] != "ok":
        return json.dumps(result)
    try:
        pr = json.loads(result["output"])
        return json.dumps({"status": "ok", "pr": pr})
    except json.JSONDecodeError:
        return json.dumps({"status": "ok", "output": result["output"]})


@tool(
    extras={
        "render_hint": "code_block",
        "category": "git",
        "destructive": True,
        "icon": "git-merge",
    }
)
async def gh_pr_merge(
    pr_number: int = 0,
    method: str = "squash",
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Faz merge de um pull request.

    ⚠️ Operação destrutiva — integra commits e pode fechar a branch.

    Args:
        pr_number: Número do PR.
        method: "squash" | "merge" | "rebase" (default: "squash").
        workspace_id: ID do workspace.
    """
    cwd = _resolve_cwd(workspace_id, config)
    if not pr_number:
        return json.dumps({"status": "error", "message": "Número do PR é obrigatório."})
    result = _gh_run(["pr", "merge", str(pr_number), f"--{method}", "--auto"], cwd=cwd)
    return json.dumps(result)


@tool(
    extras={
        "render_hint": "table",
        "category": "git",
        "destructive": False,
        "icon": "circle-dot",
    }
)
async def gh_issue_list(
    state: str = "open",
    labels: str = "",
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lista issues do repositório.

    Args:
        state: "open" | "closed" | "all" (default: "open").
        labels: Labels separadas por vírgula (ex: "bug,enhancement").
        workspace_id: ID do workspace.
    """
    cwd = _resolve_cwd(workspace_id, config)
    args = [
        "issue",
        "list",
        "--state",
        state,
        "--json",
        "number,title,state,author,createdAt,labels,assignees",
    ]
    if labels:
        args += ["--label", labels]
    result = _gh_run(args, cwd=cwd)
    if result["status"] != "ok":
        return json.dumps(result)
    try:
        issues = json.loads(result["output"])
        return json.dumps({"status": "ok", "issues": issues, "state": state})
    except json.JSONDecodeError:
        return json.dumps({"status": "ok", "output": result["output"]})


@tool(
    extras={
        "render_hint": "code_block",
        "category": "git",
        "destructive": False,
        "icon": "circle-plus",
    }
)
async def gh_issue_create(
    title: str = "",
    body: str = "",
    labels: str = "",
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Cria uma issue no repositório.

    Args:
        title: Título da issue (obrigatório).
        body: Descrição da issue (suporta Markdown).
        labels: Labels separadas por vírgula.
        workspace_id: ID do workspace.
    """
    cwd = _resolve_cwd(workspace_id, config)
    if not title:
        return json.dumps(
            {"status": "error", "message": "Título da issue é obrigatório."}
        )
    args = ["issue", "create", "--title", title, "--body", body]
    if labels:
        args += ["--label", labels]
    result = _gh_run(args, cwd=cwd)
    return json.dumps(result)


@tool(
    extras={
        "render_hint": "code_block",
        "category": "git",
        "destructive": False,
        "icon": "circle-dot",
    }
)
async def gh_issue_view(
    issue_number: int = 0,
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Exibe detalhes de uma issue.

    Args:
        issue_number: Número da issue.
        workspace_id: ID do workspace.
    """
    cwd = _resolve_cwd(workspace_id, config)
    if not issue_number:
        return json.dumps(
            {"status": "error", "message": "Número da issue é obrigatório."}
        )
    result = _gh_run(
        [
            "issue",
            "view",
            str(issue_number),
            "--json",
            "number,title,state,body,author,createdAt,labels,comments",
        ],
        cwd=cwd,
    )
    if result["status"] != "ok":
        return json.dumps(result)
    try:
        issue = json.loads(result["output"])
        return json.dumps({"status": "ok", "issue": issue})
    except json.JSONDecodeError:
        return json.dumps({"status": "ok", "output": result["output"]})


@tool(
    extras={
        "render_hint": "code_block",
        "category": "git",
        "destructive": False,
        "icon": "message-circle",
    }
)
async def gh_issue_comment(
    issue_number: int = 0,
    body: str = "",
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Adiciona um comentário a uma issue.

    Args:
        issue_number: Número da issue.
        body: Texto do comentário (suporta Markdown).
        workspace_id: ID do workspace.
    """
    cwd = _resolve_cwd(workspace_id, config)
    if not issue_number:
        return json.dumps(
            {"status": "error", "message": "Número da issue é obrigatório."}
        )
    if not body:
        return json.dumps(
            {"status": "error", "message": "Corpo do comentário é obrigatório."}
        )
    result = _gh_run(["issue", "comment", str(issue_number), "--body", body], cwd=cwd)
    return json.dumps(result)


# Sincroniza .extras → .metadata para compatibilidade com testes e endpoint GetTools
for _t in (
    gh_pr_list,
    gh_pr_create,
    gh_pr_view,
    gh_pr_merge,
    gh_issue_list,
    gh_issue_create,
    gh_issue_view,
    gh_issue_comment,
):
    if _t.extras:
        _t.metadata = _t.extras
