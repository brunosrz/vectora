"""``VectoraAnthropicChat`` — chat da Anthropic (Messages API) como ``BaseChatModel``.

Substitui ``ChatAnthropic`` (``langchain_anthropic``). SSE puro, com cada
content block identificado por `index` — texto (`text_delta`) e tool use
(`input_json_delta`, string JSON parcial que só é parseada no
`content_block_stop`, nunca antes: modelos atuais só emitem uma key/value
completa de cada vez, mas o parser não assume isso como garantia permanente).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Sequence
from typing import Any

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    ToolCall,
    ToolCallChunk,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import ConfigDict, Field

from backend.llm.anthropic.client import AnthropicClient, AnthropicResponseError

logger = logging.getLogger(__name__)


def _to_anthropic_tool(tool: Any) -> dict:
    """Converte pro formato `{name, description, input_schema}` da Anthropic
    — sem wrapper `type:"function"` nem `strict`, diferente da OpenAI."""
    convertida = convert_to_openai_tool(tool)
    funcao = convertida.get("function", convertida)
    return {
        "name": funcao.get("name", ""),
        "description": funcao.get("description", ""),
        "input_schema": funcao.get("parameters")
        or {"type": "object", "properties": {}},
    }


def _to_anthropic_messages(
    messages: list[BaseMessage],
) -> tuple[str | None, list[dict]]:
    """Separa mensagens `system` (campo top-level próprio da Anthropic, não
    um role em `messages`) do resto, e traduz tool calls/results pro formato
    de content blocks (`tool_use`/`tool_result`)."""
    partes_sistema: list[str] = []
    saida: list[dict] = []

    for msg in messages:
        if msg.type == "system":
            partes_sistema.append(str(msg.content))
            continue

        if msg.type == "tool":
            saida.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": getattr(msg, "tool_call_id", ""),
                            "content": str(msg.content),
                        }
                    ],
                }
            )
            continue

        if msg.type == "human":
            saida.append({"role": "user", "content": str(msg.content)})
            continue

        if msg.type == "ai":
            chamadas = getattr(msg, "tool_calls", None)
            if chamadas:
                blocos: list[dict] = []
                if msg.content:
                    blocos.append({"type": "text", "text": str(msg.content)})
                blocos.extend(
                    {
                        "type": "tool_use",
                        "id": c.get("id") or "",
                        "name": c.get("name", ""),
                        "input": c.get("args") or {},
                    }
                    for c in chamadas
                )
                saida.append({"role": "assistant", "content": blocos})
            else:
                saida.append({"role": "assistant", "content": str(msg.content)})
            continue

        msg_erro = (
            f"Mensagem de tipo {msg.type!r} não tem role equivalente na Anthropic"
        )
        raise ValueError(msg_erro)

    system = "\n\n".join(partes_sistema) if partes_sistema else None
    return system, saida


def _parse_content_blocks(blocos: list) -> tuple[str, list[ToolCall], list[dict]]:
    texto_partes: list[str] = []
    validas: list[ToolCall] = []
    invalidas: list[dict] = []
    for bloco in blocos or []:
        tipo = bloco.get("type")
        if tipo == "text":
            texto_partes.append(bloco.get("text", ""))
        elif tipo == "tool_use":
            entrada = bloco.get("input")
            if not isinstance(entrada, dict):
                invalidas.append(
                    {
                        "name": bloco.get("name", ""),
                        "args": entrada,
                        "id": bloco.get("id"),
                        "error": "input não é objeto JSON válido",
                        "type": "invalid_tool_call",
                    }
                )
                continue
            validas.append(
                ToolCall(
                    name=bloco.get("name", ""),
                    args=entrada,
                    id=bloco.get("id"),
                    type="tool_call",
                )
            )
    return "".join(texto_partes), validas, invalidas


def _usage_metadata(usage: dict | None) -> dict | None:
    if not usage:
        return None
    entrada = int(usage.get("input_tokens") or 0)
    saida = int(usage.get("output_tokens") or 0)
    return {
        "input_tokens": entrada,
        "output_tokens": saida,
        "total_tokens": entrada + saida,
    }


class VectoraAnthropicChat(BaseChatModel):
    """Chat model nativo da Anthropic (Messages API)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str
    client: AnthropicClient
    temperature: float | None = None
    max_tokens: int = 4096
    #: Preenchido por `bind_tools`, já no formato `input_schema` da Anthropic.
    tools: list[dict] = Field(default_factory=list)
    #: Prompt caching (`cache_control: ephemeral`) no bloco de system prompt
    #: — GA na Messages API, não precisa mais do header `anthropic-beta` da
    #: geração original. Substitui o `betas=["prompt-caching-2024-07-31"]`
    #: do `ChatAnthropic` antigo, que injetava esse marker automaticamente.
    cache_system_prompt: bool = True

    @property
    def _llm_type(self) -> str:
        return "vectora-anthropic"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> VectoraAnthropicChat:
        convertidas = [_to_anthropic_tool(t) for t in tools]
        return self.model_copy(update={"tools": convertidas, **kwargs})

    def _payload(self, messages: list[BaseMessage], **kwargs: Any) -> dict:
        system, mensagens = _to_anthropic_messages(messages)
        corpo: dict[str, Any] = {
            "model": self.model,
            "messages": mensagens,
            "max_tokens": self.max_tokens,
        }
        if system:
            corpo["system"] = (
                [
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
                if self.cache_system_prompt
                else system
            )
        if self.temperature is not None:
            corpo["temperature"] = self.temperature
        if self.tools:
            corpo["tools"] = self.tools
        if kwargs.get("tool_choice") is not None:
            corpo["tool_choice"] = kwargs["tool_choice"]
        return corpo

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        corpo = self._payload(messages, **kwargs)
        if stop:
            corpo["stop_sequences"] = stop
        resposta = await self.client.create_message(corpo)
        blocos = resposta.get("content")
        if not isinstance(blocos, list):
            msg = (
                "Anthropic respondeu sem `content` utilizável — resposta "
                f"inutilizável (id={resposta.get('id')!r})"
            )
            raise AnthropicResponseError(msg)

        texto, validas, invalidas = _parse_content_blocks(blocos)
        usage = resposta.get("usage") or {}
        ai = AIMessage(
            content=texto,
            tool_calls=validas,
            invalid_tool_calls=invalidas,
            usage_metadata=_usage_metadata(usage),  # type: ignore[arg-type]
            response_metadata={
                "model_name": resposta.get("model", self.model),
                "stop_reason": resposta.get("stop_reason"),
            },
        )
        return ChatResult(generations=[ChatGeneration(message=ai)])

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        corpo = self._payload(messages, **kwargs)
        if stop:
            corpo["stop_sequences"] = stop

        # Cada content block tem `index` explícito (0-based). Blocos de texto
        # concatenam direto; blocos `tool_use` acumulam `input_json_delta`
        # (string JSON parcial) num buffer por índice.
        nomes_por_indice: dict[int, str] = {}
        ids_por_indice: dict[int, str] = {}
        # `name` só pode ir no PRIMEIRO chunk de cada índice — o LangChain
        # concatena o campo `name` entre chunks acumulados (mesma lógica de
        # `args`), então repetir o nome em cada delta duplicaria a string.
        nome_ja_emitido: set[int] = set()

        async for evento in self.client.stream_message(corpo):
            tipo_evento = evento.get("type")

            if tipo_evento == "content_block_start":
                indice = evento.get("index")
                bloco = evento.get("content_block") or {}
                if indice is None:
                    continue
                if bloco.get("type") == "tool_use":
                    nomes_por_indice[indice] = bloco.get("name", "")
                    ids_por_indice[indice] = bloco.get("id", "")

            elif tipo_evento == "content_block_delta":
                indice = evento.get("index")
                delta = evento.get("delta") or {}
                delta_tipo = delta.get("type")
                if indice is None:
                    continue

                if delta_tipo == "text_delta":
                    texto = delta.get("text", "")
                    if texto:
                        chunk = AIMessageChunk(content=texto)
                        pedaco = ChatGenerationChunk(message=chunk)
                        if run_manager:
                            await run_manager.on_llm_new_token(texto, chunk=pedaco)
                        yield pedaco

                elif delta_tipo == "input_json_delta":
                    nome = (
                        nomes_por_indice.get(indice)
                        if indice not in nome_ja_emitido
                        else None
                    )
                    nome_ja_emitido.add(indice)
                    chunk = AIMessageChunk(
                        content="",
                        tool_call_chunks=[
                            ToolCallChunk(
                                name=nome,
                                args=delta.get("partial_json", ""),
                                id=ids_por_indice.get(indice),
                                index=indice,
                            )
                        ],
                    )
                    pedaco = ChatGenerationChunk(message=chunk)
                    if run_manager:
                        await run_manager.on_llm_new_token("", chunk=pedaco)
                    yield pedaco

            elif tipo_evento == "message_delta":
                usage = evento.get("usage")
                if usage:
                    chunk = AIMessageChunk(
                        content="",
                        usage_metadata=_usage_metadata(usage),  # type: ignore[arg-type]
                    )
                    pedaco = ChatGenerationChunk(message=chunk)
                    if run_manager:
                        await run_manager.on_llm_new_token("", chunk=pedaco)
                    yield pedaco

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        msg = "VectoraAnthropicChat é async-only (CLAUDE.md regra 10) — use ainvoke/astream."
        raise NotImplementedError(msg)
