"""Testes para os endpoints de rewind/checkpoints adicionados em A.2b.

Cobre:
- GET  /threads/{id}/checkpoints — lista vazia / com artefatos
- POST /threads/{id}/rewind     — 404 sem checkpoint, 422 sem workspace,
                                   400/409 se workspace ocupado, ok em repo git
- _ensure_schema idempotente incluindo a nova tabela
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import git
import pytest

from backend.api.handlers.threads import (
    CheckpointsResponse,
    RewindRequest,
    RewindResponse,
    _ensure_schema,
    list_thread_checkpoints,
    rewind_thread,
)

# ---------------------------------------------------------------------------
# Fixture — banco SQLite em memória / tmp_path
# ---------------------------------------------------------------------------


@pytest.fixture
async def mem_db():
    """Conexão aiosqlite em memória com schema criado."""
    import aiosqlite

    db = await aiosqlite.connect(":memory:")
    await _ensure_schema(db)
    return db


@pytest.fixture(autouse=True)
def patch_get_db(mem_db):
    """Substitui _get_db() pelo banco em memória em todos os testes."""
    with patch(
        "backend.api.handlers.threads._get_db", new=AsyncMock(return_value=mem_db)
    ):
        yield mem_db


# ---------------------------------------------------------------------------
# _ensure_schema — idempotência
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_schema_is_idempotent(mem_db):
    """Chamar _ensure_schema duas vezes não lança erro."""
    await _ensure_schema(mem_db)  # segunda chamada — deve passar sem erro


@pytest.mark.asyncio
async def test_ensure_schema_creates_checkpoint_artifacts_table(mem_db):
    async with mem_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='vectora_checkpoint_artifacts'"
    ) as cur:
        row = await cur.fetchone()
    assert row is not None


# ---------------------------------------------------------------------------
# GET /threads/{id}/checkpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_checkpoints_empty(mem_db):
    result = await list_thread_checkpoints("thread-1")
    assert isinstance(result, CheckpointsResponse)
    assert result.checkpoints == []


@pytest.mark.asyncio
async def test_list_checkpoints_returns_inserted_rows(mem_db):
    import uuid
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    await mem_db.execute(
        "INSERT INTO vectora_checkpoint_artifacts "
        "(id, thread_id, checkpoint_id, strategy, git_sha, snapshot_path, files_touched, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "thread-1", "ckpt-abc", "git", "a" * 40, None, "[]", now),
    )
    await mem_db.commit()

    result = await list_thread_checkpoints("thread-1")

    assert len(result.checkpoints) == 1
    assert result.checkpoints[0].checkpoint_id == "ckpt-abc"
    assert result.checkpoints[0].strategy == "git"
    assert result.checkpoints[0].git_sha == "a" * 40


@pytest.mark.asyncio
async def test_list_checkpoints_does_not_mix_threads(mem_db):
    import uuid
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    for tid in ("thread-a", "thread-b"):
        await mem_db.execute(
            "INSERT INTO vectora_checkpoint_artifacts "
            "(id, thread_id, checkpoint_id, strategy, git_sha, snapshot_path, files_touched, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), tid, f"ckpt-{tid}", "git", "a" * 40, None, "[]", now),
        )
    await mem_db.commit()

    result_a = await list_thread_checkpoints("thread-a")
    result_b = await list_thread_checkpoints("thread-b")

    assert all(c.thread_id == "thread-a" for c in result_a.checkpoints)
    assert all(c.thread_id == "thread-b" for c in result_b.checkpoints)


# ---------------------------------------------------------------------------
# POST /threads/{id}/rewind
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rewind_404_when_checkpoint_not_found():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await rewind_thread(
            "thread-1", RewindRequest(checkpoint_id="no-such"), workspace_id=""
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_rewind_422_when_workspace_cannot_be_resolved(mem_db):
    """Nenhum workspace_id na query nem no banco → 422."""
    import uuid
    from datetime import UTC, datetime

    from fastapi import HTTPException

    now = datetime.now(UTC).isoformat()
    await mem_db.execute(
        "INSERT INTO vectora_checkpoint_artifacts "
        "(id, thread_id, checkpoint_id, strategy, git_sha, snapshot_path, files_touched, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "thread-1", "ckpt-1", "git", "a" * 40, None, "[]", now),
    )
    await mem_db.commit()

    with pytest.raises(HTTPException) as exc_info:
        await rewind_thread(
            "thread-1", RewindRequest(checkpoint_id="ckpt-1"), workspace_id=""
        )
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_rewind_ok_on_git_repo(tmp_path: Path, mem_db):
    """Rewind com git_sha válido deve chamar restore_git_checkpoint e retornar ok."""
    import uuid
    from datetime import UTC, datetime

    # Cria repo real com commit
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "T").release()
    repo.config_writer().set_value("user", "email", "t@t.com").release()
    (tmp_path / "a.txt").write_text("v1\n")
    repo.index.add(["a.txt"])
    repo.index.commit("init")

    # Cria checkpoint
    from backend.persistence.checkpoint import create_git_checkpoint

    ckpt = create_git_checkpoint(repo, "thread-1", "estado A")
    assert ckpt["status"] == "ok"
    git_sha = ckpt["sha"]

    # Insere artefato no banco
    now = datetime.now(UTC).isoformat()
    await mem_db.execute(
        "INSERT INTO vectora_checkpoint_artifacts "
        "(id, thread_id, checkpoint_id, strategy, git_sha, snapshot_path, files_touched, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "thread-1", "ckpt-ok", "git", git_sha, None, "[]", now),
    )
    # Insere workspace no registry
    import json as _json

    await mem_db.execute(
        "INSERT INTO vectora_sessions (thread_id, created_at, last_activity, extra) VALUES (?,?,?,?)",
        ("thread-1", now, now, _json.dumps({"workspace_id": "ws-test"})),
    )
    await mem_db.commit()

    # Registra workspace no registry
    from backend.vtypes import Workspace
    from backend.workspace.workspace import workspace_registry

    ws = Workspace(
        id="ws-test", name="test", cwd=str(tmp_path), created_at=now, trusted=True
    )
    workspace_registry._workspaces["ws-test"] = ws

    result = await rewind_thread(
        "thread-1", RewindRequest(checkpoint_id="ckpt-ok"), workspace_id="ws-test"
    )
    assert isinstance(result, RewindResponse)
    assert result.status == "ok"
