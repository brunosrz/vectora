"""``GoogleChatClient`` — chat nativo do Google Gemini (`generateContent`/
`streamGenerateContent`), implementa o Protocol ``ChatClient``
(``backend/llm/base.py``).

Arquivo separado de ``chat.py`` (``VectoraGoogleChat``, subclasse de
``BaseChatModel``) pelo mesmo motivo documentado em
``backend/llm/openai/chat_client.py``: o núcleo agêntico em produção ainda
depende do adapter LangChain até o loop de conversa nativo existir e
consumir esta classe. Quando o dispatch cortar pro motor nativo,
``chat.py`` é removido.

Peculiaridades da API do Gemini que o parser respeita:
- `systemInstruction` é um campo top-level separado, não um item de `contents`.
- Tool result (papel `tool` no `VMessage`) vira `contents[].parts[].
  functionResponse` com role `user` — o Gemini não tem role `tool` própria.
- Cada evento SSE do streaming é o `GenerateContentResponse` **inteiro**
  reemitido, não um delta de campo isolado — mas os `parts[].text` entre
  chunks são incrementais (concatenar na ordem de chegada), e
  `functionCall.args` sempre chega como objeto JSON completo num único
  chunk (sem fragmentação parcial como Anthropic/OpenAI).
- `usageMetadata` aparece em CADA chunk como valor mais recente (já embute
  o total até aquele ponto) — nunca somar entre chunks; emitir só o último
  valor visto, no fim do stream.
- Chunk sem `candidates` (bloqueio por safety filter) vira erro tipado,
  nunca resposta vazia silenciosa.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from backend.llm.google.client import GoogleGenAIClient, GoogleGenAIResponseError
from backend.vtypes.message import (
    ContentBlock,
    MessageRole,
    ToolCall,
    ToolCallChunk,
    VMessage,
    VMessageChunk,
)

if TYPE_CHECKING:
    from backend.tools.registry import ToolSpec

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


def _strip_gemini_unsupported_keys(schema: Any) -> Any:
    """Remove chaves de JSON Schema que a API do Gemini rejeita com 400
    ("Cannot find field") — o schema de function-calling do Gemini é um
    subconjunto de OpenAPI 3.0, sem `additionalProperties`. Recursa em
    `properties`/`items`/`anyOf`/`oneOf`/`allOf` porque o Pydantic v2 injeta
    `additionalProperties:false` em todo objeto, inclusive dentro de cada
    branch de `anyOf` gerado por campo `Optional[...]`."""
    if isinstance(schema, dict):
        return {
            k: _strip_gemini_unsupported_keys(v)
            for k, v in schema.items()
            if k != "additionalProperties"
        }
    if isinstance(schema, list):
        return [_strip_gemini_unsupported_keys(item) for item in schema]
    return schema


def _to_google_tool(spec: ToolSpec) -> dict:
    """`functionDeclarations` do Gemini — sem wrapper `type:"function"`,
    schema direto em `parameters`."""
    convertida = spec.openai_schema()["function"]
    parametros = convertida.get("parameters") or {"type": "object", "properties": {}}
    return {
        "name": convertida.get("name", ""),
        "description": convertida.get("description", ""),
        "parameters": _strip_gemini_unsupported_keys(parametros),
    }


def _assistant_parts(msg: VMessage) -> list[dict]:
    partes: list[dict] = []
    texto = msg.text()
    if texto:
        partes.append({"text": texto})
    partes.extend(
        {"functionCall": {"name": tc.name, "args": tc.args}} for tc in msg.tool_calls
    )
    return partes


def _to_google_contents(messages: list[VMessage]) -> tuple[dict | None, list[dict]]:
    """Extrai `systemInstruction` (concatenado, se houver mais de uma
    mensagem system) e traduz o resto pro formato `contents[].parts[]` do
    Gemini — `functionCall`/`functionResponse` em vez de roles `tool`/
    tool_calls como Chat Completions."""
    partes_sistema: list[str] = []
    contents: list[dict] = []

    for msg in messages:
        if msg.role == MessageRole.SYSTEM:
            texto = msg.text()
            if texto:
                partes_sistema.append(texto)
            continue

        if msg.role == MessageRole.USER:
            contents.append({"role": "user", "parts": [{"text": msg.text()}]})
            continue

        if msg.role == MessageRole.TOOL:
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": msg.name or "",
                                "response": {"result": msg.text()},
                            }
                        }
                    ],
                }
            )
            continue

        if msg.role == MessageRole.ASSISTANT:
            contents.append({"role": "model", "parts": _assistant_parts(msg)})
            continue

        erro = f"Mensagem de role {msg.role!r} não tem equivalente no Gemini"
        raise ValueError(erro)

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
            nome = fc.get("name", "")
            chamadas.append(
                ToolCall(id=f"{nome}_call", name=nome, args=fc.get("args") or {})
            )
    return "".join(texto_partes), chamadas


def _usage_metadata(usage: dict | None) -> dict[str, int] | None:
    if not usage:
        return None
    entrada = int(usage.get("promptTokenCount") or 0)
    saida = int(usage.get("candidatesTokenCount") or 0)
    return {
        "input_tokens": entrada,
        "output_tokens": saida,
        "total_tokens": int(usage.get("totalTokenCount") or entrada + saida),
    }


class GoogleChatClient:
    """Chat client nativo do Google Gemini — implementa o Protocol
    ``ChatClient``, async-only (CLAUDE.md regra 10)."""

    def __init__(self, model: str, client: GoogleGenAIClient) -> None:
        self.model = model
        self.client = client

    def _payload(
        self,
        messages: list[VMessage],
        *,
        tools: list[ToolSpec] | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> dict:
        system, contents = _to_google_contents(messages)
        corpo: dict[str, Any] = {
            "contents": contents,
            "safetySettings": _safety_settings_permissivos(),
        }
        if system:
            corpo["systemInstruction"] = system
        generation_config: dict[str, Any] = {}
        if temperature is not None:
            generation_config["temperature"] = temperature
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens
        if generation_config:
            corpo["generationConfig"] = generation_config
        if tools:
            corpo["tools"] = [
                {"functionDeclarations": [_to_google_tool(t) for t in tools]}
            ]
        return corpo

    async def agenerate(
        self,
        messages: list[VMessage],
        *,
        tools: list[ToolSpec] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> VMessage:
        corpo = self._payload(
            messages, tools=tools, temperature=temperature, max_tokens=max_tokens
        )
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

        return VMessage(
            role=MessageRole.ASSISTANT,
            content=[ContentBlock(kind="text", text=texto)] if texto else [],
            tool_calls=chamadas,
            finish_reason="tool_calls" if chamadas else "stop",
        )

    async def astream(
        self,
        messages: list[VMessage],
        *,
        tools: list[ToolSpec] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[VMessageChunk]:
        corpo = self._payload(
            messages, tools=tools, temperature=temperature, max_tokens=max_tokens
        )
        proximo_index = 0
        # `usageMetadata` aparece em CADA chunk como valor mais recente (já
        # embute o total até aquele ponto) — nunca somar entre chunks. Guarda
        # só o último visto e emite UM chunk de uso ao final do stream.
        ultimo_usage: dict | None = None

        async for evento in self.client.stream_generate_content(self.model, corpo):
            candidatos = evento.get("candidates")
            if not isinstance(candidatos, list) or not candidatos:
                feedback = evento.get("promptFeedback")
                if feedback:
                    msg = f"Google Gemini bloqueou o stream: {feedback!r}"
                    raise GoogleGenAIResponseError(msg)
                continue

            candidato = candidatos[0]
            parts = (candidato.get("content") or {}).get("parts") or []
            texto, chamadas = _parse_candidate_parts(parts)

            if texto:
                yield VMessageChunk(delta_text=texto)

            for chamada in chamadas:
                # `functionCall.args` sempre chega completo num único chunk
                # (sem fragmentação de JSON parcial como Anthropic/OpenAI) —
                # ainda assim emitido via ToolCallChunk, formato comum que o
                # caller (backend/engine/conversation_loop.py) já acumula.
                yield VMessageChunk(
                    tool_call_chunks=[
                        ToolCallChunk(
                            index=proximo_index,
                            id=f"{chamada.name}_call",
                            name=chamada.name,
                            args_fragment=_dump_args(chamada.args),
                        )
                    ]
                )
                proximo_index += 1

            usage = evento.get("usageMetadata")
            if usage:
                ultimo_usage = usage

        if ultimo_usage:
            yield VMessageChunk(usage=_usage_metadata(ultimo_usage))


def _dump_args(args: dict) -> str:
    return json.dumps(args, ensure_ascii=False)
