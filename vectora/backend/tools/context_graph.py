"""Tools do Context Graph para o agente.

Cada tool é defensiva (§11): captura exceção e devolve string tipada — nunca
propaga. Registradas em nodes/tools.py (modo Dev).
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

logger = logging.getLogger(__name__)


def _active_workspace_id(config: RunnableConfig | None) -> str | None:
    if config is None:
        return None
    cfg = config.get("configurable", {})
    return cfg.get("workspace_id") or cfg.get("active_workspace_id")


@tool
async def build_knowledge_graph(
    config: Annotated[RunnableConfig, InjectedToolArg],
    model: str = "",
    mode: str = "semantic",
) -> str:
    """Constrói o grafo de contexto do workspace ativo.

    Extrai nós (funções, classes, conceitos), arestas (calls, imports, references)
    e produz um relatório com god nodes, conexões surpreendentes e perguntas sugeridas.

    Args:
        model: modelo LLM no formato "provider:model" (vazio = padrão do sistema).
        mode: "semantic" (AST + LLM) ou "ast" (só árvore sintática, sem LLM).

    Returns:
        Resumo do grafo com contagem de nós/arestas, god nodes e próximos passos.
    """
    try:
        workspace_id = _active_workspace_id(config)
        if not workspace_id:
            return "Erro: nenhum workspace ativo. Abra um workspace primeiro."

        from backend.services.context_graph.pipeline import build_workspace_graph

        result = await build_workspace_graph(workspace_id, model=model, mode=mode)
        if result.error:
            return f"Erro no build do grafo: {result.error}"

        lines = [
            f"Grafo construído: {result.node_count} nós, {result.edge_count} arestas.",
        ]
        if result.god_nodes:
            lines.append(
                f"God nodes (mais conectados): {', '.join(result.god_nodes[:5])}."
            )
        if result.suggested_questions:
            lines.append("Perguntas sugeridas:")
            lines.extend(f"  - {q}" for q in result.suggested_questions[:3])
        lines.append(f"Relatório em: {result.report_path}")
        return "\n".join(lines)

    except Exception as exc:
        logger.exception("graph: falha em build_knowledge_graph")
        return f"Erro ao construir o grafo: {exc}"


@tool
async def graph_query(
    question: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
    top_k: int = 10,
) -> str:
    """Consulta o grafo de contexto por pergunta livre.

    Retorna nós relevantes e sua vizinhança, consumindo muito menos tokens do
    que ler os arquivos brutos (71x menos em média).

    Args:
        question: pergunta ou termo de busca (ex.: "quem chama authenticate?").
        top_k: número máximo de nós retornados na consulta (padrão 10).

    Returns:
        Nós encontrados com seus tipos, labels e arestas de conexão, em texto.
    """
    try:
        workspace_id = _active_workspace_id(config)
        if not workspace_id:
            return "Erro: nenhum workspace ativo."

        from backend.services.workspace import workspace_registry

        ws = workspace_registry.get(workspace_id)
        if ws is None:
            return "Erro: workspace não encontrado."

        from pathlib import Path

        graph_file = Path(ws.cwd) / ".vectora/graph/graph.json"
        if not graph_file.exists():
            return "Grafo não encontrado. Execute build_knowledge_graph primeiro."

        data = json.loads(graph_file.read_text(encoding="utf-8"))
        nodes: list[dict] = data.get("nodes", [])
        edges: list[dict] = data.get("edges", [])

        q_lower = question.lower()
        matched = [
            n
            for n in nodes
            if q_lower in str(n.get("label", "")).lower()
            or q_lower in str(n.get("id", "")).lower()
            or q_lower in str(n.get("type", "")).lower()
        ][:top_k]

        if not matched:
            return f"Nenhum nó encontrado para: '{question}'."

        matched_ids = {n.get("id") for n in matched}
        rel_edges = [
            e
            for e in edges
            if e.get("source") in matched_ids or e.get("target") in matched_ids
        ]

        lines = [
            f"Encontrei {len(matched)} nó(s) para '{question}':",
            *[
                f"  [{n.get('type', '?')}] {n.get('label', n.get('id', ''))}"
                for n in matched
            ],
        ]
        if rel_edges:
            lines.append(f"\n{len(rel_edges)} arestas relacionadas:")
            lines.extend(
                f"  {e.get('source', '?')} --[{e.get('label', e.get('type', '?'))}]--> {e.get('target', '?')}"
                for e in rel_edges[:15]
            )
        return "\n".join(lines)

    except Exception as exc:
        logger.exception("graph: falha em graph_query")
        return f"Erro na consulta do grafo: {exc}"


@tool
async def graph_explain(
    node_id: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Explica um nó do grafo de contexto mostrando sua vizinhança e conexões.

    Args:
        node_id: ID ou label do nó a explicar (ex.: "AuthService", "authenticate").

    Returns:
        Tipo, vizinhos e relações do nó, com o suficiente para entender seu papel.
    """
    try:
        workspace_id = _active_workspace_id(config)
        if not workspace_id:
            return "Erro: nenhum workspace ativo."

        from backend.services.workspace import workspace_registry

        ws = workspace_registry.get(workspace_id)
        if ws is None:
            return "Erro: workspace não encontrado."

        from pathlib import Path

        graph_file = Path(ws.cwd) / ".vectora/graph/graph.json"
        if not graph_file.exists():
            return "Grafo não encontrado. Execute build_knowledge_graph primeiro."

        data = json.loads(graph_file.read_text(encoding="utf-8"))
        nodes: list[dict] = data.get("nodes", [])
        edges: list[dict] = data.get("edges", [])

        target = next(
            (n for n in nodes if n.get("id") == node_id or n.get("label") == node_id),
            None,
        )
        if target is None:
            return f"Nó '{node_id}' não encontrado no grafo."

        nid = target.get("id")
        connected = [
            e for e in edges if e.get("source") == nid or e.get("target") == nid
        ]
        neighbor_ids = {e.get("source") for e in connected} | {
            e.get("target") for e in connected
        }
        neighbor_ids.discard(nid)
        neighbors = [n for n in nodes if n.get("id") in neighbor_ids]

        lines = [
            f"Nó: {target.get('label', nid)} (tipo: {target.get('type', '?')})",
        ]
        if target.get("docstring"):
            lines.append(f"Docstring: {str(target['docstring'])[:200]}")
        lines.append(f"\n{len(connected)} arestas | {len(neighbors)} vizinhos:")
        for e in connected[:20]:
            direction = "→" if e.get("source") == nid else "←"
            other = e.get("target") if e.get("source") == nid else e.get("source")
            lines.append(
                f"  {direction} [{e.get('label', e.get('type', '?'))}] {other}"
            )
        return "\n".join(lines)

    except Exception as exc:
        logger.exception("graph: falha em graph_explain")
        return f"Erro ao explicar nó: {exc}"


