"""Execução do agente para mensagens vindas de plataformas externas.

Um único ponto de entrada para os 4 adapters: eles só traduzem formato, quem
resolve thread e roda o agente é aqui — assim uma mensagem do Telegram passa
exatamente pelo mesmo caminho de uma do chat web.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.services.connect.store import create_thread_mapping, lookup_thread
from backend.services.gateway.messaging import (
    IncomingMessage,
    OutgoingMessage,
    handle_incoming_message,
)

logger = logging.getLogger(__name__)

#: Teto de caracteres da resposta devolvida à plataforma. Telegram corta em
#: 4096 e Discord em 2000; truncar aqui evita que a plataforma rejeite a
#: mensagem inteira e o interlocutor fique sem resposta nenhuma.
MAX_REPLY_CHARS = 1900


def _extract_text(result: Any) -> str:
    """Último `AIMessage` do resultado do grafo. Um grafo que terminou só com
    tool calls (sem texto final) devolve string vazia, não estoura."""
    messages = (result or {}).get("messages") or []
    for message in reversed(messages):
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            joined = "".join(parts).strip()
            if joined:
                return joined
    return ""


async def run_agent_for_thread(thread_id: str, text: str) -> str:
    """Roda o agente do usuário local no `thread_id` dado e devolve o texto."""
    from langchain_core.messages import HumanMessage

    from backend.services import agent_factory
    from backend.vtypes.context import ctx_from_config

    agent = await agent_factory.get_user_agent(user_id="local", workspace_id=None)
    config = {
        "configurable": {"thread_id": thread_id, "user_id": "local"},
        "recursion_limit": 50,
    }
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=text)]},
        config=config,
        context=ctx_from_config(config),
    )
    reply = _extract_text(result)
    if len(reply) > MAX_REPLY_CHARS:
        reply = reply[:MAX_REPLY_CHARS] + "…"
    return reply


async def process_incoming(incoming: IncomingMessage) -> OutgoingMessage:
    """Resolve o thread e roda o agente. Nunca levanta: `handle_incoming_message`
    já converte falha em texto de erro amigável, senão o interlocutor externo
    ficaria sem resposta nenhuma."""
    return await handle_incoming_message(
        incoming,
        lookup=lookup_thread,
        create=create_thread_mapping,
        run_agent=run_agent_for_thread,
    )
