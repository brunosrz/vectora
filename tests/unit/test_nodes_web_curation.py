"""Tests for vectora/nodes/web_curation.py — gate de curadoria do RAG (A5.2).

O gate impede que resultados web irrelevantes contaminem o RAG. Os testes
mockam reranker e LLM judge — o foco é a lógica de aprovação/rejeição.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from vectora.nodes.web_curation import (
    curate_and_enqueue,
    curate_web_results,
)
from vectora.types import WebResultVerdict


def _results() -> list[dict]:
    """Dois resultados: o repo correto do brunosrz e um homônimo aleatório."""
    return [
        {
            "content": "framework de ability system do brunosrz",
            "url": "https://github.com/brunosrz/AbilitySystem",
            "title": "AbilitySystem",
        },
        {
            "content": "asset aleatório de gameplay, projeto homônimo",
            "url": "https://godotengine.org/asset-library/x",
            "title": "Godot Gameplay Systems",
        },
    ]


class TestCurateWebResults:
    @pytest.mark.asyncio
    async def test_reranker_filters_below_threshold(self):
        results = _results()
        # result[1] tem score abaixo do threshold (0.5) → cortado antes do judge.
        scored = [(results[0], 0.9), (results[1], 0.1)]
        verdicts = {0: WebResultVerdict(index=0, keep=True, reason="repo correto")}
        with patch(
            "vectora.nodes.web_curation._rerank_results", new_callable=AsyncMock
        ) as mr:
            with patch(
                "vectora.nodes.web_curation._judge", new_callable=AsyncMock
            ) as mj:
                mr.return_value = scored
                mj.return_value = verdicts
                approved, rejected = await curate_web_results(results, "godot ability")

        assert len(approved) == 1
        assert approved[0]["url"] == results[0]["url"]
        assert len(rejected) == 1
        # O judge só avalia os sobreviventes do reranker (1, não 2).
        assert mj.await_args is not None
        assert len(mj.await_args.args[0]) == 1

    @pytest.mark.asyncio
    async def test_judge_rejects_homonym(self):
        results = _results()
        # Ambos passam o reranker; o judge é quem separa o homônimo.
        scored = [(results[0], 0.8), (results[1], 0.75)]
        verdicts = {
            0: WebResultVerdict(index=0, keep=True, reason="repositório correto"),
            1: WebResultVerdict(
                index=1, keep=False, reason="projeto homônimo diferente"
            ),
        }
        with patch(
            "vectora.nodes.web_curation._rerank_results", new_callable=AsyncMock
        ) as mr:
            with patch(
                "vectora.nodes.web_curation._judge", new_callable=AsyncMock
            ) as mj:
                mr.return_value = scored
                mj.return_value = verdicts
                approved, rejected = await curate_web_results(results, "q")

        assert len(approved) == 1
        assert approved[0]["url"] == results[0]["url"]
        assert any("homônimo" in r["curation_reason"] for r in rejected)

    @pytest.mark.asyncio
    async def test_judge_failure_rejects_all(self):
        # Fail-safe: judge devolve dict vazio (falhou) → nada é aprovado.
        results = _results()
        with patch(
            "vectora.nodes.web_curation._rerank_results", new_callable=AsyncMock
        ) as mr:
            with patch(
                "vectora.nodes.web_curation._judge", new_callable=AsyncMock
            ) as mj:
                mr.return_value = [(results[0], 0.8)]
                mj.return_value = {}
                approved, rejected = await curate_web_results(results, "q")

        assert approved == []
        assert len(rejected) == 1

    @pytest.mark.asyncio
    async def test_no_survivors_skips_judge(self):
        results = _results()
        with patch(
            "vectora.nodes.web_curation._rerank_results", new_callable=AsyncMock
        ) as mr:
            with patch(
                "vectora.nodes.web_curation._judge", new_callable=AsyncMock
            ) as mj:
                mr.return_value = [(results[0], 0.2), (results[1], 0.1)]
                approved, rejected = await curate_web_results(results, "q")

        assert approved == []
        assert len(rejected) == 2
        mj.assert_not_called()

    @pytest.mark.asyncio
    async def test_kill_switch_approves_all(self):
        results = _results()
        with patch("vectora.nodes.web_curation.settings") as ms:
            ms.web_curation_enabled = False
            approved, rejected = await curate_web_results(results, "q")
        assert len(approved) == len(results)
        assert rejected == []

    @pytest.mark.asyncio
    async def test_empty_results(self):
        approved, rejected = await curate_web_results([], "q")
        assert approved == []
        assert rejected == []


class TestCurateAndEnqueue:
    @pytest.mark.asyncio
    async def test_enqueues_only_approved(self):
        results = _results()
        approved = [{**results[0], "relevance_score": 0.9, "curation_reason": "ok"}]
        rejected = [{**results[1], "relevance_score": 0.1, "curation_reason": "lixo"}]
        with patch(
            "vectora.nodes.web_curation.curate_web_results", new_callable=AsyncMock
        ) as mc:
            mc.return_value = (approved, rejected)
            with patch("vectora.tools.rag.embedding") as me:
                me.ainvoke = AsyncMock(return_value='{"queue_id": "q1"}')
                formatted_docs, queue_ids = await curate_and_enqueue(results, "q")

        # Contexto imediato do turno = todos os resultados (transiente).
        assert len(formatted_docs) == 2
        # Persistência no LanceDB = apenas o aprovado.
        assert queue_ids == ["q1"]
        assert me.ainvoke.await_count == 1

    @pytest.mark.asyncio
    async def test_nothing_approved_persists_nothing(self):
        results = _results()
        rejected = [{**r, "curation_reason": "rejeitado"} for r in results]
        with patch(
            "vectora.nodes.web_curation.curate_web_results", new_callable=AsyncMock
        ) as mc:
            mc.return_value = ([], rejected)
            with patch("vectora.tools.rag.embedding") as me:
                me.ainvoke = AsyncMock()
                formatted_docs, queue_ids = await curate_and_enqueue(results, "q")

        assert queue_ids == []
        assert me.ainvoke.await_count == 0
        # O contexto imediato ainda tem todos os resultados.
        assert len(formatted_docs) == 2