@tool
async def graph_path(
    source: str,
    target: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Encontra o caminho mais curto entre dois nós no grafo de contexto.

    Args:
        source: ID ou label do nó de origem.
        target: ID ou label do nó de destino.

    Returns:
        Sequência de nós que conectam source a target, ou mensagem de erro se não existe.
    """
    try:
        workspace_id = _active_workspace_id(config)
        if not workspace_id:
            return "Erro: nenhum workspace ativo."

        from backend.services.workspace import workspace_registry

        ws = workspace_registry.get(workspace_id)
        if ws is None:
            return "Erro: workspace não encontrado."

        from pathlib import Path

        graph_file = Path(ws.cwd) / ".vectora/graph/graph.json"
        if not graph_file.exists():
            return "Grafo não encontrado. Execute build_knowledge_graph primeiro."

        data = json.loads(graph_file.read_text(encoding="utf-8"))
        nodes: list[dict] = data.get("nodes", [])
        edges: list[dict] = data.get("edges", [])

        def _resolve_id(query: str) -> str | None:
            exact = next((n for n in nodes if n.get("id") == query), None)
            if exact:
                return str(exact.get("id"))
            by_label = next((n for n in nodes if n.get("label") == query), None)
            return str(by_label.get("id")) if by_label else None

        src_id = _resolve_id(source)
        tgt_id = _resolve_id(target)
        if src_id is None:
            return f"Nó de origem '{source}' não encontrado."
        if tgt_id is None:
            return f"Nó de destino '{target}' não encontrado."

        import networkx as nx

        graph = nx.Graph()
        for n in nodes:
            graph.add_node(n.get("id"))
        for e in edges:
            graph.add_edge(e.get("source"), e.get("target"))

        try:
            path_ids: list[str] = nx.shortest_path(graph, src_id, tgt_id)
        except nx.NetworkXNoPath:
            return f"Não existe caminho entre '{source}' e '{target}'."
        except nx.NodeNotFound as exc:
            return f"Nó não encontrado no grafo: {exc}"

        id_to_label = {n.get("id"): n.get("label", n.get("id", "")) for n in nodes}
        path_labels = [id_to_label.get(p, p) for p in path_ids]
        return f"Caminho ({len(path_ids)} nós): {' → '.join(path_labels)}"

    except Exception as exc:
        logger.exception("graph: falha em graph_path")
        return f"Erro ao buscar caminho: {exc}"
