"""``VectoraOpenRouterChat`` — chat do OpenRouter como ``BaseChatModel``.

Substitui ``ChatOpenAI(base_url=...)``. A API é OpenAI-compatível, então
aquele caminho funcionava — mas o cliente da OpenAI descarta o que é próprio
do OpenRouter: ``usage.cost``, o bloco ``provider`` de roteamento e o campo
``reasoning`` do delta.

Invariante de streaming: ``reasoning`` nunca entra em ``content``. Concatenar
os dois faz o raciocínio aparecer misturado à resposta na tela.
"""

from __future__ import annotations

import json
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

from backend.llm.openrouter.client import OpenRouterClient, OpenRouterResponseError

logger = logging.getLogger(__name__)

_ROLE_POR_TIPO = {
    "system": "system",
    "human": "user",
    "ai": "assistant",
    "tool": "tool",
    "function": "tool",
}


def _to_openrouter_message(msg: BaseMessage) -> dict:
    """Traduz uma mensagem LangChain pro formato do OpenRouter.

    Role desconhecido levanta em vez de virar `user`: mapear em silêncio faz
    o modelo receber contexto errado sem ninguém perceber.
    """
    role = _ROLE_POR_TIPO.get(msg.type)
    if role is None:
        msg_erro = (
            f"Mensagem de tipo {msg.type!r} não tem role equivalente no OpenRouter"
        )
        raise ValueError(msg_erro)

    saida: dict[str, Any] = {"role": role, "content": msg.content}

    if role == "tool":
        # Obrigatório no formato OpenAI-compatível — sem ele o provider
        # recusa a mensagem de tool com 400.
        saida["tool_call_id"] = getattr(msg, "tool_call_id", "")

    chamadas = getattr(msg, "tool_calls", None)
    if role == "assistant" and chamadas:
        saida["tool_calls"] = [
            {
                "id": c.get("id") or "",
                "type": "function",
                "function": {
                    "name": c.get("name", ""),
                    "arguments": json.dumps(c.get("args") or {}, ensure_ascii=False),
                },
            }
            for c in chamadas
        ]
        saida["content"] = msg.content or None

    return saida


def _parse_tool_calls(bruto: list) -> tuple[list[ToolCall], list[dict]]:
    """Separa tool calls válidas das que vieram com `arguments` quebrado.

    Modelo devolvendo JSON inválido é comum; a chamada entra como inválida e
    o grafo segue, em vez de perder o texto já gerado no turno.
    """
    validas: list[ToolCall] = []
    invalidas: list[dict] = []
    for item in bruto or []:
        funcao = item.get("function") or {}
        nome = funcao.get("name", "")
        args_texto = funcao.get("arguments") or "{}"
        try:
            args = json.loads(args_texto)
        except (json.JSONDecodeError, TypeError):
            invalidas.append(
                {
                    "name": nome,
                    "args": args_texto,
                    "id": item.get("id"),
                    "error": "arguments não é JSON válido",
                    "type": "invalid_tool_call",
                }
            )
            continue
        validas.append(
            ToolCall(name=nome, args=args, id=item.get("id"), type="tool_call")
        )
    return validas, invalidas


def _parse_tool_call_chunks(bruto: list) -> list[ToolCallChunk]:
    """Converte deltas incrementais de `tool_calls` do streaming em
    `ToolCallChunk` — o `AIMessageChunk.__add__` do LangChain acumula esses
    fragmentos por `index` e resolve `arguments` (string parcial) pra JSON
    completo quando todos os pedaços chegaram.
    """
    pedacos: list[ToolCallChunk] = []
    for item in bruto or []:
        funcao = item.get("function") or {}
        pedacos.append(
            ToolCallChunk(
                name=funcao.get("name"),
                args=funcao.get("arguments"),
                id=item.get("id"),
                index=item.get("index"),
            )
        )
    return pedacos


def _usage_metadata(usage: dict | None) -> dict | None:
    if not usage:
        return None
    entrada = int(usage.get("prompt_tokens") or 0)
    saida = int(usage.get("completion_tokens") or 0)
    return {
        "input_tokens": entrada,
        "output_tokens": saida,
        "total_tokens": int(usage.get("total_tokens") or entrada + saida),
    }


