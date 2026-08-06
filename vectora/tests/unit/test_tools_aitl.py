"""Testes de `backend/tools/aitl.py` — AITL (subagente pede decisão ao pai).

Cobre happy path (aprovado/negado) + erro/borda (falha na chamada de
decisão nunca propaga, sempre volta negado) no mesmo arquivo, CLAUDE.md §18.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage

from backend.tools.aitl import ask_parent_agent


class TestAskParentAgent:
    @pytest.mark.asyncio
    async def test_aprovado_quando_decisao_comeca_com_approved(self):
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="APPROVED\nSeems safe, go ahead.")
        )
        with patch(
            "backend.llm.fallback_chat_model.FallbackChatModel",
            return_value=fake_llm,
        ):
            result = json.loads(
                await ask_parent_agent.ainvoke(
                    {"reason": "preciso rodar um comando de rede pra diagnosticar"}
                )
            )

        assert result["status"] == "ok"
        assert result["approved"] is True
        assert "Seems safe" in result["reason"]

    @pytest.mark.asyncio
    async def test_negado_quando_decisao_comeca_com_denied(self):
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="DENIED\nToo vague, ask the user instead.")
        )
        with patch(
            "backend.llm.fallback_chat_model.FallbackChatModel",
            return_value=fake_llm,
        ):
            result = json.loads(
                await ask_parent_agent.ainvoke(
                    {
                        "reason": "preciso de mais acesso",
                        "requested_tool": "terminal",
                    }
                )
            )

        assert result["status"] == "ok"
        assert result["approved"] is False
        assert "Too vague" in result["reason"]

    @pytest.mark.asyncio
    async def test_erro_na_chamada_de_decisao_nunca_propaga_e_nega(self):
        """Erro/borda: LLM de julgamento falhando (rede, quota, o que for)
        vira negado com motivo — nunca uma exceção não tratada que travaria
        o subagent esperando indefinidamente."""
        with patch(
            "backend.llm.fallback_chat_model.FallbackChatModel",
            side_effect=RuntimeError("quota esgotada"),
        ):
            result = json.loads(
                await ask_parent_agent.ainvoke({"reason": "qualquer coisa"})
            )

        assert result["status"] == "ok"
        assert result["approved"] is False
        assert "erro interno" in result["reason"]
        assert "quota esgotada" in result["reason"]

    @pytest.mark.asyncio
    async def test_sem_requested_tool_ainda_funciona(self):
        """Erro/borda: requested_tool é opcional — omitir não quebra o prompt
        montado nem a chamada."""
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(return_value=AIMessage(content="APPROVED\nok"))
        with patch(
            "backend.llm.fallback_chat_model.FallbackChatModel",
            return_value=fake_llm,
        ):
            result = json.loads(
                await ask_parent_agent.ainvoke({"reason": "só confirmando"})
            )

        assert result["approved"] is True
        sent_messages = fake_llm.ainvoke.call_args.args[0]
        assert "Requested tool" not in sent_messages[1].content
