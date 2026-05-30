"""Handler do WorkspaceService — gestão de workspaces (pastas confiáveis).

Endpoints (Connect-style, espelham o proxy Hono do frontend):
    GET  /vectora.workspace.v1.WorkspaceService/ListWorkspaces
    GET  /vectora.workspace.v1.WorkspaceService/GetActiveWorkspace
    POST /vectora.workspace.v1.WorkspaceService/SetActiveWorkspace
    POST /vectora.workspace.v1.WorkspaceService/CreateWorkspace
    POST /vectora.workspace.v1.WorkspaceService/TrustWorkspace
    POST /vectora.workspace.v1.WorkspaceService/GitInitWorkspace
    GET  /vectora.workspace.v1.WorkspaceService/BrowseDir
    GET  /vectora.workspace.v1.WorkspaceService/ListWorktrees
    POST /vectora.workspace.v1.WorkspaceService/CreateWorktree

O user_id é extraído de ``request.state.user`` (injetado pelo AuthMiddleware);
em modo CLI/root local, usa ``"local"``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vectora.workspace.v1.WorkspaceService", tags=["workspaces"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WorkspaceInfo(BaseModel):
    id: str
    name: str
    cwd: str
    trusted: bool = False
    is_git_repo: bool = False
    git_remote: str | None = None
    git_current_branch: str | None = None
    git_default_branch: str | None = None


class ListWorkspacesResponse(BaseModel):
    workspaces: list[WorkspaceInfo]
    active_id: str | None = None


class ActiveWorkspaceResponse(BaseModel):
    workspace: WorkspaceInfo | None = None


class SetActiveRequest(BaseModel):
    workspace_id: str


class CreateWorkspaceRequest(BaseModel):
    path: str
    trust: bool = False
    git_init: bool = False


class TrustRequest(BaseModel):
    workspace_id: str


class GitInitRequest(BaseModel):
    workspace_id: str


class StatusResponse(BaseModel):
    status: str
    message: str = ""
    workspace: WorkspaceInfo | None = None


class DirEntry(BaseModel):
    name: str
    path: str
    is_dir: bool


class BrowseResponse(BaseModel):
    path: str
    parent: str | None = None
    entries: list[DirEntry]


class WorktreeInfo(BaseModel):
    path: str
    branch: str | None = None
    head: str | None = None


class ListWorktreesResponse(BaseModel):
    worktrees: list[WorktreeInfo]


class CreateWorktreeRequest(BaseModel):
    workspace_id: str
    name: str
    branch: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_id(request: Request) -> str:
    """Extrai o user_id do request autenticado, ou 'local' em modo CLI."""
    user = getattr(request.state, "user", None)
    if user is not None and getattr(user, "id", None):
        return str(user.id)
    return "local"


def _to_info(ws: Any) -> WorkspaceInfo:
    """Converte um ``vectora.types.Workspace`` (duck-typed para evitar import cycle)."""
    return WorkspaceInfo(
        id=ws.id,
        name=ws.name,
        cwd=ws.cwd,
        trusted=getattr(ws, "trusted", False),
        is_git_repo=getattr(ws, "is_git_repo", False),
        git_remote=getattr(ws, "git_remote", None),
        git_current_branch=getattr(ws, "git_current_branch", None),
        git_default_branch=getattr(ws, "git_default_branch", None),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/ListWorkspaces", response_model=ListWorkspacesResponse)
async def list_workspaces(request: Request) -> ListWorkspacesResponse:
    """Lista todos os workspaces registrados."""
    from vectora.services.workspace import workspace_registry

    uid = _user_id(request)
    active = workspace_registry.get_active(uid)
    return ListWorkspacesResponse(
        workspaces=[_to_info(ws) for ws in workspace_registry.list_all()],
        active_id=active.id if active else None,
    )


@router.get("/GetActiveWorkspace", response_model=ActiveWorkspaceResponse)
async def get_active_workspace(request: Request) -> ActiveWorkspaceResponse:
    """Retorna o workspace ativo do usuário (ou o do diretório atual)."""
    from vectora.services.workspace import workspace_registry

    uid = _user_id(request)
    active = workspace_registry.get_active(uid)
    if active is None:
        active = workspace_registry.get_or_create()
        workspace_registry.set_active(active.id, uid)
    return ActiveWorkspaceResponse(workspace=_to_info(active))


@router.post("/SetActiveWorkspace", response_model=StatusResponse)
async def set_active_workspace(
    request: Request, body: SetActiveRequest
) -> StatusResponse:
    """Troca o workspace ativo do usuário."""
    from vectora.services.workspace import workspace_registry

    uid = _user_id(request)
    ok = workspace_registry.set_active(body.workspace_id, uid)
    if not ok:
        return StatusResponse(status="error", message="Workspace não encontrado.")
    ws = workspace_registry.get(body.workspace_id)
    return StatusResponse(status="ok", workspace=_to_info(ws) if ws else None)


@router.post("/CreateWorkspace", response_model=StatusResponse)
async def create_workspace(
    request: Request, body: CreateWorkspaceRequest
) -> StatusResponse:
    """Registra uma pasta como workspace, opcionalmente confiando e iniciando git."""
    from vectora.services.workspace import workspace_registry

    path = Path(body.path).expanduser()
    if not path.exists() or not path.is_dir():
        return StatusResponse(
            status="error", message=f"Diretório não encontrado: {body.path}"
        )

    uid = _user_id(request)
    ws = workspace_registry.create(
        str(path), trust=body.trust, git_init=body.git_init, user_id=uid
    )
    workspace_registry.set_active(ws.id, uid)
    return StatusResponse(status="ok", workspace=_to_info(ws))


@router.post("/TrustWorkspace", response_model=StatusResponse)
async def trust_workspace(request: Request, body: TrustRequest) -> StatusResponse:
    """Marca um workspace como confiável."""
    from vectora.services.workspace import workspace_registry

    uid = _user_id(request)
    ok = workspace_registry.trust(body.workspace_id, uid)
    if not ok:
        return StatusResponse(status="error", message="Workspace não encontrado.")
    ws = workspace_registry.get(body.workspace_id)
    return StatusResponse(status="ok", workspace=_to_info(ws) if ws else None)


@router.post("/GitInitWorkspace", response_model=StatusResponse)
async def git_init_workspace(request: Request, body: GitInitRequest) -> StatusResponse:
    """Inicializa um repositório git na pasta do workspace."""
    from vectora.services.workspace import workspace_registry
    from vectora.tools.git import detect_git_info, git_init_repo

    ws = workspace_registry.get(body.workspace_id)
    if ws is None:
        return StatusResponse(status="error", message="Workspace não encontrado.")

    result = git_init_repo(ws.cwd)
    if result.get("status") == "error":
        return StatusResponse(status="error", message=result.get("message", ""))

    info = detect_git_info(ws.cwd)
    ws.is_git_repo = info.get("is_git_repo", False)
    ws.git_current_branch = info.get("git_current_branch")
    ws.git_remote = info.get("git_remote")
    workspace_registry._save()
    return StatusResponse(status="ok", workspace=_to_info(ws))


@router.get("/BrowseDir", response_model=BrowseResponse)
async def browse_dir(
    path: Annotated[str, Query()] = "",
) -> BrowseResponse:
    """Lista subdiretórios de um caminho, para o directory browser da UI.

    Sem ``path`` → home do usuário. Mostra apenas diretórios (não arquivos),
    ocultando entradas que começam com ponto.
    """
    base = Path(path).expanduser() if path else Path.home()
    try:
        base = base.resolve()
    except OSError:
        base = Path.home()

    if not base.exists() or not base.is_dir():
        base = Path.home()

    entries: list[DirEntry] = []
    try:
        for item in sorted(base.iterdir(), key=lambda p: p.name.lower()):
            if item.name.startswith("."):
                continue
            try:
                is_dir = item.is_dir()
            except OSError:
                continue
            if not is_dir:
                continue
            entries.append(DirEntry(name=item.name, path=str(item), is_dir=True))
    except PermissionError:
        pass

    parent = str(base.parent) if base.parent != base else None
    return BrowseResponse(path=str(base), parent=parent, entries=entries)


@router.get("/ListWorktrees", response_model=ListWorktreesResponse)
async def list_worktrees(
    workspace_id: Annotated[str, Query()] = "",
) -> ListWorktreesResponse:
    """Lista as worktrees de um workspace git."""
    from vectora.tools.git import _git_worktree_impl, _open_repo

    repo, err = _open_repo(workspace_id or None, None)
    if err:
        return ListWorktreesResponse(worktrees=[])
    result = _git_worktree_impl(repo, workspace_id, action="list")
    items = result.get("worktrees", []) if result.get("status") == "ok" else []
    return ListWorktreesResponse(
        worktrees=[
            WorktreeInfo(
                path=w.get("path", ""),
                branch=w.get("branch"),
                head=w.get("head"),
            )
            for w in items
        ]
    )


@router.post("/CreateWorktree", response_model=StatusResponse)
async def create_worktree(body: CreateWorktreeRequest) -> StatusResponse:
    """Cria uma nova worktree para o workspace."""
    from vectora.tools.git import _git_worktree_impl, _open_repo

    repo, err = _open_repo(body.workspace_id or None, None)
    if err:
        return StatusResponse(
            status="error", message=json.loads(err).get("message", "")
        )
    result = _git_worktree_impl(
        repo, body.workspace_id, action="add", name=body.name, branch=body.branch
    )
    return StatusResponse(
        status=result.get("status", "error"), message=result.get("message", "")
    )
