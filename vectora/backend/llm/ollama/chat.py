"""``VectoraOllamaChat`` — chat do Ollama como ``BaseChatModel``.

Sobre ``POST /api/chat``, não sobre o endpoint OpenAI-compat: é o nativo que
expõe ``message.thinking`` em campo próprio, ``images`` por mensagem e os
contadores de token. (O Hermes usa o OpenAI-compat pro chat e HTTP direto só
pros metadados — aqui o chat também é nativo por causa do `thinking`.)

Dois invariantes:

- ``thinking`` nunca entra em ``content`` — concatenar mistura raciocínio e
  resposta na tela.
- Imagem vai no array ``images`` em base64 **puro**, sem o prefixo ``data:``.
  Mandar no formato de content block da OpenAI faz o modelo não ver a imagem.
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
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolCall
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import ConfigDict, Field

from backend.llm.ollama.client import OllamaClient, OllamaResponseError

logger = logging.getLogger(__name__)

_ROLE_POR_TIPO = {
    "system": "system",
    "human": "user",
    "ai": "assistant",
    "tool": "tool",
    "function": "tool",
}


def _split_conteudo(content: Any) -> tuple[str, list[str]]:
    """Separa texto de imagens num content multimodal do LangChain.

    Devolve `(texto, imagens_base64_puras)`. O prefixo `data:image/...;base64,`
    é removido: o Ollama espera só o payload.
    """
    if isinstance(content, str):
        return content, []

    partes: list[str] = []
    imagens: list[str] = []
    for bloco in content or []:
        if not isinstance(bloco, dict):
            continue
        if bloco.get("type") == "text":
            partes.append(str(bloco.get("text") or ""))
        elif bloco.get("type") == "image_url":
            url = bloco.get("image_url")
            bruto = url.get("url", "") if isinstance(url, dict) else str(url or "")
            imagens.append(bruto.split(",", 1)[-1] if "," in bruto else bruto)
    return "".join(partes), imagens


def _to_ollama_message(msg: BaseMessage) -> dict:
    role = _ROLE_POR_TIPO.get(msg.type)
    if role is None:
        msg_erro = f"Mensagem de tipo {msg.type!r} não tem role equivalente no Ollama"
        raise ValueError(msg_erro)

    texto, imagens = _split_conteudo(msg.content)
    saida: dict[str, Any] = {"role": role, "content": texto}
    if imagens:
        saida["images"] = imagens

    chamadas = getattr(msg, "tool_calls", None)
    if role == "assistant" and chamadas:
        saida["tool_calls"] = [
            {"function": {"name": c.get("name", ""), "arguments": c.get("args") or {}}}
            for c in chamadas
        ]
    return saida


def _parse_tool_calls(bruto: list) -> list[ToolCall]:
    """`arguments` vem como objeto no Ollama moderno e como string no antigo.

    Aceitar os dois evita quebrar contra servidor desatualizado — e fazer
    `json.loads` de um dict estouraria.
    """
    chamadas: list[ToolCall] = []
    for item in bruto or []:
        funcao = item.get("function") or {}
        args = funcao.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        chamadas.append(
            ToolCall(
                name=funcao.get("name", ""),
                args=args if isinstance(args, dict) else {},
                id=item.get("id"),
                type="tool_call",
            )
        )
    return chamadas


class VectoraOllamaChat(BaseChatModel):
    """Chat model nativo do Ollama."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str
    client: OllamaClient
    temperature: float | None = None
    #: `true`/`false` ou nível (`"low"`/`"medium"`/`"high"`/`"max"`). Ausente do
    #: payload quando None — mandar `false` num modelo sem a capacidade é
    #: diferente de não mandar nada.
    think: bool | str | None = None
    #: JSON schema pra structured output (campo `format` do Ollama).
    response_format: dict | str | None = None
    tools: list[dict] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "vectora-ollama"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> VectoraOllamaChat:
        convertidas = [convert_to_openai_tool(t) for t in tools]
        return self.model_copy(update={"tools": convertidas, **kwargs})

    def _payload(self, messages: list[BaseMessage], **kwargs: Any) -> dict:
        from backend.settings import settings

        corpo: dict[str, Any] = {
            "model": self.model,
            "messages": [_to_ollama_message(m) for m in messages],
        }
        options: dict[str, Any] = {
            "num_ctx": settings.ollama_num_ctx,
            "num_predict": settings.ollama_num_predict,
        }
        if self.temperature is not None:
            options["temperature"] = self.temperature
        corpo["options"] = options
        if self.tools:
            corpo["tools"] = self.tools
        if self.think is not None:
            corpo["think"] = self.think
        if self.response_format is not None:
            corpo["format"] = self.response_format
        if kwargs.get("keep_alive") is not None:
            corpo["keep_alive"] = kwargs["keep_alive"]
        return corpo

    @staticmethod
    def _mensagem_da_resposta(corpo: dict) -> dict:
        mensagem = corpo.get("message")
        if not isinstance(mensagem, dict):
            msg = (
                "Ollama respondeu sem `message` — resposta inutilizável "
                f"(model={corpo.get('model')!r})"
            )
            raise OllamaResponseError(msg)
        return mensagem

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        corpo = self._payload(messages, **kwargs)
        corpo["stream"] = False
        if stop:
            corpo.setdefault("options", {})["stop"] = stop

        resposta = await self.client.post_json("/api/chat", corpo)
        mensagem = self._mensagem_da_resposta(resposta)

        entrada = int(resposta.get("prompt_eval_count") or 0)
        saida = int(resposta.get("eval_count") or 0)
        metadata: dict[str, Any] = {
            "model_name": resposta.get("model", self.model),
            "finish_reason": resposta.get("done_reason"),
        }
        if mensagem.get("thinking"):
            metadata["reasoning"] = mensagem["thinking"]

        ai = AIMessage(
            content=mensagem.get("content") or "",
            tool_calls=_parse_tool_calls(mensagem.get("tool_calls") or []),
            usage_metadata={
                "input_tokens": entrada,
                "output_tokens": saida,
                "total_tokens": entrada + saida,
            },
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
            corpo.setdefault("options", {})["stop"] = stop

        async for evento in self.client.stream_ndjson("/api/chat", corpo):
            mensagem = evento.get("message") or {}

            raciocinio = mensagem.get("thinking")
            if raciocinio:
                chunk = AIMessageChunk(
                    content="", additional_kwargs={"reasoning": raciocinio}
                )
                pedaco = ChatGenerationChunk(message=chunk)
                if run_manager:
                    await run_manager.on_llm_new_token("", chunk=pedaco)
                yield pedaco

            texto = mensagem.get("content")
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
            "VectoraOllamaChat é async-only (CLAUDE.md regra 10) — use ainvoke/astream."
        )
        raise NotImplementedError(msg)