class VectoraOpenRouterChat(BaseChatModel):
    """Chat model nativo do OpenRouter."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str
    client: OpenRouterClient
    temperature: float | None = None
    max_tokens: int | None = None
    #: Bloco `provider` do OpenRouter (ordem, fallbacks, exigência de tools).
    #: Ausente do payload quando None — mandar `null` restringe o roteamento
    #: em vez de deixar o OpenRouter escolher.
    provider: dict | None = None
    #: Preenchido por `bind_tools`, no formato OpenAI de function calling.
    tools: list[dict] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "vectora-openrouter"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> VectoraOpenRouterChat:
        convertidas = [convert_to_openai_tool(t) for t in tools]
        return self.model_copy(update={"tools": convertidas, **kwargs})

    def _payload(self, messages: list[BaseMessage], **kwargs: Any) -> dict:
        corpo: dict[str, Any] = {
            "model": self.model,
            "messages": [_to_openrouter_message(m) for m in messages],
        }
        if self.temperature is not None:
            corpo["temperature"] = self.temperature
        if self.max_tokens is not None:
            corpo["max_tokens"] = self.max_tokens
        if self.tools:
            corpo["tools"] = self.tools
        if self.provider:
            corpo["provider"] = self.provider
        for chave in ("tool_choice", "response_format", "reasoning"):
            if kwargs.get(chave) is not None:
                corpo[chave] = kwargs[chave]
        return corpo

    @staticmethod
    def _primeira_escolha(corpo: dict) -> dict:
        escolhas = corpo.get("choices")
        if not isinstance(escolhas, list) or not escolhas:
            msg = (
                "OpenRouter respondeu sem `choices` — resposta inutilizável "
                f"(id={corpo.get('id')!r})"
            )
            raise OpenRouterResponseError(msg)
        return escolhas[0]

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        corpo = self._payload(messages, **kwargs)
        if stop:
            corpo["stop"] = stop
        resposta = await self.client.post_json("/chat/completions", corpo)
        escolha = self._primeira_escolha(resposta)
        mensagem = escolha.get("message") or {}

        validas, invalidas = _parse_tool_calls(mensagem.get("tool_calls") or [])
        usage = resposta.get("usage") or {}
        metadata: dict[str, Any] = {
            "model_name": resposta.get("model", self.model),
            "finish_reason": escolha.get("finish_reason"),
        }
        if "cost" in usage:
            # O OpenRouter devolve o custo real da geração; o cliente da
            # OpenAI descartava esse campo por não existir na API dele.
            metadata["cost"] = usage["cost"]
        if mensagem.get("reasoning"):
            metadata["reasoning"] = mensagem["reasoning"]

        ai = AIMessage(
            content=mensagem.get("content") or "",
            tool_calls=validas,
            invalid_tool_calls=invalidas,
            usage_metadata=_usage_metadata(usage),  # type: ignore[arg-type]
            response_metadata=metadata,
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
            corpo["stop"] = stop

        async for evento in self.client.stream_sse("/chat/completions", corpo):
            # O OpenRouter manda `usage` no último evento SSE do stream —
            # às vezes junto de `choices` vazio, às vezes acompanhando o
            # chunk final com finish_reason. Captura nos dois casos.
            usage = evento.get("usage")
            if usage:
                metadata: dict[str, Any] = {}
                if "cost" in usage:
                    metadata["cost"] = usage["cost"]
                chunk = AIMessageChunk(
                    content="",
                    usage_metadata=_usage_metadata(usage),  # type: ignore[arg-type]
                    response_metadata=metadata,
                )
                pedaco = ChatGenerationChunk(message=chunk)
                if run_manager:
                    await run_manager.on_llm_new_token("", chunk=pedaco)
                yield pedaco

            escolhas = evento.get("choices") or []
            if not escolhas:
                continue
            delta = escolhas[0].get("delta") or {}

            raciocinio = delta.get("reasoning")
            if raciocinio:
                # Canal próprio: concatenar em `content` mistura raciocínio
                # com resposta na tela.
                chunk = AIMessageChunk(
                    content="", additional_kwargs={"reasoning": raciocinio}
                )
                pedaco = ChatGenerationChunk(message=chunk)
                if run_manager:
                    await run_manager.on_llm_new_token("", chunk=pedaco)
                yield pedaco

            tool_calls_bruto = delta.get("tool_calls")
            if tool_calls_bruto:
                # Fragmentado em múltiplos chunks por `index` — o LangGraph
                # acumula via `AIMessageChunk.__add__` e resolve pra tool
                # call completa quando o stream termina. Sem isso, o modelo
                # nunca conseguia de fato chamar uma tool no caminho
                # streaming (só no não-streaming).
                chunk = AIMessageChunk(
                    content="",
                    tool_call_chunks=_parse_tool_call_chunks(tool_calls_bruto),
                )
                pedaco = ChatGenerationChunk(message=chunk)
                if run_manager:
                    await run_manager.on_llm_new_token("", chunk=pedaco)
                yield pedaco

            texto = delta.get("content")
            if texto:
                chunk = AIMessageChunk(content=texto)
                pedaco = ChatGenerationChunk(message=chunk)
                if run_manager:
                    await run_manager.on_llm_new_token(texto, chunk=pedaco)
                yield pedaco

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        msg = (
            "VectoraOpenRouterChat é async-only (CLAUDE.md regra 10) — "
            "use ainvoke/astream."
        )
        raise NotImplementedError(msg)
