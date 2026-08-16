"""Testes para backend/services/connect/runner.py.

`run_agent_for_thread` é o ponto de entrada único que os 4 adapters
(Telegram/Discord/Slack/Email) usam pra rodar uma mensagem externa através
do motor nativo (`backend/engine/conversation_loop.py`) — mesmo caminho que
o chat web usa, sob o usuário "local" e `permission_mode="auto"` (mensageria
externa não tem UI de aprovar/rejeitar tool call).
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.engine.hitl import ApprovalGate
from backend.persistence.native.session_store import SessionStore
from backend.services import agent_factory
from backend.services.agent_factory import NativeAgent
from backend.services.connect import runner
from backend.storage.sqlite.pool import AsyncConnectionPool
from backend.tools.context import ToolContext
from backend.tools.registry import ToolRegistry
from backend.vtypes.message import ToolCallChunk, VMessageChunk


@pytest.fixture
async def native_session_store(tmp_path):
    pool = AsyncConnectionPool(
        str(tmp_path / "connect-runner-sessions.db"), min_size=1, max_size=2
    )
    await pool.open()
    store = SessionStore(pool)
    await store.setup()
    try:
        yield store
    finally:
        await pool.close()


def _require_spec(name: str) -> Any:
    """`TOOL_REGISTRY.get(name)` sem o `| None` — chamado só depois de
    garantir que a tool foi registrada (`@vtool`) neste próprio teste."""
    from backend.tools.registry import TOOL_REGISTRY

    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        msg = f"tool '{name}' não registrada — setup do teste está errado"
        raise AssertionError(msg)
    return spec


def _texto_chunk(texto: str) -> VMessageChunk:
    return VMessageChunk(delta_text=texto)


def _tool_call_chunk(*, index: int, id: str, name: str, args: str) -> VMessageChunk:  # noqa: A002
    return VMessageChunk(
        tool_call_chunks=[
            ToolCallChunk(index=index, id=id, name=name, args_fragment=args)
        ]
    )


class _ScriptedChatClient:
    """Cliente de chat fake — cada `astream` consome o próximo turno
    pré-roteirizado. Com `exc`, toda chamada levanta a exceção dada."""

    def __init__(
        self,
        turnos: list[list[VMessageChunk]] | None = None,
        *,
        exc: Exception | None = None,
    ) -> None:
        self._turnos = turnos or []
        self.chamadas = 0
        self._exc = exc

    async def astream(self, messages, *, tools=None, temperature=None, max_tokens=None):
        self.chamadas += 1
        if self._exc is not None:
            raise self._exc
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
    tool_registry: ToolRegistry | None = None,
    subagent_catalog: dict[str, Any] | None = None,
    chat_client: Any = None,
) -> None:
    native_agent = NativeAgent(
        tool_registry=tool_registry or ToolRegistry(),
        subagent_catalog=subagent_catalog or {},
        system_prompt="system prompt de teste",
    )

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
    monkeypatch.setattr(
        runner,
        "FallbackChatClient",
        lambda primary_model_id="": (
            chat_client or _ScriptedChatClient([[_texto_chunk("ok")]])
        ),
    )


class TestRunAgentForThread:
    async def test_roda_o_turno_e_devolve_o_texto_final(
        self, native_session_store, monkeypatch
    ):
        client = _ScriptedChatClient([[_texto_chunk("Olá! Como posso ajudar?")]])
        _patch_native_engine(
            monkeypatch, session_store=native_session_store, chat_client=client
        )

        reply = await runner.run_agent_for_thread("connect-telegram-abc", "oi")

        assert reply == "Olá! Como posso ajudar?"
        assert client.chamadas == 1

        # A mensagem do usuário e a resposta do agente ficaram persistidas
        # em SessionStore, sob o mesmo thread_id do mapeamento da plataforma.
        historico = await native_session_store.get_history("connect-telegram-abc")
        assert [m.role.value for m in historico] == ["system", "user", "assistant"]
        assert historico[1].text() == "oi"
        assert historico[-1].text() == "Olá! Como posso ajudar?"

        # Erro/borda: resposta maior que MAX_REPLY_CHARS é truncada (Telegram/
        # Discord rejeitam mensagem inteira acima do limite da plataforma).
        texto_longo = "x" * (runner.MAX_REPLY_CHARS + 500)
        client2 = _ScriptedChatClient([[_texto_chunk(texto_longo)]])
        _patch_native_engine(
            monkeypatch, session_store=native_session_store, chat_client=client2
        )
        reply2 = await runner.run_agent_for_thread("connect-telegram-def", "oi de novo")
        assert len(reply2) == runner.MAX_REPLY_CHARS + 1  # +1 do "…" de corte
        assert reply2.endswith("…")

    async def test_segunda_mensagem_na_mesma_thread_reusa_o_historico(
        self, native_session_store, monkeypatch
    ):
        """Cada chamada relê o histórico persistido — a 2ª mensagem do mesmo
        `thread_id` não recria o system prompt nem perde o turno anterior."""
        _patch_native_engine(
            monkeypatch,
            session_store=native_session_store,
            chat_client=_ScriptedChatClient([[_texto_chunk("primeira resposta")]]),
        )
        await runner.run_agent_for_thread("connect-discord-xyz", "primeira mensagem")

        _patch_native_engine(
            monkeypatch,
            session_store=native_session_store,
            chat_client=_ScriptedChatClient([[_texto_chunk("segunda resposta")]]),
        )
        await runner.run_agent_for_thread("connect-discord-xyz", "segunda mensagem")

        historico = await native_session_store.get_history("connect-discord-xyz")
        # Só 1 system prompt (não duplicado) + 2 turnos completos.
        assert [m.role.value for m in historico] == [
            "system",
            "user",
            "assistant",
            "user",
            "assistant",
        ]

    async def test_tool_destrutiva_nunca_pausa_em_hitl_mensageria_externa(
        self, native_session_store, monkeypatch
    ):
        """`permission_mode` fixo em "auto" — o interlocutor externo não tem
        UI de aprovar/rejeitar, então uma tool destrutiva roda direto em vez
        de deixar o turno preso esperando aprovação que nunca chega."""
        from backend.tools.registry import TOOL_REGISTRY, ToolExtras, vtool

        if TOOL_REGISTRY.get("escrever_arquivo_connect") is None:

            @vtool(extras=ToolExtras(destructive=True))
            async def escrever_arquivo_connect(ctx: ToolContext) -> str:
                """escreve um arquivo (fake)."""
                return "escrito"

        registry = ToolRegistry()
        registry.register(_require_spec("escrever_arquivo_connect"))

        client = _ScriptedChatClient(
            [
                [
                    _tool_call_chunk(
                        index=0,
                        id="call_1",
                        name="escrever_arquivo_connect",
                        args="{}",
                    )
                ],
                [_texto_chunk("arquivo escrito com sucesso")],
            ]
        )
        _patch_native_engine(
            monkeypatch,
            session_store=native_session_store,
            tool_registry=registry,
            chat_client=client,
        )

        reply = await runner.run_agent_for_thread(
            "connect-slack-c1", "escreva um arquivo"
        )

        assert reply == "arquivo escrito com sucesso"
        assert client.chamadas == 2  # nunca pausou — o loop seguiu direto
        historico = await native_session_store.get_history("connect-slack-c1")
        assert [m.role.value for m in historico[-3:]] == [
            "assistant",
            "tool",
            "assistant",
        ]

    async def test_falha_no_chat_client_propaga_pro_handle_incoming_message(
        self, native_session_store, monkeypatch
    ):
        """Erro/borda: run_agent_for_thread NÃO trata a exceção — é
        `handle_incoming_message` (backend/services/gateway/messaging.py)
        quem converte falha em resposta amigável, então o interlocutor
        externo nunca fica sem resposta nenhuma."""
        _patch_native_engine(
            monkeypatch,
            session_store=native_session_store,
            chat_client=_ScriptedChatClient(exc=RuntimeError("provider fora do ar")),
        )

        with pytest.raises(RuntimeError, match="provider fora do ar"):
            await runner.run_agent_for_thread("connect-email-1", "mensagem qualquer")


class TestProcessIncoming:
    async def test_fluxo_completo_resolve_thread_roda_agente_e_devolve_resposta(
        self, native_session_store, monkeypatch, tmp_path
    ):
        """Fluxo ponta a ponta de uma mensagem de plataforma externa: resolve
        (cria) o mapeamento thread, roda o agente via `run_agent_for_thread`
        e devolve a resposta pronta pra plataforma reenviar."""
        from backend.services.gateway.messaging import IncomingMessage
        from backend.settings import settings

        monkeypatch.setattr(settings, "db_dsn", str(tmp_path / "connect-process.db"))

        _patch_native_engine(
            monkeypatch,
            session_store=native_session_store,
            chat_client=_ScriptedChatClient([[_texto_chunk("resposta do agente")]]),
        )

        incoming = IncomingMessage(
            platform="telegram", platform_user_id="999", text="oi vectora"
        )
        outgoing = await runner.process_incoming(incoming)

        assert outgoing.platform == "telegram"
        assert outgoing.platform_user_id == "999"
        assert outgoing.text == "resposta do agente"

        # Erro/borda: falha ao rodar o agente (ex.: provider fora do ar)
        # nunca deixa o interlocutor sem resposta — process_incoming devolve
        # uma mensagem amigável em vez de propagar a exceção.
        _patch_native_engine(
            monkeypatch,
            session_store=native_session_store,
            chat_client=_ScriptedChatClient(exc=RuntimeError("boom")),
        )
        incoming2 = IncomingMessage(
            platform="telegram", platform_user_id="999", text="de novo"
        )
        outgoing2 = await runner.process_incoming(incoming2)
        assert "não consegui processar" in outgoing2.text.lower()
        # Reusa a MESMA thread da primeira mensagem (mesmo platform_user_id).
        assert outgoing2.platform_user_id == "999"
