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
    # G.2.1 — campos de transport. `local` é o default; SSH e Codespace
    # populam os campos abaixo conforme criados.
    transport: str = "local"
    remote_host: str | None = None
    remote_path: str | None = None
    codespace_name: str | None = None


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
    # ID do SafeRoot que cobre o path atual, quando aplicável. Frontend
    # exibe a label do safe-root como contexto ("dentro de Documents").
    safe_root_id: str | None = None


class SafeRootInfo(BaseModel):
    id: str
    path: str
    label: str
    builtin: bool


class ListSafeRootsResponse(BaseModel):
    roots: list[SafeRootInfo]


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


def _is_privileged(request: Request) -> bool:
    """True para root/admin (CLI local também é privilegiado).

    Usuários privilegiados podem navegar fora dos safe-roots
    (necessário para o admin escolher pastas a confiar).
    """
    user = getattr(request.state, "user", None)
    if user is None:
        return True  # CLI sem auth = root local
    role = str(getattr(user, "role", "")).lower()
    return role in {"root", "admin"}


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
        transport=getattr(ws, "transport", "local"),
        remote_host=getattr(ws, "remote_host", None),
        remote_path=getattr(ws, "remote_path", None),
        codespace_name=getattr(ws, "codespace_name", None),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/ListWorkspaces", response_model=ListWorkspacesResponse)
async def list_workspaces(request: Request) -> ListWorkspacesResponse:
    """Lista todos os workspaces registrados."""
    from src.services.workspace import workspace_registry

    uid = _user_id(request)
    active = workspace_registry.get_active(uid)
    return ListWorkspacesResponse(
        workspaces=[_to_info(ws) for ws in workspace_registry.list_all()],
        active_id=active.id if active else None,
    )


@router.get("/GetActiveWorkspace", response_model=ActiveWorkspaceResponse)
async def get_active_workspace(request: Request) -> ActiveWorkspaceResponse:
    """Retorna o workspace ativo do usuário (ou o do diretório atual)."""
    from src.services.workspace import workspace_registry

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
    from src.services.workspace import workspace_registry

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
    from src.services.workspace import workspace_registry

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
    from src.services.workspace import workspace_registry

    uid = _user_id(request)
    ok = workspace_registry.trust(body.workspace_id, uid)
    if not ok:
        return StatusResponse(status="error", message="Workspace não encontrado.")
    ws = workspace_registry.get(body.workspace_id)
    return StatusResponse(status="ok", workspace=_to_info(ws) if ws else None)


@router.post("/GitInitWorkspace", response_model=StatusResponse)
async def git_init_workspace(request: Request, body: GitInitRequest) -> StatusResponse:
    """Inicializa um repositório git na pasta do workspace."""
    from src.services.workspace import workspace_registry
    from src.tools.git import detect_git_info, git_init_repo

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
    request: Request,
    path: Annotated[str, Query()] = "",
) -> BrowseResponse:
    """Lista subdiretórios de um caminho, respeitando safe-roots.

    Usuários comuns (member/viewer): só navegam dentro das raízes
    configuradas pelo admin (``SafeRootRegistry``). Sem path, abre na
    raiz mais próxima do HOME (geralmente ``~/Documents/vectora``).
    Tentar sair gera 403; o botão "subir um nível" some na borda.

    Privilegiados (root/admin/CLI local): navegação livre — necessário
    para o admin escolher novas pastas a marcar como confiáveis.
    """
    from fastapi import HTTPException

    from src.services.safe_roots import get_safe_root_registry

    registry = get_safe_root_registry()
    privileged = _is_privileged(request)

    base = Path(path).expanduser() if path else Path.home()
    try:
        base = base.resolve()
    except OSError:
        base = Path.home()

    if not base.exists() or not base.is_dir():
        base = Path.home()

    # Cap por safe-root para usuários comuns.
    safe_root_id: str | None = None
    if not privileged:
        containing = registry.is_under_safe_root(str(base))
        if containing is None:
            # Se o caller pediu explicitamente um path fora, recusa.
            if path:
                raise HTTPException(
                    status_code=403,
                    detail="Caminho fora das pastas seguras configuradas.",
                )
            # Sem path: cai no safe-root mais próximo do HOME.
            fallback = registry.closest_safe_root_for(str(Path.home()))
            if fallback is None:
                raise HTTPException(
                    status_code=403,
                    detail="Nenhuma pasta segura configurada. "
                    "Peça ao admin para adicionar uma.",
                )
            base = Path(fallback.path)
            safe_root_id = fallback.id
        else:
            safe_root_id = containing.id

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

    # `parent` só preenche se ainda está sob algum safe-root (user comum)
    # ou se há um pai real (privileged).
    parent: str | None
    if base.parent == base:
        parent = None
    elif privileged:
        parent = str(base.parent)
    else:
        parent_under = registry.is_under_safe_root(str(base.parent))
        parent = str(base.parent) if parent_under is not None else None

    return BrowseResponse(
        path=str(base),
        parent=parent,
        entries=entries,
        safe_root_id=safe_root_id,
    )


