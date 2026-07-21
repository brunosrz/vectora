"""Vectora Connect — camada de abstração de mensageria (Sprint 8).

resolve_thread_id: reusa thread existente por platform_user_id, cria na
primeira mensagem. handle_incoming_message: fecha o loop e nunca deixa o
usuário externo sem resposta, mesmo com falha do agente.
"""

from __future__ import annotations

import pytest

from backend.services.gateway.messaging import (
    IncomingMessage,
    handle_incoming_message,
    resolve_thread_id,
)


def _incoming(
    platform="telegram", platform_user_id="123", text="oi"
) -> IncomingMessage:
    return IncomingMessage(
        platform=platform, platform_user_id=platform_user_id, text=text
    )


@pytest.mark.asyncio
async def test_resolve_thread_id_reuses_existing_mapping():
    async def lookup(platform, uid):
        assert (platform, uid) == ("telegram", "123")
        return "thread-existing"

    async def create(platform, uid):
        raise AssertionError("não deveria criar — já existe mapeamento")

    thread_id = await resolve_thread_id(_incoming(), lookup=lookup, create=create)

    assert thread_id == "thread-existing"


@pytest.mark.asyncio
async def test_resolve_thread_id_creates_new_thread_on_first_message():
    async def lookup(platform, uid):
        return None

    async def create(platform, uid):
        return "thread-new"

    thread_id = await resolve_thread_id(_incoming(), lookup=lookup, create=create)

    assert thread_id == "thread-new"


@pytest.mark.asyncio
async def test_handle_incoming_message_returns_agent_reply():
    async def lookup(platform, uid):
        return "thread-1"

    async def create(platform, uid):
        raise AssertionError("não deveria criar")

    async def run_agent(thread_id, text):
        assert thread_id == "thread-1"
        assert text == "oi"
        return "resposta do agente"

    result = await handle_incoming_message(
        _incoming(), lookup=lookup, create=create, run_agent=run_agent
    )

    assert result.platform == "telegram"
    assert result.platform_user_id == "123"
    assert result.text == "resposta do agente"


@pytest.mark.asyncio
async def test_handle_incoming_message_agent_failure_returns_friendly_error_not_exception():
    # Erro/borda: agente indisponível não pode deixar o usuário externo sem
    # resposta nenhuma (tools defensivas, CLAUDE.md regra 11).
    async def lookup(platform, uid):
        return "thread-1"

    async def create(platform, uid):
        return "thread-1"

    async def run_agent(thread_id, text):
        raise RuntimeError("LLM indisponível")

    result = await handle_incoming_message(
        _incoming(), lookup=lookup, create=create, run_agent=run_agent
    )

    assert result.text
    assert "não consegui" in result.text.lower()
