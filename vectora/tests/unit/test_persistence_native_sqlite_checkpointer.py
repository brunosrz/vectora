"""Exercício real de ``VectoraSqliteSaver`` — antes desta auditoria, o
checkpointer nativo (já em produção via ``agent_factory.py``) não tinha
nenhum teste que de fato gravasse/lesse checkpoint: a fixture que deveria
fazer isso (``backend.testing.fixtures.checkpointer``) nunca era
importada por nenhum teste."""

from __future__ import annotations

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import Checkpoint

from backend.persistence.native.sqlite_checkpointer import (
    VectoraSqliteSaver,
    _metadata_where,
)
from backend.storage.sqlite.pool import AsyncConnectionPool


@pytest.fixture
async def saver(tmp_path):
    pool = AsyncConnectionPool(str(tmp_path / "checkpoints.db"), min_size=1, max_size=2)
    await pool.open()
    saver = VectoraSqliteSaver(pool)
    await saver.setup()
    try:
        yield saver
    finally:
        await pool.close()


def _config(thread_id: str, checkpoint_id: str | None = None) -> RunnableConfig:
    configurable: dict = {"thread_id": thread_id, "checkpoint_ns": ""}
    if checkpoint_id is not None:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable}


def _checkpoint(checkpoint_id: str, channel_values: dict | None = None) -> Checkpoint:
    return {
        "v": 1,
        "id": checkpoint_id,
        "ts": "2026-01-01T00:00:00+00:00",
        "channel_values": channel_values or {},
        "channel_versions": {},
        "versions_seen": {},
        "updated_channels": None,
    }


class TestAputAgetTuple:
    async def test_round_trip_grava_e_le_o_checkpoint(self, saver: VectoraSqliteSaver):
        checkpoint = _checkpoint("ckpt-1", {"messages": ["oi"]})
        saved_config = await saver.aput(
            _config("thread-1"), checkpoint, {"source": "loop", "step": 1}, {}
        )

        assert saved_config["configurable"]["checkpoint_id"] == "ckpt-1"

        tuple_ = await saver.aget_tuple(_config("thread-1"))
        assert tuple_ is not None
        assert tuple_.checkpoint["channel_values"]["messages"] == ["oi"]
        assert tuple_.metadata["source"] == "loop"

    async def test_thread_sem_checkpoint_retorna_none(self, saver: VectoraSqliteSaver):
        assert await saver.aget_tuple(_config("thread-inexistente")) is None

    async def test_aget_tuple_com_checkpoint_id_especifico(
        self, saver: VectoraSqliteSaver
    ):
        for i in (1, 2):
            await saver.aput(
                _config("thread-2"),
                _checkpoint(f"ckpt-{i}"),
                {"source": "loop", "step": i},
                {},
            )

        tuple_ = await saver.aget_tuple(_config("thread-2", "ckpt-1"))
        assert tuple_ is not None
        assert tuple_.config["configurable"]["checkpoint_id"] == "ckpt-1"


class TestAlist:
    async def test_alist_ordena_do_mais_recente_pro_mais_antigo(
        self, saver: VectoraSqliteSaver
    ):
        for i in (1, 2, 3):
            await saver.aput(
                _config("thread-3"),
                _checkpoint(f"ckpt-{i}"),
                {"source": "loop", "step": i},
                {},
            )

        checkpoints = [c async for c in saver.alist(_config("thread-3"))]
        ids = [c.config["configurable"]["checkpoint_id"] for c in checkpoints]
        assert ids == ["ckpt-3", "ckpt-2", "ckpt-1"]

    async def test_alist_respeita_limit(self, saver: VectoraSqliteSaver):
        for i in (1, 2, 3):
            await saver.aput(
                _config("thread-4"),
                _checkpoint(f"ckpt-{i}"),
                {"source": "loop", "step": i},
                {},
            )

        checkpoints = [c async for c in saver.alist(_config("thread-4"), limit=1)]
        assert len(checkpoints) == 1

    async def test_alist_filtra_por_metadata(self, saver: VectoraSqliteSaver):
        await saver.aput(
            _config("thread-5"),
            _checkpoint("a"),
            {"source": "input", "step": 1},
            {},
        )
        await saver.aput(
            _config("thread-5"),
            _checkpoint("b"),
            {"source": "loop", "step": 2},
            {},
        )

        checkpoints = [
            c async for c in saver.alist(_config("thread-5"), filter={"source": "loop"})
        ]
        assert len(checkpoints) == 1
        assert checkpoints[0].metadata["source"] == "loop"


class TestAputWrites:
    async def test_writes_ficam_associadas_ao_checkpoint(
        self, saver: VectoraSqliteSaver
    ):
        await saver.aput(
            _config("thread-6"),
            _checkpoint("ckpt-1"),
            {"source": "loop", "step": 1},
            {},
        )
        await saver.aput_writes(
            _config("thread-6", "ckpt-1"),
            [("messages", "valor-1"), ("other", "valor-2")],
            task_id="task-1",
        )

        tuple_ = await saver.aget_tuple(_config("thread-6", "ckpt-1"))
        assert tuple_ is not None
        canais = {w[1] for w in tuple_.pending_writes or []}
        assert canais == {"messages", "other"}

    async def test_segunda_tentativa_da_mesma_task_nao_duplica_write_regular(
        self, saver: VectoraSqliteSaver
    ):
        await saver.aput(
            _config("thread-7"),
            _checkpoint("ckpt-1"),
            {"source": "loop", "step": 1},
            {},
        )
        for _ in range(2):
            await saver.aput_writes(
                _config("thread-7", "ckpt-1"),
                [("messages", "valor-original")],
                task_id="task-1",
            )

        tuple_ = await saver.aget_tuple(_config("thread-7", "ckpt-1"))
        assert tuple_ is not None
        assert len(tuple_.pending_writes or []) == 1


class TestAdeleteThread:
    async def test_apaga_checkpoints_e_writes_da_thread(
        self, saver: VectoraSqliteSaver
    ):
        await saver.aput(
            _config("thread-8"),
            _checkpoint("ckpt-1"),
            {"source": "loop", "step": 1},
            {},
        )
        await saver.aput_writes(
            _config("thread-8", "ckpt-1"), [("messages", "x")], task_id="task-1"
        )

        await saver.adelete_thread("thread-8")

        assert await saver.aget_tuple(_config("thread-8")) is None
        checkpoints = [c async for c in saver.alist(_config("thread-8"))]
        assert checkpoints == []


class TestMetadataWhereGuardDeSeguranca:
    def test_chave_valida_gera_predicado(self):
        predicates, values = _metadata_where({"source": "loop"})
        assert len(predicates) == 1
        assert values == ["loop"]

    def test_chave_com_caractere_de_injecao_e_rejeitada(self):
        """Guard contra SQL injection via nome de campo: só
        [a-zA-Z0-9_.-] é aceito — sem isso, uma chave maliciosa entraria
        direto na string do `json_extract` sem passar por parâmetro."""
        with pytest.raises(ValueError, match="Filter key inválida"):
            _metadata_where({"source; DROP TABLE checkpoints;--": "x"})

    def test_chave_com_espaco_e_rejeitada(self):
        with pytest.raises(ValueError, match="Filter key inválida"):
            _metadata_where({"has space": "x"})
