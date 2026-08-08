"""``ChatClient`` — Protocol nativo que os 5 clients de chat de provider
implementam (Sprint 14, Workstream 3). Substitui
``langchain_core.language_models.chat_models.BaseChatModel``.

Diferença central em relação ao ``BaseChatModel``: não existe mais
``bind_tools()`` produzindo uma instância nova imutável com as tools
"presas" — cada chamada de ``astream``/``agenerate`` recebe ``tools=``
diretamente como parâmetro. Isso elimina o hack de
``RunnableBinding``/``_unwrap_binding`` que ``FallbackChatModel`` precisava
antes só pra contornar essa abstração do LangChain.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from backend.tools.registry import ToolSpec
    from backend.vtypes.message import VMessage, VMessageChunk


class ChatClient(Protocol):
    """Interface comum aos 5 clients de chat nativos (openai/anthropic/
    google/openrouter/ollama) e ao ``FallbackChatClient`` que orquestra
    fallback entre eles."""

    async def astream(
        self,
        messages: list[VMessage],
        *,
        tools: list[ToolSpec] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[VMessageChunk]:
        """Streaming — cada implementação faz `yield` de fragmentos
        `VMessageChunk` conforme o provider entrega (delta de texto, tool
        call fragmentada ou completa, usage)."""
        ...

    async def agenerate(
        self,
        messages: list[VMessage],
        *,
        tools: list[ToolSpec] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> VMessage:
        """Não-streaming — devolve a mensagem completa do turno."""
        ...
