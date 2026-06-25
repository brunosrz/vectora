"""Tests TDD para update_plan_item (FASE 2.3).

Cobre: atualização de itens em artifacts de plano, item não encontrado,
artifact inexistente, invalidação de workbench_invalidate metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from backend.tools.plans import update_plan_item


def _cfg(thread_id: str = "t1", workspace_id: str = "ws1") -> Any:
    return {"configurable": {"thread_id": thread_id, "workspace_id": workspace_id}}


# ---------------------------------------------------------------------------
# Atualização de item em markdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_marca_item_como_done(tmp_path: Path) -> None:
    """Item pendente → done atualiza checkbox no markdown."""
    artifact = tmp_path / "t1" / "plano.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Plano\n\n- [ ] Implementar auth\n- [ ] Testes\n")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "backend.tools.plans._artifacts_dir",
            lambda session_id: tmp_path / session_id,
        )
        result = json.loads(
            await update_plan_item.ainvoke(
                {
                    "artifact_slug": "plano",
                    "item": "Implementar auth",
                    "status": "done",
                },
                _cfg(),
            )
        )

    assert result["status"] == "updated"
    assert "Implementar auth" in result["item"]
    content = artifact.read_text()
    assert "- [x] Implementar auth" in content
    assert "- [ ] Testes" in content


@pytest.mark.asyncio
async def test_marca_item_como_in_progress(tmp_path: Path) -> None:
    """status=in_progress coloca prefixo ~> no item."""
    artifact = tmp_path / "t1" / "plano.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("- [ ] Implementar login\n")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "backend.tools.plans._artifacts_dir",
            lambda session_id: tmp_path / session_id,
        )
        result = json.loads(
            await update_plan_item.ainvoke(
                {
                    "artifact_slug": "plano",
                    "item": "Implementar login",
                    "status": "in_progress",
                },
                _cfg(),
            )
        )

    assert result["status"] == "updated"
    content = artifact.read_text()
    assert "~>" in content or "in_progress" in content.lower() or "🔄" in content


@pytest.mark.asyncio
async def test_item_nao_encontrado_retorna_erro(tmp_path: Path) -> None:
    """Item que não existe no artifact → status: not_found."""
    artifact = tmp_path / "t1" / "plano.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("- [ ] Outro item\n")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "backend.tools.plans._artifacts_dir",
            lambda session_id: tmp_path / session_id,
        )
        result = json.loads(
            await update_plan_item.ainvoke(
                {
                    "artifact_slug": "plano",
                    "item": "Item inexistente",
                    "status": "done",
                },
                _cfg(),
            )
        )

    assert result["status"] == "not_found"


@pytest.mark.asyncio
async def test_artifact_inexistente_retorna_erro(tmp_path: Path) -> None:
    """Artifact que não existe → status: not_found."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "backend.tools.plans._artifacts_dir",
            lambda session_id: tmp_path / session_id,
        )
        result = json.loads(
            await update_plan_item.ainvoke(
                {
                    "artifact_slug": "inexistente",
                    "item": "Algo",
                    "status": "done",
                },
                _cfg(),
            )
        )

    assert result["status"] == "not_found"


@pytest.mark.asyncio
async def test_status_invalido_retorna_erro(tmp_path: Path) -> None:
    """Status inválido → status: error (não propaga exception)."""
    artifact = tmp_path / "t1" / "plano.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("- [ ] Item\n")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "backend.tools.plans._artifacts_dir",
            lambda session_id: tmp_path / session_id,
        )
        result = json.loads(
            await update_plan_item.ainvoke(
                {
                    "artifact_slug": "plano",
                    "item": "Item",
                    "status": "flying",
                },
                _cfg(),
            )
        )

    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Metadata invariantes
# ---------------------------------------------------------------------------


def test_update_plan_item_nao_e_destrutivo() -> None:
    extras = getattr(update_plan_item, "extras", {}) or {}
    assert extras.get("destructive") is False


def test_update_plan_item_invalida_plan() -> None:
    extras = getattr(update_plan_item, "extras", {}) or {}
    assert "plan" in extras.get("invalidates", [])
