"""``VectoraOpenAIChat`` — chat da OpenAI (Responses API) como ``BaseChatModel``.

Substitui ``ChatOpenAI`` (``langchain_openai``). A Responses API é o sucessor
recomendado da Chat Completions desde 2026 — usa `input`/`output` (items) em
vez de `messages`/`choices`, e streaming por eventos discretos tipados em vez
de deltas por campo único.

Edge case confirmado por pesquisa da documentação oficial: o servidor pode
emitir ``response.function_call_arguments.done`` **sem nenhum delta
anterior** — nesse caso o JSON completo já vem no próprio evento `.done`.
O parser não assume que sempre há deltas pra acumular.
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

from backend.llm.openai.client import OpenAIClient, OpenAIResponseError

logger = logging.getLogger(__name__)


def _normalize_strict_schema(schema: dict) -> dict:
    """Aplica os requisitos do `strict:true` da Responses API recursivamente:
    `additionalProperties:false` em todo objeto, e todo campo em `required`
    (campos opcionais viram `type:[tipo, "null"]`)."""
    schema = dict(schema)
    if schema.get("type") == "object" and "properties" in schema:
        props = schema["properties"]
        original_required = set(schema.get("required") or [])
        novo_props: dict[str, Any] = {}
        for nome, subschema in props.items():
            sub = (
                _normalize_strict_schema(subschema)
                if isinstance(subschema, dict)
                else subschema
            )
            if (
                nome not in original_required
                and isinstance(sub, dict)
                and "type" in sub
            ):
                tipo = sub["type"]
                if isinstance(tipo, str) and tipo != "null":
                    sub = {**sub, "type": [tipo, "null"]}
            novo_props[nome] = sub
        schema["properties"] = novo_props
        schema["required"] = list(props.keys())
        schema["additionalProperties"] = False
    return schema


def _to_openai_tool(tool: Any) -> dict:
    """Converte uma tool pro formato flat da Responses API
    (`{type, name, description, parameters, strict}`) — diferente do formato
    aninhado `{type:"function", function:{...}}` da Chat Completions."""
    convertida = convert_to_openai_tool(tool)
    funcao = convertida.get("function", convertida)
    parametros = funcao.get("parameters") or {"type": "object", "properties": {}}
    return {
        "type": "function",
        "name": funcao.get("name", ""),
        "description": funcao.get("description", ""),
        "parameters": _normalize_strict_schema(parametros),
        "strict": True,
    }


_ROLE_POR_TIPO = {"system": "system", "human": "user", "ai": "assistant"}


def _to_openai_input(messages: list[BaseMessage]) -> list[dict]:
    """Traduz mensagens LangChain pro formato `input` (lista de items) da
    Responses API. Tool calls viram items `function_call` separados; results
    de tool viram `function_call_output` — não são mensagens de role `tool`
    como na Chat Completions."""
    itens: list[dict] = []
    for msg in messages:
        if msg.type == "tool":
            itens.append(
                {
                    "type": "function_call_output",
                    "call_id": getattr(msg, "tool_call_id", ""),
                    "output": str(msg.content),
                }
            )
            continue

        role = _ROLE_POR_TIPO.get(msg.type)
        if role is None:
            msg_erro = (
                f"Mensagem de tipo {msg.type!r} não tem role equivalente na OpenAI"
            )
            raise ValueError(msg_erro)

        chamadas = getattr(msg, "tool_calls", None)
        if role == "assistant" and chamadas:
            if msg.content:
                itens.append({"role": "assistant", "content": str(msg.content)})
            itens.extend(
                {
                    "type": "function_call",
                    "call_id": c.get("id") or "",
                    "name": c.get("name", ""),
                    "arguments": json.dumps(c.get("args") or {}, ensure_ascii=False),
                }
                for c in chamadas
            )
            continue

        itens.append({"role": role, "content": str(msg.content)})
    return itens


def _parse_output_items(output: list) -> tuple[str, list[ToolCall], list[dict]]:
    texto_partes: list[str] = []
    validas: list[ToolCall] = []
    invalidas: list[dict] = []
    for item in output or []:
        tipo = item.get("type")
        if tipo == "message":
            texto_partes.extend(
                bloco.get("text", "")
                for bloco in item.get("content") or []
                if bloco.get("type") == "output_text"
            )
        elif tipo == "function_call":
            args_texto = item.get("arguments") or "{}"
            try:
                args = json.loads(args_texto)
            except (json.JSONDecodeError, TypeError):
                invalidas.append(
                    {
                        "name": item.get("name", ""),
                        "args": args_texto,
                        "id": item.get("call_id"),
                        "error": "arguments não é JSON válido",
                        "type": "invalid_tool_call",
                    }
                )
                continue
            validas.append(
                ToolCall(
                    name=item.get("name", ""),
                    args=args,
                    id=item.get("call_id"),
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
        "total_tokens": int(usage.get("total_tokens") or entrada + saida),
    }


class VectoraOpenAIChat(BaseChatModel):
    """Chat model nativo da OpenAI (Responses API)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str
    client: OpenAIClient
    temperature: float | None = None
    max_tokens: int | None = None
    #: Preenchido por `bind_tools`, já no formato flat da Responses API.
    tools: list[dict] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "vectora-openai"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> VectoraOpenAIChat:
        convertidas = [_to_openai_tool(t) for t in tools]
        return self.model_copy(update={"tools": convertidas, **kwargs})

    def _payload(self, messages: list[BaseMessage], **kwargs: Any) -> dict:
        corpo: dict[str, Any] = {
            "model": self.model,
            "input": _to_openai_input(messages),
        }
        if self.temperature is not None:
            corpo["temperature"] = self.temperature
        if self.max_tokens is not None:
            corpo["max_output_tokens"] = self.max_tokens
        if self.tools:
            corpo["tools"] = self.tools
        for chave in ("tool_choice", "instructions"):
            if kwargs.get(chave) is not None:
                corpo[chave] = kwargs[chave]
        return corpo

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        corpo = self._payload(messages, **kwargs)
        resposta = await self.client.create_response(corpo)
        output = resposta.get("output")
        if not isinstance(output, list):
            msg = (
                "OpenAI respondeu sem `output` utilizável — resposta "
                f"inutilizável (id={resposta.get('id')!r})"
            )
            raise OpenAIResponseError(msg)

        texto, validas, invalidas = _parse_output_items(output)
        usage = resposta.get("usage") or {}
        ai = AIMessage(
            content=texto,
            tool_calls=validas,
            invalid_tool_calls=invalidas,
            usage_metadata=_usage_metadata(usage),  # type: ignore[arg-type]
            response_metadata={
                "model_name": resposta.get("model", self.model),
                "status": resposta.get("status"),
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

        # Acumula por item_id — `response.output_item.added` cria a entrada
        # (name/call_id), `response.function_call_arguments.delta` fragmenta
        # os argumentos por múltiplos eventos, mapeados pro `index` que o
        # AIMessageChunk.__add__ do LangChain usa pra remontar a tool call.
        indices_por_item: dict[str, int] = {}
        nomes_por_item: dict[str, str] = {}
        call_ids_por_item: dict[str, str] = {}
        proximo_index = 0
        # Item que já recebeu `.done` sem nenhum delta anterior — o JSON
        # completo vem no próprio evento `.done`, não deve ser tratado como
        # fragmento incremental.
        recebeu_delta: set[str] = set()
        # `name` só pode ir no PRIMEIRO chunk de cada item — o LangChain
        # concatena o campo `name` entre chunks acumulados (mesma lógica de
        # `args`), então repetir o nome em cada delta duplicaria a string.
        nome_ja_emitido: set[str] = set()

        async for evento in self.client.stream_response(corpo):
            tipo = evento.get("type")

            if tipo == "response.output_item.added":
                item = evento.get("item") or {}
                if item.get("type") == "function_call":
                    item_id = item.get("id") or ""
                    indices_por_item[item_id] = proximo_index
                    nomes_por_item[item_id] = item.get("name", "")
                    call_ids_por_item[item_id] = item.get("call_id", "")
                    proximo_index += 1

            elif tipo == "response.function_call_arguments.delta":
                item_id = evento.get("item_id") or ""
                if item_id not in indices_por_item:
                    continue
                recebeu_delta.add(item_id)
                nome = (
                    nomes_por_item.get(item_id)
                    if item_id not in nome_ja_emitido
                    else None
                )
                nome_ja_emitido.add(item_id)
                chunk = AIMessageChunk(
                    content="",
                    tool_call_chunks=[
                        ToolCallChunk(
                            name=nome,
                            args=evento.get("delta", ""),
                            id=call_ids_por_item.get(item_id),
                            index=indices_por_item[item_id],
                        )
                    ],
                )
                pedaco = ChatGenerationChunk(message=chunk)
                if run_manager:
                    await run_manager.on_llm_new_token("", chunk=pedaco)
                yield pedaco

            elif tipo == "response.function_call_arguments.done":
                item_id = evento.get("item_id") or ""
                if item_id not in indices_por_item or item_id in recebeu_delta:
                    # Já veio fragmentado via delta — o `.done` só confirma
                    # o fim, o LangChain já acumulou o JSON completo.
                    continue
                # Edge case: nenhum delta chegou antes do `.done` — o JSON
                # completo está no próprio evento.
                chunk = AIMessageChunk(
                    content="",
                    tool_call_chunks=[
                        ToolCallChunk(
                            name=nomes_por_item.get(item_id),
                            args=evento.get("arguments", ""),
                            id=call_ids_por_item.get(item_id),
                            index=indices_por_item[item_id],
                        )
                    ],
                )
                pedaco = ChatGenerationChunk(message=chunk)
                if run_manager:
                    await run_manager.on_llm_new_token("", chunk=pedaco)
                yield pedaco

            elif tipo == "response.output_text.delta":
                texto = evento.get("delta", "")
                if texto:
                    chunk = AIMessageChunk(content=texto)
                    pedaco = ChatGenerationChunk(message=chunk)
                    if run_manager:
                        await run_manager.on_llm_new_token(texto, chunk=pedaco)
                    yield pedaco

            elif tipo == "response.completed":
                resposta = evento.get("response") or {}
                usage = resposta.get("usage")
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
        msg = (
            "VectoraOpenAIChat é async-only (CLAUDE.md regra 10) — use ainvoke/astream."
        )
        raise NotImplementedError(msg)
