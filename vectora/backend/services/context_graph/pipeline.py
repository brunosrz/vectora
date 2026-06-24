"""Pipeline principal do Context Graph — build assíncrono por workspace.

Orquestra os passes: detect → AST (asyncio.to_thread) → semântico → build
→ cluster → analyze → report/export. Grava artefatos em .vectora/graph/
dentro do workspace.

Defensivo (§11): cada passo tem try/except com logging estruturado.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_GRAPH_DIR = ".vectora/graph"


@dataclass
class GraphResult:
    workspace_id: str
    workspace_path: Path
    graph_path: Path
    report_path: Path
    html_path: Path
    node_count: int = 0
    edge_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    god_nodes: list[str] = field(default_factory=list)
    suggested_questions: list[str] = field(default_factory=list)
    error: str | None = None


def _graph_out_dir(workspace_path: Path) -> Path:
    return workspace_path / _GRAPH_DIR


async def build_workspace_graph(
    workspace_id: str,
    *,
    model: str = "",
    mode: str = "semantic",
    update: bool = False,
) -> GraphResult:
    """Constrói (ou atualiza) o grafo de contexto de um workspace.

    Args:
        workspace_id: ID do workspace (sha256 truncado do cwd).
        model: model_id no formato "provider:model" — vazio = LLM padrão.
        mode: "semantic" (AST + LLM), "ast" (só AST).
        update: True = incremental (só arquivos novos/modificados).

    Returns:
        GraphResult com caminhos dos artefatos e métricas básicas.
    """
    from backend.services.workspace import workspace_registry

    ws = workspace_registry.get(workspace_id)
    if ws is None:
        msg = f"context_graph: workspace {workspace_id!r} não encontrado"
        logger.error(msg)
        return GraphResult(
            workspace_id=workspace_id,
            workspace_path=Path(),
            graph_path=Path(),
            report_path=Path(),
            html_path=Path(),
            error=msg,
        )

    workspace_path = Path(ws.cwd)
    out_dir = _graph_out_dir(workspace_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    graph_json = out_dir / "graph.json"
    report_md = out_dir / "GRAPH_REPORT.md"
    graph_html = out_dir / "graph.html"
    manifest_path = str(out_dir / "manifest.json")

    result = GraphResult(
        workspace_id=workspace_id,
        workspace_path=workspace_path,
        graph_path=graph_json,
        report_path=report_md,
        html_path=graph_html,
    )

    try:
        # ── Passo 1: detectar arquivos ────────────────────────────────────────
        from .detect import detect, detect_incremental, save_manifest

        logger.info("context_graph: detectando arquivos em %s", workspace_path)
        if update and graph_json.exists():
            corpus = await asyncio.to_thread(
                detect_incremental,
                workspace_path,
                manifest_path,
                kind="semantic" if mode == "semantic" else "ast",
            )
            all_files: list[str] = [
                f
                for flist in corpus.get("new_files", {}).values()
                for f in flist
            ]
        else:
            corpus = await asyncio.to_thread(detect, workspace_path)
            all_files = [f for flist in corpus.get("files", {}).values() for f in flist]

        if not all_files:
            logger.info("context_graph: nenhum arquivo novo detectado")
            return result

        logger.info(
            "context_graph: %d arquivos para extração",
            len(all_files),
            extra={"workspace_id": workspace_id, "mode": mode},
        )

        # ── Passo 2: extração AST (CPU-bound → thread) ────────────────────────
        ast_results: dict[str, Any] = {"nodes": [], "edges": [], "hyperedges": []}
        try:
            ast_results = await asyncio.to_thread(
                _run_ast_extraction, all_files, workspace_path
            )
        except Exception:
            logger.exception("context_graph: falha na extração AST", extra={"workspace_id": workspace_id})

        # ── Passo 3: extração semântica (async LLM) ───────────────────────────
        semantic_results: dict[str, Any] = {"nodes": [], "edges": [], "hyperedges": [], "input_tokens": 0, "output_tokens": 0}
        if mode == "semantic":
            from .semantic import extract_semantic

            files_map = corpus.get("new_files" if update else "files") or {}
            text_paths = (
                [Path(f) for f in files_map.get("code", [])]
                + [Path(f) for f in files_map.get("document", [])]
                + [Path(f) for f in files_map.get("paper", [])]
            )

            if text_paths:
                try:
                    semantic_results = await extract_semantic(
                        text_paths,
                        workspace_path,
                        model_id=model,
                        deep_mode=False,
                    )
                    result.input_tokens = semantic_results.get("input_tokens", 0)
                    result.output_tokens = semantic_results.get("output_tokens", 0)
                except Exception:
                    logger.exception("context_graph: falha na extração semântica", extra={"workspace_id": workspace_id})

        # ── Passo 4: build (funde AST + semântico → grafo NetworkX) ──────────
        from .build import build

        try:
            graph = await asyncio.to_thread(
                build,
                [ast_results, semantic_results],
                root=workspace_path,
            )
        except Exception:
            logger.exception("context_graph: falha no build do grafo", extra={"workspace_id": workspace_id})
            return result

        result.node_count = graph.number_of_nodes()
        result.edge_count = graph.number_of_edges()

        # ── Passo 5: cluster (comunidades Leiden/Louvain) ─────────────────────
        from .cluster import cluster, score_all

        communities: dict[int, list[str]] = {}
        cohesion: dict[int, float] = {}
        try:
            communities = await asyncio.to_thread(cluster, graph)
            cohesion = await asyncio.to_thread(score_all, graph, communities)
        except Exception:
            logger.exception("context_graph: falha no clustering", extra={"workspace_id": workspace_id})

        # ── Passo 6: analyze (god nodes, conexões surpreendentes, perguntas) ──
        from .analyze import god_nodes, suggest_questions, surprising_connections

        community_labels: dict[int, str] = {}
        god_node_list: list[dict] = []
        surprise_list: list[dict] = []
        questions: list[dict] = []

        try:
            god_node_list = await asyncio.to_thread(god_nodes, graph)
            surprise_list = await asyncio.to_thread(surprising_connections, graph, communities)
            questions = await asyncio.to_thread(suggest_questions, graph, communities, community_labels)
            result.god_nodes = [n.get("label", n.get("id", "")) for n in god_node_list[:5]]
            result.suggested_questions = [q.get("question", "") for q in questions[:5]]
        except Exception:
            logger.exception("context_graph: falha na análise", extra={"workspace_id": workspace_id})

        # ── Passo 7: report + export ──────────────────────────────────────────
        from .export import to_html, to_json
        from .report import generate as generate_report

        token_cost = {"input": result.input_tokens, "output": result.output_tokens}

        try:
            report_text = await asyncio.to_thread(
                generate_report,
                graph,
                communities,
                cohesion,
                community_labels,
                god_node_list,
                surprise_list,
                corpus,
                token_cost,
                str(workspace_path),
                questions,
            )
            report_md.write_text(report_text, encoding="utf-8")
        except Exception:
            logger.exception("context_graph: falha ao gerar relatório", extra={"workspace_id": workspace_id})

        try:
            await asyncio.to_thread(to_json, graph, communities, str(graph_json))
        except Exception:
            logger.exception("context_graph: falha ao exportar graph.json", extra={"workspace_id": workspace_id})

        try:
            await asyncio.to_thread(to_html, graph, communities, str(graph_html))
        except Exception:
            logger.exception("context_graph: falha ao exportar graph.html", extra={"workspace_id": workspace_id})

        # ── Passo 8: salvar manifesto incremental ─────────────────────────────
        try:
            await asyncio.to_thread(
                save_manifest,
                corpus.get("files", {}),
                manifest_path,
                kind="both",
                root=workspace_path,
            )
        except Exception:
            logger.exception("context_graph: falha ao salvar manifesto", extra={"workspace_id": workspace_id})

        logger.info(
            "context_graph: build completo — %d nós, %d arestas, %d tokens",
            result.node_count, result.edge_count,
            result.input_tokens + result.output_tokens,
            extra={"workspace_id": workspace_id},
        )
        return result

    except Exception:
        logger.exception("context_graph: falha catastrófica no pipeline", extra={"workspace_id": workspace_id})
        result.error = "Falha no pipeline do context graph — veja os logs."
        return result


def _run_ast_extraction(files: list[str], workspace_path: Path) -> dict[str, Any]:
    """Roda extração AST síncrona (chamada via asyncio.to_thread)."""
    from .cache import load_cached, save_cached
    from .extract import _get_extractor, _safe_extract

    nodes: list[dict] = []
    edges: list[dict] = []
    hyperedges: list[dict] = []

    for file_str in files:
        path = Path(file_str)
        try:
            cached = load_cached(path, workspace_path)
            if cached is not None:
                nodes.extend(cached.get("nodes", []))
                edges.extend(cached.get("edges", []))
                hyperedges.extend(cached.get("hyperedges", []))
                continue
            extractor = _get_extractor(path)
            if extractor is None:
                continue
            data = _safe_extract(extractor, path)
            if "error" not in data:
                save_cached(path, data, workspace_path)
            nodes.extend(data.get("nodes", []))
            edges.extend(data.get("edges", []))
            hyperedges.extend(data.get("hyperedges", []))
        except Exception:
            logger.exception("context_graph: falha ao extrair %s", file_str)

    return {"nodes": nodes, "edges": edges, "hyperedges": hyperedges}