@router.get("/ListSafeRoots", response_model=ListSafeRootsResponse)
async def list_safe_roots() -> ListSafeRootsResponse:
    """Lista as raízes confiáveis configuradas (visível a qualquer user)."""
    from src.services.safe_roots import get_safe_root_registry

    registry = get_safe_root_registry()
    return ListSafeRootsResponse(
        roots=[
            SafeRootInfo(id=r.id, path=r.path, label=r.label, builtin=r.builtin)
            for r in registry.all_roots()
        ],
    )


@router.get("/ListWorktrees", response_model=ListWorktreesResponse)
async def list_worktrees(
    workspace_id: Annotated[str, Query()] = "",
) -> ListWorktreesResponse:
    """Lista as worktrees de um workspace git."""
    from src.tools.git import _git_worktree_impl, _open_repo

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
    from src.tools.git import _git_worktree_impl, _open_repo

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


# ---------------------------------------------------------------------------
# Workbench views (Bloco T cont., T6/T7) — REST-style /workspaces/{id}/...
# ---------------------------------------------------------------------------
#
# Endpoints específicos consumidos pelas abas Arquivos e Diff do Workbench.
# Mantidos num router separado com prefixo /workspaces para conviver com o
# router Connect-style acima sem colisão.

view_router = APIRouter(prefix="/workspaces", tags=["workspaces-view"])


class TreeEntry(BaseModel):
    name: str
    path: str  # caminho relativo ao workspace
    kind: str  # "dir" | "file"
    size: int | None = None


class TreeResponse(BaseModel):
    path: str
    entries: list[TreeEntry]


class FileResponse(BaseModel):
    path: str
    kind: str  # "text" | "binary"
    content: str | None = None
    size: int = 0
    truncated: bool = False


class DiffFile(BaseModel):
    path: str
    status: str  # "M" | "A" | "D" | "R"
    additions: int = 0
    deletions: int = 0


class DiffHunk(BaseModel):
    header: str
    lines: list[str]


class DiffSummary(BaseModel):
    is_git_repo: bool
    total_additions: int = 0
    total_deletions: int = 0
    files: list[DiffFile]


class DiffFileResponse(BaseModel):
    path: str
    hunks: list[DiffHunk]


# Tamanho máximo lido pela aba Arquivos (previne payload gigante).
_MAX_FILE_PREVIEW = 256 * 1024  # 256 kB

# Diretórios ignorados por padrão na árvore — reduz ruído típico de projetos.
_IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".next",
    ".turbo",
    ".cache",
    "dist",
    "build",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}


def _resolve_inside(workspace_id: str, rel_path: str) -> Path | None:
    """Resolve ``rel_path`` para um caminho dentro do workspace ou None.

    Reusa o helper de segurança do Bloco Q4 (`resolve_within_workspace`),
    garantindo que `..` e symlinks para fora não escapem da pasta confiável.
    """
    from src.services.security import resolve_within_workspace
    from src.services.workspace import workspace_registry

    ws = workspace_registry.get(workspace_id)
    if ws is None:
        return None
    base = Path(ws.cwd)
    candidate = base if not rel_path else base / rel_path
    return resolve_within_workspace(str(candidate), base)


@view_router.get("/{workspace_id}/tree", response_model=TreeResponse)
async def workspace_tree(
    workspace_id: str,
    path: Annotated[str, Query()] = "",
) -> TreeResponse:
    """Lista entradas de um diretório dentro do workspace ativo.

    `path` é relativo ao workspace. Sem path → raiz. Diretórios típicos de
    build/cache são ocultados para enxugar a árvore.
    """
    resolved = _resolve_inside(workspace_id, path)
    if resolved is None or not resolved.exists() or not resolved.is_dir():
        return TreeResponse(path=path, entries=[])

    from src.services.workspace import workspace_registry

    ws = workspace_registry.get(workspace_id)
    base = Path(ws.cwd) if ws else resolved

    entries: list[TreeEntry] = []
    try:
        for item in sorted(
            resolved.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
        ):
            try:
                is_dir = item.is_dir()
            except OSError:
                continue
            if is_dir and item.name in _IGNORED_DIR_NAMES:
                continue
            try:
                rel = str(item.relative_to(base))
            except ValueError:
                continue
            size: int | None = None
            if not is_dir:
                try:
                    size = item.stat().st_size
                except OSError:
                    size = None
            entries.append(
                TreeEntry(
                    name=item.name,
                    path=rel.replace("\\", "/"),
                    kind="dir" if is_dir else "file",
                    size=size,
                )
            )
    except PermissionError:
        pass

    return TreeResponse(path=path, entries=entries)


