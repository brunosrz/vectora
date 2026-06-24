"""Handler REST do Context Graph — build, query e export por workspace.

Endpoints (todos exigem autenticação; workspace deve existir):
    POST  /workspaces/{workspace_id}/context-graph/build    — enfileira build
    GET   /workspaces/{workspace_id}/context-graph/status   — status do build
    GET   /workspaces/{workspace_id}/context-graph          — graph.json
    GET   /workspaces/{workspace_id}/context-graph/report   — GRAPH_REPORT.md
    GET   /workspaces/{workspace_id}/context-graph/html     — graph.html
    POST  /workspaces/{workspace_id}/context-graph/query    — pergunta livre
    POST  /workspaces/{workspace_id}/context-graph/explain  — explica nó
    POST  /workspaces/{workspace_id}/context-graph/path     — caminho entre nós
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/context-graph", tags=["context-graph"]
)

_GRAPH_DIR = ".vectora/graph"
_active_builds: dict[str, str] = {}  # workspace_id → "running" | "done" | "error:<msg>"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class BuildRequest(BaseModel):
    model: str = ""
    mode: str = "semantic"
    update: bool = False


class BuildResponse(BaseModel):
    status: str
    message: str


class StatusResponse(BaseModel):
    status: str
    node_count: int | None = None
    edge_count: int | None = None
    error: str | None = None


class QueryRequest(BaseModel):
    question: str
    top_k: int = 10


class ExplainRequest(BaseModel):
    node_id: str
    depth: int = 1


class PathRequest(BaseModel):
    source: str
    target: str


class GraphQueryResponse(BaseModel):
    answer: str
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return str(user.id)


def _graph_dir(workspace_id: str) -> Path | None:
    from backend.services.workspace import workspace_registry

    ws = workspace_registry.get(workspace_id)
    if ws is None:
        return None
    return Path(ws.cwd) / _GRAPH_DIR


def _require_graph_dir(workspace_id: str) -> Path:
    d = _graph_dir(workspace_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")
    return d


def _require_graph_json(workspace_id: str) -> dict[str, Any]:
    d = _require_graph_dir(workspace_id)
    graph_file = d / "graph.json"
    if not graph_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Grafo não encontrado — execute o build primeiro",
        )
    try:
        return json.loads(graph_file.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.exception("context-graph: falha ao ler graph.json")
        raise HTTPException(status_code=500, detail="Grafo corrompido") from exc


async def _run_build(workspace_id: str, req: BuildRequest) -> None:
    _active_builds[workspace_id] = "running"
    try:
        from backend.services.context_graph.pipeline import build_workspace_graph

        result = await build_workspace_graph(
            workspace_id,
            model=req.model,
            mode=req.mode,
            update=req.update,
        )
        if result.error:
            _active_builds[workspace_id] = f"error:{result.error}"
        else:
            _active_builds[workspace_id] = (
                f"done:{result.node_count}:{result.edge_count}"
            )
    except Exception:
        logger.exception(
            "context-graph: falha no build em background",
            extra={"workspace_id": workspace_id},
        )
        _active_builds[workspace_id] = "error:Falha interna no pipeline"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/build", response_model=BuildResponse)
async def post_build(
    request: Request,
    workspace_id: str,
    body: BuildRequest,
    background_tasks: BackgroundTasks,
) -> BuildResponse:
    _user_id(request)
    _require_graph_dir(workspace_id)

    if _active_builds.get(workspace_id) == "running":
        return BuildResponse(status="running", message="Build já em andamento")

    background_tasks.add_task(_run_build, workspace_id, body)
    return BuildResponse(status="queued", message="Build enfileirado")


def _status_from_disk(workspace_id: str) -> StatusResponse:
    d = _graph_dir(workspace_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")
    graph_file = d / "graph.json"
    if not graph_file.exists():
        return StatusResponse(status="not_built")
    try:
        data = json.loads(graph_file.read_text(encoding="utf-8"))
        return StatusResponse(
            status="done",
            node_count=len(data.get("nodes", [])),
            edge_count=len(data.get("edges", [])),
        )
    except Exception:
        return StatusResponse(status="error", error="graph.json ilegível")


@router.get("/status", response_model=StatusResponse)
async def get_status(request: Request, workspace_id: str) -> StatusResponse:
    _user_id(request)
    raw = _active_builds.get(workspace_id)

    if raw is None:
        return _status_from_disk(workspace_id)
    if raw == "running":
        return StatusResponse(status="running")
    if raw.startswith("error:"):
        return StatusResponse(status="error", error=raw[6:])
    if raw.startswith("done:"):
        parts = raw[5:].split(":")
        return StatusResponse(
            status="done",
            node_count=int(parts[0]) if parts else None,
            edge_count=int(parts[1]) if len(parts) > 1 else None,
        )
    return StatusResponse(status="unknown")


@router.get("", response_model=dict)
async def get_graph(request: Request, workspace_id: str) -> dict:
    _user_id(request)
    return _require_graph_json(workspace_id)


@router.get("/report")
async def get_report(request: Request, workspace_id: str) -> dict[str, str]:
    _user_id(request)
    d = _require_graph_dir(workspace_id)
    report_file = d / "GRAPH_REPORT.md"
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    return {"report": report_file.read_text(encoding="utf-8")}


@router.get("/html", response_class=HTMLResponse)
async def get_html(request: Request, workspace_id: str) -> HTMLResponse:
    _user_id(request)
    d = _require_graph_dir(workspace_id)
    html_file = d / "graph.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="HTML do grafo não encontrado")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@router.post("/query", response_model=GraphQueryResponse)
async def post_query(
    request: Request, workspace_id: str, body: QueryRequest
) -> GraphQueryResponse:
    _user_id(request)
    data = _require_graph_json(workspace_id)

    nodes: list[dict] = data.get("nodes", [])
    edges: list[dict] = data.get("edges", [])
    q_lower = body.question.lower()

    matched_nodes = [
        n
        for n in nodes
        if q_lower in str(n.get("label", "")).lower()
        or q_lower in str(n.get("id", "")).lower()
    ][: body.top_k]
    matched_ids = {n.get("id") for n in matched_nodes}

    neighborhood_edges = [
        e
        for e in edges
        if e.get("source") in matched_ids or e.get("target") in matched_ids
    ]
    neighbor_ids = {e.get("source") for e in neighborhood_edges} | {
        e.get("target") for e in neighborhood_edges
    }
    neighbor_nodes = [
        n
        for n in nodes
        if n.get("id") in neighbor_ids and n.get("id") not in matched_ids
    ]

    all_nodes = matched_nodes + neighbor_nodes
    summary = f"Encontrei {len(matched_nodes)} nó(s) correspondente(s) à consulta."
    return GraphQueryResponse(answer=summary, nodes=all_nodes, edges=neighborhood_edges)


@router.post("/explain", response_model=GraphQueryResponse)
async def post_explain(
    request: Request, workspace_id: str, body: ExplainRequest
) -> GraphQueryResponse:
    _user_id(request)
    data = _require_graph_json(workspace_id)

    nodes: list[dict] = data.get("nodes", [])
    edges: list[dict] = data.get("edges", [])

    target = next((n for n in nodes if n.get("id") == body.node_id), None)
    if target is None:
        raise HTTPException(
            status_code=404, detail=f"Nó '{body.node_id}' não encontrado"
        )

    connected_edges = [
        e
        for e in edges
        if e.get("source") == body.node_id or e.get("target") == body.node_id
    ]
    neighbor_ids = {e.get("source") for e in connected_edges} | {
        e.get("target") for e in connected_edges
    }
    neighbor_ids.discard(body.node_id)
    neighbor_nodes = [n for n in nodes if n.get("id") in neighbor_ids]

    summary = f"Nó: {target.get('label', body.node_id)} | {len(connected_edges)} arestas | {len(neighbor_nodes)} vizinhos"
    return GraphQueryResponse(
        answer=summary, nodes=[target, *neighbor_nodes], edges=connected_edges
    )


@router.post("/path", response_model=GraphQueryResponse)
async def post_path(
    request: Request, workspace_id: str, body: PathRequest
) -> GraphQueryResponse:
    _user_id(request)
    data = _require_graph_json(workspace_id)

    nodes: list[dict] = data.get("nodes", [])
    edges: list[dict] = data.get("edges", [])

    try:
        import networkx as nx

        graph = nx.Graph()
        for n in nodes:
            graph.add_node(n.get("id"))
        for e in edges:
            graph.add_edge(
                e.get("source"),
                e.get("target"),
                **{k: v for k, v in e.items() if k not in {"source", "target"}},
            )

        path_ids: list[str] = nx.shortest_path(graph, body.source, body.target)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail=f"Caminho não encontrado: {exc}"
        ) from exc

    path_id_set = set(path_ids)
    path_nodes = [n for n in nodes if n.get("id") in path_id_set]
    path_edges = [
        e
        for e in edges
        if e.get("source") in path_id_set and e.get("target") in path_id_set
    ]
    summary = f"Caminho de {body.source} → {body.target}: {len(path_ids)} nós"
    return GraphQueryResponse(answer=summary, nodes=path_nodes, edges=path_edges)
