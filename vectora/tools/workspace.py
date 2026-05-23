"""Workspace tools: describe, list, bucket summary.

Ferramentas que expõem o estado do WorkspaceRegistry para os agents,
permitindo que o orchestrator e search respondam perguntas sobre o
conhecimento indexado sem precisar disparar uma busca vetorial.
"""

from __future__ import annotations

import json
import logging

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig

from vectora.types import Workspace

logger = logging.getLogger(__name__)


def _resolve_workspace(
    workspace_id: str | None, config: RunnableConfig | None
) -> Workspace | None:
    """Resolve workspace_id → Workspace, priorizando config quando id é None."""
    from vectora.services.workspace import workspace_registry

    wid = workspace_id
    if wid is None and config is not None:
        wid = (config.get("configurable") or {}).get("workspace_id")

    if wid:
        ws = workspace_registry.get(wid)
        if ws is not None:
            return ws

    # Fallback: workspace do diretório atual
    return workspace_registry.get_or_create()


@tool(extras={"render_hint": "markdown"})
async def workspace_describe(
    workspace_id: str | None = None,
    config: RunnableConfig | None = None,
) -> str:
    """Descreve o workspace ativo: base de conhecimento indexada, buckets e tópicos.

    Retorna o conteúdo do MANIFEST.md gerado pelo curator após ingestão de docs.
    Use para responder "o que você sabe sobre este projeto?" ou "o que está indexado?".

    Args:
        workspace_id: ID do workspace (usa o workspace do diretório atual se omitido)
    """
    ws = _resolve_workspace(workspace_id, config)
    if ws is None:
        return json.dumps(
            {"status": "not_found", "message": "Nenhum workspace encontrado."}
        )

    manifest_path = ws.manifest_path()
    if not manifest_path.exists():
        return json.dumps(
            {
                "status": "no_manifest",
                "workspace_id": ws.id,
                "name": ws.name,
                "cwd": ws.cwd,
                "message": (
                    "Manifest ainda não gerado. Use /rag add <pasta> para indexar "
                    "documentos. O curator cria o MANIFEST.md automaticamente após "
                    "a ingestão."
                ),
            }
        )

    try:
        content = manifest_path.read_text(encoding="utf-8")
        return json.dumps(
            {
                "status": "success",
                "workspace_id": ws.id,
                "name": ws.name,
                "manifest": content,
            }
        )
    except Exception as e:
        logger.exception("workspace_describe: erro ao ler manifest %s", ws.id)
        return json.dumps({"status": "error", "error": str(e)})


@tool(extras={"render_hint": "table"})
async def workspace_list() -> str:
    """Lista todos os workspaces Vectora registrados.

    Mostra id, nome, diretório e versão do manifest de cada workspace.
    Útil para auditar projetos indexados ou alternar contextos.
    """
    from vectora.services.workspace import workspace_registry

    workspaces = workspace_registry.list_all()
    if not workspaces:
        return json.dumps(
            {"status": "empty", "message": "Nenhum workspace registrado ainda."}
        )

    items = [
        {
            "id": ws.id,
            "name": ws.name,
            "cwd": ws.cwd,
            "created_at": ws.created_at,
            "manifest_version": ws.manifest_version,
            "has_manifest": ws.manifest_path().exists(),
            "bucket_count": len(ws.bucket_names),
        }
        for ws in workspaces
    ]
    return json.dumps({"status": "success", "workspaces": items, "count": len(items)})


@tool(extras={"render_hint": "markdown"})
async def bucket_summary(
    bucket: str,
    workspace_id: str | None = None,
    config: RunnableConfig | None = None,
) -> str:
    """Retorna o resumo de um bucket específico do workspace.

    Cada bucket (code, docs, notes, web_cache) tem seu próprio
    buckets/<bucket>.md com resumo do que foi indexado.

    Args:
        bucket: Nome do bucket (ex: "code", "docs", "notes", "web_cache")
        workspace_id: ID do workspace (usa o ativo se omitido)
    """
    ws = _resolve_workspace(workspace_id, config)
    if ws is None:
        return json.dumps(
            {"status": "not_found", "message": "Nenhum workspace encontrado."}
        )

    bucket_path = ws.bucket_manifest_path(bucket)
    if not bucket_path.exists():
        return json.dumps(
            {
                "status": "no_manifest",
                "bucket": bucket,
                "workspace_id": ws.id,
                "message": (
                    f"Nenhum manifest para o bucket '{bucket}'. "
                    "Indexe documentos neste bucket primeiro."
                ),
            }
        )

    try:
        content = bucket_path.read_text(encoding="utf-8")
        return json.dumps(
            {
                "status": "success",
                "bucket": bucket,
                "workspace_id": ws.id,
                "summary": content,
            }
        )
    except Exception as e:
        logger.exception("bucket_summary: erro ao ler manifest bucket=%s", bucket)
        return json.dumps({"status": "error", "error": str(e)})