@view_router.get("/{workspace_id}/file", response_model=FileResponse)
async def workspace_file(
    workspace_id: str,
    path: Annotated[str, Query()],
) -> FileResponse:
    """Lê o conteúdo (texto truncado) de um arquivo dentro do workspace."""
    resolved = _resolve_inside(workspace_id, path)
    if resolved is None or not resolved.exists() or not resolved.is_file():
        return FileResponse(path=path, kind="text", content=None, size=0)

    try:
        size = resolved.stat().st_size
    except OSError:
        size = 0

    # Detecção rudimentar de binário: byte nulo nos primeiros 8 kB.
    try:
        with resolved.open("rb") as f:
            head = f.read(8192)
    except OSError:
        return FileResponse(path=path, kind="text", content=None, size=size)

    if b"\x00" in head:
        return FileResponse(path=path, kind="binary", size=size)

    try:
        with resolved.open("r", encoding="utf-8", errors="replace") as f:
            content = f.read(_MAX_FILE_PREVIEW + 1)
    except OSError:
        return FileResponse(path=path, kind="text", content=None, size=size)

    truncated = len(content) > _MAX_FILE_PREVIEW
    if truncated:
        content = content[:_MAX_FILE_PREVIEW]
    return FileResponse(
        path=path,
        kind="text",
        content=content,
        size=size,
        truncated=truncated,
    )


def _parse_unified_diff(diff_text: str) -> list[DiffHunk]:
    """Quebra um diff unificado em hunks (sem a linha 'diff --git' inicial)."""
    hunks: list[DiffHunk] = []
    current: DiffHunk | None = None
    for line in diff_text.splitlines():
        if line.startswith("@@"):
            if current is not None:
                hunks.append(current)
            current = DiffHunk(header=line, lines=[])
        elif current is not None:
            current.lines.append(line)
    if current is not None:
        hunks.append(current)
    return hunks


@view_router.get("/{workspace_id}/git/diff", response_model=DiffSummary)
async def workspace_git_diff(workspace_id: str) -> DiffSummary:
    """Retorna o resumo do diff (uncommitted) do workspace.

    Inclui working tree + staged (HEAD..workdir). Para workspaces não-git
    retorna ``is_git_repo=False`` e lista vazia.
    """
    from src.services.workspace import workspace_registry

    ws = workspace_registry.get(workspace_id)
    if ws is None or not ws.cwd:
        return DiffSummary(is_git_repo=False, files=[])

    try:
        from git import Repo  # type: ignore[import-not-found]
        from git.exc import (  # type: ignore[import-not-found]
            InvalidGitRepositoryError,
            NoSuchPathError,
        )
    except Exception:
        return DiffSummary(is_git_repo=False, files=[])

    try:
        repo = Repo(ws.cwd, search_parent_directories=False)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return DiffSummary(is_git_repo=False, files=[])

    files: list[DiffFile] = []
    total_add = 0
    total_del = 0

    # `git diff HEAD` cobre staged + unstaged. Vazio = working tree limpa.
    try:
        diff_text = repo.git.diff("HEAD", numstat=True) or ""
    except Exception:
        diff_text = ""

    for raw in diff_text.splitlines():
        parts = raw.split("\t")
        if len(parts) < 3:
            continue
        adds_s, dels_s, path = parts[0], parts[1], parts[2]
        try:
            adds = int(adds_s) if adds_s != "-" else 0
            dels = int(dels_s) if dels_s != "-" else 0
        except ValueError:
            adds = dels = 0

        # Status: M/A/D — derivado de name-status (ainda barato).
        status = "M"
        try:
            ns = repo.git.diff("HEAD", "--name-status", path) or ""
            head = ns.splitlines()[0].split("\t", 1)[0] if ns else "M"
            status = head[:1] if head else "M"
        except Exception:
            status = "M"

        files.append(
            DiffFile(
                path=path.replace("\\", "/"),
                status=status,
                additions=adds,
                deletions=dels,
            )
        )
        total_add += adds
        total_del += dels

    return DiffSummary(
        is_git_repo=True,
        total_additions=total_add,
        total_deletions=total_del,
        files=files,
    )


@view_router.get("/{workspace_id}/git/diff/file", response_model=DiffFileResponse)
async def workspace_git_diff_file(
    workspace_id: str,
    path: Annotated[str, Query()],
) -> DiffFileResponse:
    """Hunks unificados de um arquivo específico (lazy load do diff-tab)."""
    from src.services.workspace import workspace_registry

    ws = workspace_registry.get(workspace_id)
    if ws is None:
        return DiffFileResponse(path=path, hunks=[])

    try:
        from git import Repo  # type: ignore[import-not-found]
        from git.exc import (  # type: ignore[import-not-found]
            InvalidGitRepositoryError,
            NoSuchPathError,
        )
    except Exception:
        return DiffFileResponse(path=path, hunks=[])

    try:
        repo = Repo(ws.cwd, search_parent_directories=False)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return DiffFileResponse(path=path, hunks=[])

    try:
        diff_text = repo.git.diff("HEAD", "--", path) or ""
    except Exception:
        diff_text = ""

    return DiffFileResponse(path=path, hunks=_parse_unified_diff(diff_text))
