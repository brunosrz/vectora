"""Tool para atualizar itens de plano em artifacts markdown.

Permite ao agente marcar etapas de um plano como pending, in_progress,
done ou failed — refletindo o estado real de execução no Plan tab.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Annotated

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

logger = logging.getLogger(__name__)

VALID_STATUSES = {"pending", "in_progress", "done", "failed"}

_STATUS_MARKER = {
    "done": "- [x]",
    "failed": "- [!]",
    "pending": "- [ ]",
    "in_progress": "- [~]",
}


def _artifacts_dir(session_id: str) -> Path:
    """Pasta de artifacts da sessão. Sanitiza o session_id (sem traversal)."""
    safe = session_id.replace("/", "").replace("\\", "").replace("..", "")
    return Path.home() / ".vectora" / "artifacts" / safe


def _find_and_replace_item(content: str, item: str, status: str) -> tuple[bool, str]:
    """Substitui a primeira linha que contenha `item` com o marcador do status.

    Retorna (encontrado, novo_conteúdo).
    """
    marker = _STATUS_MARKER[status]
    lines = content.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if item in line and re.search(r"- \[[ x!~]\]", line):
            updated = re.sub(r"- \[[ x!~]\]", marker, line, count=1)
            if status == "in_progress":
                updated = re.sub(r"(- \[~\]\s*)(~>)?\s*", r"\1~> ", updated)
            lines[i] = updated
            return True, "".join(lines)
    return False, content


@tool(
    extras={
        "invalidates": ["plan"],
        "destructive": False,
        "category": "workspace",
        "icon": "check-square",
    }
)
async def update_plan_item(
    artifact_slug: str,
    item: str,
    status: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Atualiza o status de um item de plano em um artifact markdown.

    Marca checkboxes da sessão atual: pending → done, in_progress ou failed.
    Use para refletir o progresso real de execução no Plan tab em tempo real.

    Args:
        artifact_slug: Nome do artifact sem extensão (ex: "plano-sprint-1")
        item: Texto do item a atualizar (substring é suficiente)
        status: Novo status — pending | in_progress | done | failed
    """
    try:
        if status not in VALID_STATUSES:
            return json.dumps(
                {
                    "status": "error",
                    "error": f"status '{status}' inválido. Use: {sorted(VALID_STATUSES)}",
                }
            )

        configurable = (config or {}).get("configurable") or {}
        session_id = configurable.get("thread_id", "default")
        artifact_path = _artifacts_dir(session_id) / f"{artifact_slug}.md"

        if not artifact_path.exists():
            return json.dumps({"status": "not_found", "artifact": artifact_slug})

        content = artifact_path.read_text(encoding="utf-8")
        found, new_content = _find_and_replace_item(content, item, status)

        if not found:
            return json.dumps({"status": "not_found", "item": item})

        artifact_path.write_text(new_content, encoding="utf-8")
        return json.dumps({"status": "updated", "item": item, "new_status": status})

    except Exception as e:
        logger.exception("update_plan_item: erro inesperado slug=%s", artifact_slug)
        return json.dumps({"status": "error", "error": str(e)})
