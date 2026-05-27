"""Git tools — operações locais em repositórios git via GitPython.

G3 — Bloco G: git_status, git_log, git_diff, git_branch,
               git_checkout, git_commit, git_push, git_pull, git_stash.

Todas as tools:
- Resolvem o CWD via _resolve_workspace (workspace_id → config → cwd atual)
- Retornam JSON estruturado compatível com os render_hints declarados
- Funções-helper públicas (_git_*_impl) recebem git.Repo diretamente,
  facilitando testes unitários sem dependência do WorkspaceRegistry.

Dependência: gitpython >= 3.1
"""

from __future__ import annotations

import contextlib
import json
import logging
from typing import TYPE_CHECKING, Annotated

import git
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _resolve_workspace(workspace_id: str | None, config: RunnableConfig | None):
    """Resolve workspace → Workspace (mesmo padrão de workspace.py)."""
    from vectora.services.workspace import workspace_registry

    wid = workspace_id
    if wid is None and config is not None:
        wid = (config.get("configurable") or {}).get("workspace_id")
    if wid:
        ws = workspace_registry.get(wid)
        if ws is not None:
            return ws
    return workspace_registry.get_or_create()


def _open_repo(workspace_id: str | None, config: RunnableConfig | None):
    """Abre git.Repo para o workspace ativo.

    Retorna (repo, None) em sucesso ou (None, error_json_str) em falha.
    """
    ws = _resolve_workspace(workspace_id, config)
    if ws is None:
        return None, json.dumps(
            {"status": "error", "message": "Workspace não encontrado."}
        )
    try:
        repo = git.Repo(ws.cwd, search_parent_directories=True)
        return repo, None
    except git.InvalidGitRepositoryError:
        return None, json.dumps(
            {
                "status": "not_git",
                "message": f"Não é um repositório git: {ws.cwd}",
            }
        )
    except Exception as exc:
        return None, json.dumps({"status": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Funções-helper públicas (testáveis diretamente)
# ---------------------------------------------------------------------------


def _git_status_impl(repo: git.Repo) -> dict:
    """Retorna o estado de trabalho do repositório."""
    try:
        branch = repo.active_branch.name
    except TypeError:
        branch = (
            str(repo.head.commit.hexsha[:7])
            if not repo.head.is_detached
            else "HEAD detached"
        )

    untracked = repo.untracked_files
    modified = [item.a_path for item in repo.index.diff(None)]
    staged = [item.a_path for item in repo.index.diff("HEAD")]

    # ahead/behind quando há remote tracking
    ahead = behind = 0
    try:
        tracking = repo.active_branch.tracking_branch()
        if tracking:
            commits = list(repo.iter_commits(f"{tracking.name}..HEAD"))
            ahead = len(commits)
            commits_behind = list(repo.iter_commits(f"HEAD..{tracking.name}"))
            behind = len(commits_behind)
    except Exception:
        pass

    clean = not untracked and not modified and not staged
    return {
        "status": "ok",
        "branch": branch,
        "clean": clean,
        "untracked": list(untracked),
        "modified": modified,
        "staged": staged,
        "ahead": ahead,
        "behind": behind,
    }


def _git_log_impl(repo: git.Repo, n: int = 10, branch: str | None = None) -> dict:
    """Retorna histórico de commits."""
    try:
        ref = branch or repo.active_branch.name
    except TypeError:
        ref = "HEAD"

    try:
        commits = list(repo.iter_commits(ref, max_count=n))
    except git.GitCommandError:
        # repo vazio ou branch inválida
        return {"status": "ok", "commits": [], "branch": ref}

    return {
        "status": "ok",
        "branch": ref,
        "commits": [
            {
                "hash": c.hexsha[:7],
                "author": str(c.author),
                "date": c.authored_datetime.isoformat(),
                "message": c.message.strip().splitlines()[0],
            }
            for c in commits
        ],
    }


def _git_diff_impl(repo: git.Repo, ref: str | None = None) -> dict:
    """Retorna diff do working tree (ou em relação a ref)."""
    try:
        if ref:
            diff_text = repo.git.diff(ref)
        else:
            diff_text = repo.git.diff()
        return {"status": "ok", "diff": diff_text}
    except git.GitCommandError as exc:
        return {"status": "error", "message": str(exc)}


def _git_branch_impl(
    repo: git.Repo,
    action: str,
    name: str | None = None,
) -> dict:
    """Operações em branches: list / create / delete."""
    if action == "list":
        branches = [b.name for b in repo.branches]
        try:
            current = repo.active_branch.name
        except TypeError:
            current = "(HEAD detached)"
        return {"status": "ok", "branches": branches, "current": current}

    if action == "create":
        if not name:
            return {"status": "error", "message": "Nome da branch é obrigatório."}
        try:
            repo.create_head(name)
            return {"status": "ok", "branch": name, "action": "created"}
        except git.GitCommandError as exc:
            return {"status": "error", "message": str(exc)}

    if action == "delete":
        if not name:
            return {"status": "error", "message": "Nome da branch é obrigatório."}
        try:
            repo.delete_head(name, force=True)
            return {"status": "ok", "branch": name, "action": "deleted"}
        except git.GitCommandError as exc:
            return {"status": "error", "message": str(exc)}

    return {"status": "error", "message": f"Ação desconhecida: {action}"}


def _git_checkout_impl(repo: git.Repo, ref: str) -> dict:
    """Faz checkout para branch ou commit."""
    try:
        repo.git.checkout(ref)
        try:
            branch = repo.active_branch.name
        except TypeError:
            branch = ref
        return {"status": "ok", "branch": branch, "ref": ref}
    except git.GitCommandError as exc:
        return {"status": "error", "message": str(exc)}


def _git_commit_impl(
    repo: git.Repo,
    message: str,
    all: bool = False,  # noqa: A002
) -> dict:
    """Cria um commit.

    Args:
        message: Mensagem de commit (formato conventional commits recomendado).
        all: Se True, stageia automaticamente arquivos modificados rastreados
             (equivalente a `git commit -a`).
    """
    # Stage -a se solicitado
    if all:
        repo.git.add("-u")

    if not repo.index.diff("HEAD") and not repo.index.diff(None, staged=True):
        # Verifica staged mais precisamente
        if not repo.is_dirty(index=True):
            return {
                "status": "error",
                "message": "Nada staged para commitar. Use git_status para ver o estado.",
            }

    try:
        commit = repo.index.commit(message)
        return {
            "status": "ok",
            "hash": commit.hexsha[:7],
            "message": message,
            "files_changed": len(commit.stats.files),
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def _git_push_impl(
    repo: git.Repo,
    remote: str = "origin",
    branch: str | None = None,
    force: bool = False,
) -> dict:
    """Faz push para remote."""
    try:
        active = branch or repo.active_branch.name
        args = [remote, active]
        if force:
            args.append("--force")
        repo.git.push(*args)
        return {"status": "ok", "remote": remote, "branch": active, "forced": force}
    except git.GitCommandError as exc:
        return {"status": "error", "message": str(exc)}


def _git_pull_impl(
    repo: git.Repo,
    remote: str = "origin",
    branch: str | None = None,
) -> dict:
    """Faz pull do remote."""
    try:
        active = branch or repo.active_branch.name
        repo.git.pull(remote, active)
        return {"status": "ok", "remote": remote, "branch": active}
    except git.GitCommandError as exc:
        return {"status": "error", "message": str(exc)}


def _git_stash_impl(
    repo: git.Repo,
    action: str,
    name: str | None = None,
) -> dict:
    """Operações de stash: push / pop / list / drop."""
    if action == "push":
        try:
            args = ["push"]
            if name:
                args += ["-m", name]
            out = repo.git.stash(*args)
            if "No local changes" in out:
                return {"status": "info", "message": "Nada para salvar no stash."}
            return {"status": "ok", "action": "push", "message": out.strip()}
        except git.GitCommandError as exc:
            return {"status": "error", "message": str(exc)}

    if action == "pop":
        try:
            repo.git.stash("pop")
            return {"status": "ok", "action": "pop"}
        except git.GitCommandError as exc:
            return {"status": "error", "message": str(exc)}

    if action == "list":
        try:
            out = repo.git.stash("list")
            entries = [l.strip() for l in out.splitlines() if l.strip()]
            return {"status": "ok", "action": "list", "entries": entries}
        except git.GitCommandError as exc:
            return {"status": "error", "message": str(exc)}

    if action == "drop":
        try:
            repo.git.stash("drop")
            return {"status": "ok", "action": "drop"}
        except git.GitCommandError as exc:
            return {"status": "error", "message": str(exc)}

    return {"status": "error", "message": f"Ação desconhecida: {action}"}


# ---------------------------------------------------------------------------
# @tool wrappers (G3)
# ---------------------------------------------------------------------------


@tool(
    extras={
        "render_hint": "code_block",
        "category": "git",
        "destructive": False,
        "icon": "git-branch",
    }
)
async def git_status(
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str:
    """Mostra o estado do repositório git: arquivos modificados, staged, untracked.

    Retorna branch ativa, contagem ahead/behind e listas de arquivos por categoria.
    Use antes de commitar ou criar PR para garantir que o estado está correto.

    Args:
        workspace_id: ID do workspace (usa o workspace ativo se omitido).
    """
    repo, err = _open_repo(workspace_id, config)
    if err:
        return err
    return json.dumps(_git_status_impl(repo))


@tool(
    extras={
        "render_hint": "table",
        "category": "git",
        "destructive": False,
        "icon": "git-commit",
    }
)
async def git_log(
    n: int = 10,
    branch: str | None = None,
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str:
    """Exibe o histórico de commits do repositório.

    Args:
        n: Número de commits a retornar (default: 10).
        branch: Branch específica (usa branch ativa se omitida).
        workspace_id: ID do workspace.
    """
    repo, err = _open_repo(workspace_id, config)
    if err:
        return err
    return json.dumps(_git_log_impl(repo, n=n, branch=branch))


@tool(
    extras={
        "render_hint": "diff",
        "category": "git",
        "destructive": False,
        "icon": "diff",
    }
)
async def git_diff(
    ref: str | None = None,
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str:
    """Mostra o diff do working tree ou em relação a um commit/branch.

    Args:
        ref: Commit hash, tag ou branch para comparar (compara working tree se omitido).
        workspace_id: ID do workspace.
    """
    repo, err = _open_repo(workspace_id, config)
    if err:
        return err
    return json.dumps(_git_diff_impl(repo, ref=ref))


@tool(
    extras={
        "render_hint": "table",
        "category": "git",
        "destructive": False,
        "icon": "git-branch",
    }
)
async def git_branch(
    action: str = "list",
    name: str | None = None,
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str:
    """Gerencia branches: lista, cria ou deleta.

    Args:
        action: "list" | "create" | "delete"
        name: Nome da branch (obrigatório para create/delete).
        workspace_id: ID do workspace.
    """
    repo, err = _open_repo(workspace_id, config)
    if err:
        return err
    return json.dumps(_git_branch_impl(repo, action=action, name=name))


@tool(
    extras={
        "render_hint": "code_block",
        "category": "git",
        "destructive": True,
        "icon": "git-branch",
    }
)
async def git_checkout(
    ref: str = "",
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str:
    """Troca para uma branch ou commit.

    ⚠️ Mudanças não commitadas podem ser perdidas. Faça git_status antes.

    Args:
        ref: Branch, tag ou commit hash para checkout.
        workspace_id: ID do workspace.
    """
    repo, err = _open_repo(workspace_id, config)
    if err:
        return err
    if not ref:
        return json.dumps({"status": "error", "message": "ref é obrigatório."})
    return json.dumps(_git_checkout_impl(repo, ref=ref))


@tool(
    extras={
        "render_hint": "code_block",
        "category": "git",
        "destructive": True,
        "icon": "git-commit",
    }
)
async def git_commit(
    message: str = "",
    all: bool = False,  # noqa: A002
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str:
    """Cria um commit com os arquivos staged.

    Use conventional commits: feat:, fix:, refactor:, docs:, test:, chore:.
    Sempre escreva mensagens descritivas — nunca "wip" ou "update".

    Args:
        message: Mensagem de commit (conventional commits recomendado).
        all: Se True, stageia automaticamente modificações rastreadas (-a).
        workspace_id: ID do workspace.
    """
    repo, err = _open_repo(workspace_id, config)
    if err:
        return err
    if not message:
        return json.dumps(
            {"status": "error", "message": "Mensagem de commit é obrigatória."}
        )
    return json.dumps(_git_commit_impl(repo, message=message, all=all))


@tool(
    extras={
        "render_hint": "code_block",
        "category": "git",
        "destructive": True,
        "icon": "upload-cloud",
    }
)
async def git_push(
    remote: str = "origin",
    branch: str | None = None,
    force: bool = False,
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str:
    """Envia commits locais para o remote.

    ⚠️ Force push em branches compartilhadas pode sobrescrever histórico remoto.

    Args:
        remote: Nome do remote (default: "origin").
        branch: Branch a enviar (usa branch ativa se omitida).
        force: Se True, usa --force (cuidado em branches compartilhadas).
        workspace_id: ID do workspace.
    """
    repo, err = _open_repo(workspace_id, config)
    if err:
        return err
    return json.dumps(_git_push_impl(repo, remote=remote, branch=branch, force=force))


@tool(
    extras={
        "render_hint": "code_block",
        "category": "git",
        "destructive": True,
        "icon": "download-cloud",
    }
)
async def git_pull(
    remote: str = "origin",
    branch: str | None = None,
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str:
    """Baixa e integra commits do remote.

    Args:
        remote: Nome do remote (default: "origin").
        branch: Branch a baixar (usa branch ativa se omitida).
        workspace_id: ID do workspace.
    """
    repo, err = _open_repo(workspace_id, config)
    if err:
        return err
    return json.dumps(_git_pull_impl(repo, remote=remote, branch=branch))


@tool(
    extras={
        "render_hint": "code_block",
        "category": "git",
        "destructive": False,
        "icon": "layers",
    }
)
async def git_stash(
    action: str = "push",
    name: str | None = None,
    workspace_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str:
    """Gerencia o stash: salva, aplica ou lista mudanças temporárias.

    Args:
        action: "push" | "pop" | "list" | "drop"
        name: Nome descritivo do stash (opcional, apenas para push).
        workspace_id: ID do workspace.
    """
    repo, err = _open_repo(workspace_id, config)
    if err:
        return err
    return json.dumps(_git_stash_impl(repo, action=action, name=name))


# Sincroniza .extras → .metadata para compatibilidade com testes e endpoint GetTools
for _t in (
    git_status,
    git_log,
    git_diff,
    git_branch,
    git_checkout,
    git_commit,
    git_push,
    git_pull,
    git_stash,
):
    if _t.extras:
        _t.metadata = _t.extras


# ---------------------------------------------------------------------------
# G7 — helpers para detecção de git no workspace
# ---------------------------------------------------------------------------


def detect_git_info(cwd: str) -> dict:
    """Detecta se o diretório é um repo git e retorna informações básicas.

    Retorna dict com is_git_repo, branch, remote e default_branch.
    Usado por WorkspaceRegistry.get_or_create() para preencher campos git.
    """
    try:
        repo = git.Repo(cwd, search_parent_directories=True)
        try:
            branch = repo.active_branch.name
        except TypeError:
            branch = None
        remotes = [r.name for r in repo.remotes]
        remote_url = None
        if repo.remotes:
            with contextlib.suppress(Exception):
                remote_url = repo.remotes[0].url
        return {
            "is_git_repo": True,
            "git_current_branch": branch,
            "git_remote": remote_url,
            "git_remotes": remotes,
        }
    except git.InvalidGitRepositoryError:
        return {"is_git_repo": False}
    except Exception:
        return {"is_git_repo": False}
