"""Regressão ao vivo: `resume_chat` (retomada de HITL) chamava
`get_user_agent(resume_user_id)` sem `model`/`chat_mode`/`workspace_id` —
caía no grafo "__default__" em vez do grafo compilado com o
`FallbackChatModel.primary_model_id` que o usuário de fato selecionou
(ex.: `nine_router:gemini-...`). Sintoma real: aprovar uma tool destrutiva
resumia a conversa com o provider padrão do sistema (Google), que falhava
com `GoogleGenAIResponseError: API key not valid` mesmo o usuário tendo
selecionado um modelo roteado via 9Router.

`stream_chat` agora grava o seletor de grafo (`model`, `chat_mode`,
`workspace_id`) por `thread_id` em `_thread_graph_selector`; `resume_chat`
lê esse seletor para chamar `get_user_agent` com os mesmos parâmetros.
"""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.schemas import ChatConfig, ResumeChatRequest, StreamChatRequest


async def _empty_events(*_a: object, **_kw: object):
    return
    yield  # async generator


def _mock_graph() -> MagicMock:
    graph = MagicMock()
    graph.astream_events = MagicMock(return_value=_empty_events())
    return graph


def _mock_registry(ws_id: str) -> MagicMock:
    ws = MagicMock()
    ws.id = ws_id
    registry = MagicMock()
    registry.get.return_value = None
    registry.get_active.return_value = None
    registry.get_or_create_session_workspace.return_value = ws
    return registry


class TestResumeChatUsesSameGraphAsStreamChat:
    @pytest.mark.asyncio
    async def test_resume_chat_repassa_model_chat_mode_e_workspace_do_turno_original(
        self,
    ) -> None:
        get_user_agent_calls: list[dict[str, object]] = []

        async def _fake_get_user_agent(user_id, **kwargs):
            get_user_agent_calls.append({"user_id": user_id, **kwargs})
            return _mock_graph()

        with (
            patch(
                "backend.services.agent_factory.get_user_agent",
                new=AsyncMock(side_effect=_fake_get_user_agent),
            ),
            patch(
                "backend.api.handlers.threads._upsert_session",
                new=AsyncMock(),
            ),
            patch(
                "backend.workspace.workspace.workspace_registry",
                _mock_registry("ws-resume-test"),
            ),
        ):
            import backend.api.handlers.chat as chat_mod

            importlib.reload(chat_mod)

            http_request = MagicMock()
            http_request.state = MagicMock(user=None)

            stream_request = StreamChatRequest(
                content="oi",
                thread_id="thread-resume-1",
                config=ChatConfig(model="nine_router:gemini-2.5-flash"),
            )
            await chat_mod.stream_chat(stream_request, http_request)

            resume_request = ResumeChatRequest(
                thread_id="thread-resume-1",
                interrupt_id="irrelevant",
                decision="approve",
            )
            await chat_mod.resume_chat(resume_request, http_request)

        assert len(get_user_agent_calls) == 2
        stream_call, resume_call = get_user_agent_calls

        assert stream_call["model"] == "nine_router:gemini-2.5-flash"
        assert resume_call["model"] == "nine_router:gemini-2.5-flash", (
            "resume_chat deve resolver o MESMO grafo (mesmo model_id embutido "
            "no FallbackChatModel) que stream_chat usou nesse turno — nunca "
            "cair no grafo '__default__'"
        )
        assert resume_call["chat_mode"] == stream_call["chat_mode"]
        assert resume_call["workspace_id"] == stream_call["workspace_id"]

    @pytest.mark.asyncio
    async def test_resume_chat_sem_turno_anterior_conhecido_usa_default_sem_lancar(
        self,
    ) -> None:
        """Erro/borda: thread nunca vista por stream_chat (processo reiniciado
        entre o pedido de aprovação e a resposta, ou request malformada) não
        deve lançar — degrada pro grafo default em vez de quebrar o resume."""
        get_user_agent_calls: list[dict[str, object]] = []

        async def _fake_get_user_agent(user_id, **kwargs):
            get_user_agent_calls.append({"user_id": user_id, **kwargs})
            return _mock_graph()

        with patch(
            "backend.services.agent_factory.get_user_agent",
            new=AsyncMock(side_effect=_fake_get_user_agent),
        ):
            import backend.api.handlers.chat as chat_mod

            importlib.reload(chat_mod)

            http_request = MagicMock()
            http_request.state = MagicMock(user=None)

            resume_request = ResumeChatRequest(
                thread_id="thread-nunca-vista",
                interrupt_id="irrelevant",
                decision="approve",
            )
            await chat_mod.resume_chat(resume_request, http_request)

        assert len(get_user_agent_calls) == 1
        assert get_user_agent_calls[0]["model"] == ""
        assert get_user_agent_calls[0]["chat_mode"] is False
        assert get_user_agent_calls[0]["workspace_id"] is None
