"""``FakeChatClient`` — implementação nativa do Protocol `ChatClient`
(`backend/llm/base.py`) pra testes, sem depender de nenhum provider real.
Substitui o `FakeChatModel` do LangChain (já removido — sem consumidor
desde a Sprint 15) e generaliza o padrão `_ScriptedChatClient` que
`test_engine_conversation_loop.py`/`test_engine_subagents.py` reimplementam
localmente hoje.

Roteirizável por sequência de turnos: cada chamada a `astream`/`agenerate`
consome o próximo turno do script, na ordem — um turno é a lista de
`VMessageChunk` que aquela volta do loop deve produzir (pra `astream`) ou
diretamente uma `VMessage` completa (pra `agenerate`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from backend.vtypes.message import ContentBlock, MessageRole, VMessage

if TYPE_CHECKING:
    from backend.tools.registry import ToolSpec
    from backend.vtypes.message import VMessageChunk


class FakeChatClient:
    """Scriptável por `turns` (streaming) e/ou `responses` (não-streaming).
    Registra cada chamada em `.calls` (mensagens + tools recebidas) pra
    asserção posterior sobre o que o motor de fato enviou ao "provider"."""

    def __init__(
        self,
        turns: list[list[VMessageChunk]] | None = None,
        responses: list[VMessage] | None = None,
    ) -> None:
        self._turns = turns or []
        self._responses = responses or []
        self.stream_calls = 0
        self.generate_calls = 0
        self.calls: list[dict[str, object]] = []

    async def astream(
        self,
        messages: list[VMessage],
        *,
        tools: list[ToolSpec] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[VMessageChunk]:
        self.calls.append(
            {"kind": "astream", "messages": list(messages), "tools": tools}
        )
        if self.stream_calls >= len(self._turns):
            msg = (
                f"FakeChatClient.astream chamado {self.stream_calls + 1}x, mas só "
                f"{len(self._turns)} turno(s) foram roteirizados — script "
                "insuficiente pro teste."
            )
            raise AssertionError(msg)
        turno = self._turns[self.stream_calls]
        self.stream_calls += 1
        for chunk in turno:
            yield chunk

    async def agenerate(
        self,
        messages: list[VMessage],
        *,
        tools: list[ToolSpec] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> VMessage:
        self.calls.append(
            {"kind": "agenerate", "messages": list(messages), "tools": tools}
        )
        if self.generate_calls >= len(self._responses):
            msg = (
                f"FakeChatClient.agenerate chamado {self.generate_calls + 1}x, mas "
                f"só {len(self._responses)} resposta(s) foram roteirizadas — "
                "script insuficiente pro teste."
            )
            raise AssertionError(msg)
        resposta = self._responses[self.generate_calls]
        self.generate_calls += 1
        return resposta


def text_chunk(text: str) -> VMessageChunk:
    """Atalho pra roteirizar um turno de texto puro (sem tool call)."""
    from backend.vtypes.message import VMessageChunk as _VMessageChunk

    return _VMessageChunk(delta_text=text)


def text_response(text: str, *, name: str | None = None) -> VMessage:
    """Atalho pra roteirizar uma resposta completa de `agenerate`."""
    return VMessage(
        role=MessageRole.ASSISTANT,
        content=[ContentBlock(kind="text", text=text)],
        finish_reason="stop",
        name=name,
    )
