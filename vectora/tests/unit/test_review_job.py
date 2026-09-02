"""Testes para backend/services/gateway/review_job.py — execução da
revisão de PR self-hosted (gh-bot), disparada por um `review_job` recebido
pelo túnel do gateway (ver backend/services/gateway/__init__.py::_dispatch).
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.engine import conversation_loop
from backend.engine.hitl import ApprovalGate
from backend.llm import fallback_chat_client
from backend.persistence.native.session_store import SessionStore
from backend.services import agent_factory
from backend.services.agent_factory import NativeAgent
from backend.services.gateway import review_job
from backend.storage.sqlite.pool import AsyncConnectionPool
from backend.tools.registry import ToolRegistry
from backend.vtypes.message import VMessageChunk


@pytest.fixture
async def native_session_store(tmp_path):
    pool = AsyncConnectionPool(
        str(tmp_path / "review-job-sessions.db"), min_size=1, max_size=2
    )
    await pool.open()
    store = SessionStore(pool)
    await store.setup()
    try:
        yield store
    finally:
        await pool.close()


def _texto_chunk(texto: str) -> VMessageChunk:
    return VMessageChunk(delta_text=texto)


class _ScriptedChatClient:
    """Mesmo fake de test_cli_run_task.py — cada `astream` consome o
    próximo turno pré-roteirizado."""

    def __init__(self, turnos: list[list[VMessageChunk]] | None = None) -> None:
        self._turnos = turnos or []
        self.chamadas = 0
        self.model_ids: list[str] = []

    async def astream(self, messages, *, tools=None, temperature=None, max_tokens=None):
        self.chamadas += 1
        turno = self._turnos[self.chamadas - 1]
        for chunk in turno:
            yield chunk

    async def agenerate(
        self, messages, *, tools=None, temperature=None, max_tokens=None
    ):
        msg = "não usado (astream-only)"
        raise NotImplementedError(msg)


def _patch_native_engine(
    monkeypatch,
    *,
    session_store: SessionStore,
    chat_client: Any = None,
) -> _ScriptedChatClient:
    native_agent = NativeAgent(
        tool_registry=ToolRegistry(), subagent_catalog={}, system_prompt="system"
    )
    client = chat_client or _ScriptedChatClient([[_texto_chunk("ok")]])

    async def _fake_get_native_agent(
        user_id: str | None = None,
        chat_mode: bool = False,
        workspace_id: str | None = None,
    ) -> NativeAgent:
        return native_agent

    async def _fake_get_session_store() -> SessionStore:
        return session_store

    approval_gate = ApprovalGate(session_store)

    async def _fake_get_approval_gate() -> ApprovalGate:
        return approval_gate

    async def _fake_get_store() -> None:
        return None

    monkeypatch.setattr(agent_factory, "get_native_agent", _fake_get_native_agent)
    monkeypatch.setattr(agent_factory, "get_session_store", _fake_get_session_store)
    monkeypatch.setattr(agent_factory, "get_approval_gate", _fake_get_approval_gate)
    monkeypatch.setattr(agent_factory, "get_store", _fake_get_store)

    def _fake_chat_client_ctor(primary_model_id: str = "") -> _ScriptedChatClient:
        client.model_ids.append(primary_model_id)
        return client

    monkeypatch.setattr(
        fallback_chat_client, "FallbackChatClient", _fake_chat_client_ctor
    )
    return client


class TestBuildTask:
    def test_monta_o_prompt_com_diff_e_metadata(self) -> None:
        task = review_job._build_task(
            "diff --git a/a.py\n+print(1)", {"pr_number": "42", "repo": "x/y"}
        )
        assert "diff --git a/a.py" in task
        assert "pr_number: 42" in task
        assert "repo: x/y" in task

    def test_erro_borda_metadata_vazia_nao_quebra(self) -> None:
        task = review_job._build_task("diff x", {})
        assert "diff x" in task


class TestRunReviewJob:
    async def test_erro_borda_sem_vectora_model_levanta_erro_tipado(
        self, monkeypatch
    ) -> None:
        monkeypatch.delenv("VECTORA_MODEL", raising=False)
        with pytest.raises(review_job.ReviewJobModelNotConfiguredError):
            await review_job.run_review_job("diff x", {})

    async def test_roda_a_revisao_e_devolve_o_texto_final(
        self, native_session_store, monkeypatch
    ) -> None:
        monkeypatch.setenv("VECTORA_MODEL", "google_genai:gemini-flash")
        client = _ScriptedChatClient([[_texto_chunk("LGTM, só um nit.")]])
        _patch_native_engine(
            monkeypatch, session_store=native_session_store, chat_client=client
        )

        texto = await review_job.run_review_job(
            "diff --git a/a.py\n+print(1)", {"pr_number": "7"}
        )

        assert texto == "LGTM, só um nit."
        assert client.chamadas == 1
        assert client.model_ids == ["google_genai:gemini-flash"]

    async def test_erro_borda_sem_mensagem_final_devolve_string_vazia(
        self, native_session_store, monkeypatch
    ) -> None:
        monkeypatch.setenv("VECTORA_MODEL", "google_genai:gemini-flash")
        from backend.engine.conversation_loop import LoopResult

        async def _fake_run_conversation(**kwargs):
            return LoopResult(stopped_reason="stop", final_message=None)

        _patch_native_engine(monkeypatch, session_store=native_session_store)
        monkeypatch.setattr(
            conversation_loop, "run_conversation", _fake_run_conversation
        )

        texto = await review_job.run_review_job("diff x", {})

        assert texto == ""

    async def test_erro_de_execucao_se_propaga_pro_chamador(
        self, native_session_store, monkeypatch
    ) -> None:
        """`run_review_job` não engole erro nenhum — quem decide como
        reportar (postar `error` em vez de `review_text`) é o chamador
        (`GatewayClient._handle_review_job`), não esta função."""
        monkeypatch.setenv("VECTORA_MODEL", "google_genai:gemini-flash")

        async def _fake_run_conversation(**kwargs):
            msg = "provider indisponível"
            raise ConnectionError(msg)

        _patch_native_engine(monkeypatch, session_store=native_session_store)
        monkeypatch.setattr(
            conversation_loop, "run_conversation", _fake_run_conversation
        )

        with pytest.raises(ConnectionError, match="provider indisponível"):
            await review_job.run_review_job("diff x", {})
