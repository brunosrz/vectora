"""Tests da injeção do bloco ``user_context`` no orchestrator.

Cobre os 4 sites que constroem o payload final ao usuário em
``src/agents/orchestrator.py``:

1. ``orchestrator()`` — caminho de resposta direta (``_ORCHESTRATOR_PROMPT``).
2. ``_synthesize_after_coder`` — síntese após o Coder Agent.
3. ``_synthesize_after_search`` — síntese após o Search Agent.
4. ``_synthesize_after_parallel`` — síntese após dispatch paralelo (C5).

Cada teste mocka o LLM correspondente, executa o nó e inspeciona os
``messages`` enviados ao ``ainvoke`` para garantir que:

- Quando ``configurable`` tem ``user_name``/``language``, há **um**
  ``SystemMessage`` com ``name="user_context"`` contendo nome + locale.
- Quando ``configurable`` é vazio, **nenhum** SystemMessage com esse
  name aparece (não inserimos bloco vazio).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.constants import END

from src.agents.orchestrator import (
    _synthesize_after_coder,
    _synthesize_after_parallel,
    _synthesize_after_search,
    orchestrator,
)
from src.types import CoderResult, OrchestratorDecision, SearchResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cfg_with_user_ctx(
    name: str = "Bruno Soares", language: str = "pt_BR"
) -> RunnableConfig:
    return {"configurable": {"user_name": name, "language": language}}


def _cfg_empty() -> RunnableConfig:
    return {"configurable": {}}


def _captured_payload(mock: AsyncMock) -> list:
    """Devolve a lista de messages do primeiro ``ainvoke`` capturado."""
    assert mock.ainvoke.await_args is not None, "ainvoke não foi chamado"
    args, kwargs = mock.ainvoke.await_args
    # Pode vir como posicional ou keyword; ambos os agentes usam posicional.
    return args[0] if args else kwargs.get("input") or kwargs.get("messages")


def _user_context_msg(payload: list) -> SystemMessage | None:
    for m in payload:
        if isinstance(m, SystemMessage) and getattr(m, "name", None) == "user_context":
            return m
    return None


# ---------------------------------------------------------------------------
# Site 1 — orchestrator() (caminho de resposta direta)
# ---------------------------------------------------------------------------


class TestOrchestratorMainPath:
    @pytest.mark.asyncio
    async def test_injects_user_context_when_provided(self):
        state: Any = {
            "messages": [HumanMessage(content="oi")],
            "session_metadata": {},
        }

        fake_decision = OrchestratorDecision(
            action="respond",
            response="``````markdown\nOlá!\n``````",
            reason="saudação",
        )
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(return_value=fake_decision)

        with patch(
            "src.agents.orchestrator._get_orchestrator_llm",
            return_value=fake_llm,
        ):
            cmd = await orchestrator(state, config=_cfg_with_user_ctx())

        assert cmd.goto == END
        payload = _captured_payload(fake_llm)
        user_ctx = _user_context_msg(payload)
        assert user_ctx is not None, (
            "esperava SystemMessage(name='user_context') no payload"
        )
        assert "Bruno Soares" in user_ctx.content
        assert "`pt_BR`" in user_ctx.content

    @pytest.mark.asyncio
    async def test_no_user_context_when_configurable_empty(self):
        """Sem user_name nem language → nenhum bloco user_context no payload."""
        state: Any = {
            "messages": [HumanMessage(content="oi")],
            "session_metadata": {},
        }
        fake_decision = OrchestratorDecision(
            action="respond", response="ok", reason="saudação"
        )
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(return_value=fake_decision)

        with patch(
            "src.agents.orchestrator._get_orchestrator_llm",
            return_value=fake_llm,
        ):
            await orchestrator(state, config=_cfg_empty())

        payload = _captured_payload(fake_llm)
        assert _user_context_msg(payload) is None

    @pytest.mark.asyncio
    async def test_user_context_appears_before_orchestrator_prompt(self):
        """Ordem importa: o bloco do user vem antes do prompt principal."""
        state: Any = {
            "messages": [HumanMessage(content="oi")],
            "session_metadata": {},
        }
        fake_decision = OrchestratorDecision(
            action="respond", response="ok", reason="saudação"
        )
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(return_value=fake_decision)

        with patch(
            "src.agents.orchestrator._get_orchestrator_llm",
            return_value=fake_llm,
        ):
            await orchestrator(state, config=_cfg_with_user_ctx())

        payload = _captured_payload(fake_llm)
        # Acha o índice do user_context e o índice do SystemMessage principal
        # (sem name="user_context" e que mencione 'Orchestrator' do
        # _ORCHESTRATOR_PROMPT).
        ctx_idx = next(
            i
            for i, m in enumerate(payload)
            if isinstance(m, SystemMessage)
            and getattr(m, "name", None) == "user_context"
        )
        prompt_idx = next(
            i
            for i, m in enumerate(payload)
            if isinstance(m, SystemMessage)
            and getattr(m, "name", None) != "user_context"
            and "Orchestrator" in m.content
        )
        assert ctx_idx < prompt_idx, (
            "user_context deve vir ANTES do _ORCHESTRATOR_PROMPT"
        )


# ---------------------------------------------------------------------------
# Site 2 — _synthesize_after_coder
# ---------------------------------------------------------------------------


class TestSynthesizeAfterCoder:
    @pytest.mark.asyncio
    async def test_injects_user_context(self):
        state: Any = {
            "messages": [HumanMessage(content="cria main.py")],
            "session_metadata": {},
            "coder_result": CoderResult(
                summary="Arquivo criado", files_changed=["main.py"], success=True
            ),
        }
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Pronto."))

        with patch("src.agents.orchestrator._get_synthesis_llm", return_value=fake_llm):
            cmd = await _synthesize_after_coder(
                state,
                session_id=None,
                state_update_extra={},
                config=_cfg_with_user_ctx(),
            )

        assert cmd.goto == END
        payload = _captured_payload(fake_llm)
        ctx = _user_context_msg(payload)
        assert ctx is not None
        assert "Bruno Soares" in ctx.content
        assert "`pt_BR`" in ctx.content

    @pytest.mark.asyncio
    async def test_no_user_context_when_config_none(self):
        state: Any = {
            "messages": [HumanMessage(content="cria main.py")],
            "session_metadata": {},
            "coder_result": CoderResult(summary="ok", success=True),
        }
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Pronto."))

        with patch("src.agents.orchestrator._get_synthesis_llm", return_value=fake_llm):
            await _synthesize_after_coder(
                state, session_id=None, state_update_extra={}, config=None
            )

        payload = _captured_payload(fake_llm)
        assert _user_context_msg(payload) is None


# ---------------------------------------------------------------------------
# Site 3 — _synthesize_after_search
# ---------------------------------------------------------------------------


class TestSynthesizeAfterSearch:
    @pytest.mark.asyncio
    async def test_injects_user_context(self):
        state: Any = {
            "messages": [HumanMessage(content="pesquise X")],
            "session_metadata": {},
            "search_result": SearchResult(
                summary="Encontrei", sources=["https://x.com"], confidence=0.9
            ),
        }
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Resumo"))

        with patch("src.agents.orchestrator._get_synthesis_llm", return_value=fake_llm):
            cmd = await _synthesize_after_search(
                state,
                session_id=None,
                state_update_extra={},
                config=_cfg_with_user_ctx("Maria José", "es-419"),
            )

        assert cmd.goto == END
        payload = _captured_payload(fake_llm)
        ctx = _user_context_msg(payload)
        assert ctx is not None
        assert "Maria José" in ctx.content
        assert "`es-419`" in ctx.content

    @pytest.mark.asyncio
    async def test_no_user_context_when_config_none(self):
        state: Any = {
            "messages": [HumanMessage(content="pesquise X")],
            "session_metadata": {},
            "search_result": SearchResult(summary="ok"),
        }
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Resumo"))

        with patch("src.agents.orchestrator._get_synthesis_llm", return_value=fake_llm):
            await _synthesize_after_search(
                state, session_id=None, state_update_extra={}, config=None
            )

        payload = _captured_payload(fake_llm)
        assert _user_context_msg(payload) is None


# ---------------------------------------------------------------------------
# Site 4 — _synthesize_after_parallel
# ---------------------------------------------------------------------------


class TestSynthesizeAfterParallel:
    @pytest.mark.asyncio
    async def test_injects_user_context(self):
        state: Any = {
            "messages": [HumanMessage(content="compare X e Y")],
            "session_metadata": {},
            "parallel_results": [
                {
                    "agent": "search",
                    "task": "busca X",
                    "response": "ok",
                    "success": True,
                },
                {
                    "agent": "coder",
                    "task": "código Y",
                    "response": "ok",
                    "success": True,
                },
            ],
        }
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Integrei"))

        with patch("src.agents.orchestrator._get_synthesis_llm", return_value=fake_llm):
            cmd = await _synthesize_after_parallel(
                state,
                session_id=None,
                state_update_extra={},
                config=_cfg_with_user_ctx("Iñaki", "Portuguese_Brazil"),
            )

        assert cmd.goto == END
        payload = _captured_payload(fake_llm)
        ctx = _user_context_msg(payload)
        assert ctx is not None
        assert "Iñaki" in ctx.content
        # Locale cru — sem normalização (Portuguese_Brazil estilo Windows)
        assert "`Portuguese_Brazil`" in ctx.content

    @pytest.mark.asyncio
    async def test_no_user_context_when_config_none(self):
        state: Any = {
            "messages": [HumanMessage(content="compare X e Y")],
            "session_metadata": {},
            "parallel_results": [
                {"agent": "search", "task": "busca", "response": "ok", "success": True}
            ],
        }
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Integrei"))

        with patch("src.agents.orchestrator._get_synthesis_llm", return_value=fake_llm):
            await _synthesize_after_parallel(
                state, session_id=None, state_update_extra={}, config=None
            )

        payload = _captured_payload(fake_llm)
        assert _user_context_msg(payload) is None
