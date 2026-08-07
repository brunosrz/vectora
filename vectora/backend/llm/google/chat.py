"""``VectoraGoogleChat`` — chat do Google Gemini (`generateContent`/
`streamGenerateContent`) como ``BaseChatModel``.

Substitui ``ChatGoogleGenerativeAI`` (``langchain_google_genai``). Modelo de
streaming diferente de Anthropic/OpenAI: cada evento SSE é o objeto
`GenerateContentResponse` **inteiro**, não um delta de um campo isolado —
mas os `parts[].text` entre chunks são incrementais (concatenar na ordem de
chegada), e `functionCall.args` sempre chega como objeto JSON completo num
único chunk (sem fragmentação incremental como Anthropic/OpenAI).
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

from backend.llm.google.client import GoogleGenAIClient, GoogleGenAIResponseError

logger = logging.getLogger(__name__)

_HARM_CATEGORIES = (
    "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "HARM_CATEGORY_DANGEROUS_CONTENT",
    "HARM_CATEGORY_CIVIC_INTEGRITY",
)


def _safety_settings_permissivos() -> list[dict]:
    """Threshold mais permissivo em toda categoria — o Vectora não filtra
    conteúdo, o que o modelo aceita gerar é decisão do modelo."""
    return [
        {"category": categoria, "threshold": "BLOCK_NONE"}
        for categoria in _HARM_CATEGORIES
    ]


def _to_google_tool(tool: Any) -> dict:
    """Converte pro formato `functionDeclarations` do Gemini — sem wrapper
    `type:"function"`, schema direto em `parameters`."""
    convertida = convert_to_openai_tool(tool)
    funcao = convertida.get("function", convertida)
    return {
        "name": funcao.get("name", ""),
        "description": funcao.get("description", ""),
        "parameters": funcao.get("parameters") or {"type": "object", "properties": {}},
    }


def _to_google_contents(
    messages: list[BaseMessage],
) -> tuple[dict | None, list[dict]]:
    """Separa `system` (campo `systemInstruction` top-level) do resto, e
    traduz pro formato `contents[].parts[]` — `functionCall`/`functionResponse`
    em vez de roles `tool`/tool_calls como Chat Completions."""
    partes_sistema: list[str] = []
    contents: list[dict] = []

    for msg in messages:
        if msg.type == "system":
            partes_sistema.append(str(msg.content))
            continue

        if msg.type == "human":
            contents.append({"role": "user", "parts": [{"text": str(msg.content)}]})
            continue

        if msg.type == "tool":
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": getattr(msg, "name", "") or "",
                                "response": {"result": str(msg.content)},
                            }
                        }
                    ],
                }
            )
            continue

        if msg.type == "ai":
            chamadas = getattr(msg, "tool_calls", None)
            partes: list[dict] = []
            if msg.content:
                partes.append({"text": str(msg.content)})
            if chamadas:
                partes.extend(
                    {
                        "functionCall": {
                            "name": c.get("name", ""),
                            "args": c.get("args") or {},
                        }
                    }
                    for c in chamadas
                )
            contents.append({"role": "model", "parts": partes})
            continue

        msg_erro = f"Mensagem de tipo {msg.type!r} não tem role equivalente no Gemini"
        raise ValueError(msg_erro)

    system = (
        {"parts": [{"text": "\n\n".join(partes_sistema)}]} if partes_sistema else None
    )
    return system, contents


def _parse_candidate_parts(parts: list) -> tuple[str, list[ToolCall]]:
    texto_partes: list[str] = []
    chamadas: list[ToolCall] = []
    for parte in parts or []:
        if "text" in parte:
            texto_partes.append(parte["text"])
        elif "functionCall" in parte:
            fc = parte["functionCall"]
            chamadas.append(
                ToolCall(
                    name=fc.get("name", ""),
                    args=fc.get("args") or {},
                    id=fc.get("name", "") + "_call",
                    type="tool_call",
                )
            )
    return "".join(texto_partes), chamadas


def _usage_metadata(usage: dict | None) -> dict | None:
    if not usage:
        return None
    entrada = int(usage.get("promptTokenCount") or 0)
    saida = int(usage.get("candidatesTokenCount") or 0)
    return {
        "input_tokens": entrada,
        "output_tokens": saida,
        "total_tokens": int(usage.get("totalTokenCount") or entrada + saida),
    }


class VectoraGoogleChat(BaseChatModel):
    """Chat model nativo do Google Gemini."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str
    client: GoogleGenAIClient
    temperature: float | None = None
    #: Preenchido por `bind_tools`, já no formato `functionDeclarations`.
    tools: list[dict] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "vectora-google-genai"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> VectoraGoogleChat:
        convertidas = [_to_google_tool(t) for t in tools]
        return self.model_copy(update={"tools": convertidas, **kwargs})

    def _payload(self, messages: list[BaseMessage]) -> dict:
        system, contents = _to_google_contents(messages)
        corpo: dict[str, Any] = {
            "contents": contents,
            "safetySettings": _safety_settings_permissivos(),
        }
        if system:
            corpo["systemInstruction"] = system
        if self.temperature is not None:
            corpo["generationConfig"] = {"temperature": self.temperature}
        if self.tools:
            corpo["tools"] = [{"functionDeclarations": self.tools}]
        return corpo

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        corpo = self._payload(messages)
        resposta = await self.client.generate_content(self.model, corpo)
        candidatos = resposta.get("candidates")
        if not isinstance(candidatos, list) or not candidatos:
            msg = (
                "Google Gemini respondeu sem `candidates` — resposta bloqueada "
                f"(safety filter?) ou inutilizável: {resposta.get('promptFeedback')!r}"
            )
            raise GoogleGenAIResponseError(msg)

        candidato = candidatos[0]
        parts = (candidato.get("content") or {}).get("parts") or []
        texto, chamadas = _parse_candidate_parts(parts)
        usage = resposta.get("usageMetadata") or {}
        ai = AIMessage(
            content=texto,
            tool_calls=chamadas,
            usage_metadata=_usage_metadata(usage),  # type: ignore[arg-type]
            response_metadata={
                "model_name": self.model,
                "finish_reason": candidato.get("finishReason"),
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
        corpo = self._payload(messages)
        proximo_index = 0
        # `usageMetadata` aparece em CADA chunk como valor mais recente (já
        # embute o total até aquele ponto) — se emitíssemos um chunk de uso a
        # cada evento, o `AIMessageChunk.__add__` do LangChain SOMARIA os
        # campos numéricos entre chunks, inflando o total. Guarda só o
        # último valor visto e emite UM chunk de uso ao final do stream.
        ultimo_usage: dict | None = None

        async for evento in self.client.stream_generate_content(self.model, corpo):
            candidatos = evento.get("candidates")
            if not isinstance(candidatos, list) or not candidatos:
                # Chunk sem candidates (bloqueio por safety filter no meio do
                # stream) vira erro tipado — nunca resposta vazia silenciosa.
                feedback = evento.get("promptFeedback")
                if feedback:
                    msg = f"Google Gemini bloqueou o stream: {feedback!r}"
                    raise GoogleGenAIResponseError(msg)
                continue

            candidato = candidatos[0]
            parts = (candidato.get("content") or {}).get("parts") or []
            texto, chamadas = _parse_candidate_parts(parts)

            if texto:
                chunk = AIMessageChunk(content=texto)
                pedaco = ChatGenerationChunk(message=chunk)
                if run_manager:
                    await run_manager.on_llm_new_token(texto, chunk=pedaco)
                yield pedaco

            for chamada in chamadas:
                # `functionCall.args` sempre chega completo num único chunk
                # (sem fragmentação de JSON parcial como Anthropic/OpenAI) —
                # ainda assim emitido via `tool_call_chunks` (não `tool_calls`
                # direto), porque é isso que `AIMessageChunk.__add__` usa pra
                # derivar `.tool_calls` depois de acumular vários chunks.
                chunk = AIMessageChunk(
                    content="",
                    tool_call_chunks=[
                        ToolCallChunk(
                            name=chamada["name"],
                            args=json.dumps(chamada["args"], ensure_ascii=False),
                            id=chamada["id"],
                            index=proximo_index,
                        )
                    ],
                )
                proximo_index += 1
                pedaco = ChatGenerationChunk(message=chunk)
                if run_manager:
                    await run_manager.on_llm_new_token("", chunk=pedaco)
                yield pedaco

            usage = evento.get("usageMetadata")
            if usage:
                ultimo_usage = usage

        if ultimo_usage:
            chunk = AIMessageChunk(
                content="",
                usage_metadata=_usage_metadata(ultimo_usage),  # type: ignore[arg-type]
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
        msg = (
            "VectoraGoogleChat é async-only (CLAUDE.md regra 10) — use ainvoke/astream."
        )
        raise NotImplementedError(msg)
