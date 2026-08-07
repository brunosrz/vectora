"""``VectoraGoogleChat`` — chat nativo do Google Gemini
(`generateContent`/`streamGenerateContent`).

Substitui `ChatGoogleGenerativeAI` (`langchain_google_genai`). Caso
obrigatório de regressão: `functionCall` misturado com `text` no mesmo
array `parts[]`, streaming multi-chunk, ordem preservada — diferente de
Anthropic/OpenAI, aqui não há fragmentação de JSON parcial em tool calls.
"""

from __future__ import annotations

from typing import cast

import httpx
import pytest
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
)

from backend.llm.google.chat import VectoraGoogleChat
from backend.llm.google.client import GoogleGenAIClient, GoogleGenAIResponseError


def _modelo(handler, **kwargs) -> VectoraGoogleChat:
    client = GoogleGenAIClient(
        api_key="ga-test",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return VectoraGoogleChat(model="gemini-2.5-flash", client=client, **kwargs)


def _resposta_ok(texto: str = "Olá", **extra) -> dict:
    return {
        "candidates": [
            {
                "content": {"role": "model", "parts": [{"text": texto}]},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 3,
            "totalTokenCount": 13,
        },
        **extra,
    }


class TestGenerate:
    @pytest.mark.asyncio
    async def test_prompt_simples_devolve_conteudo(self):
        def handler(_req):
            return httpx.Response(200, json=_resposta_ok("Olá do Gemini"))

        resultado = await _modelo(handler)._agenerate([HumanMessage("oi")])

        assert resultado.generations[0].message.content == "Olá do Gemini"

    @pytest.mark.asyncio
    async def test_usage_metadata_mapeado(self):
        def handler(_req):
            return httpx.Response(200, json=_resposta_ok())

        resultado = await _modelo(handler)._agenerate([HumanMessage("oi")])
        msg = resultado.generations[0].message

        assert isinstance(msg, AIMessage)
        assert msg.usage_metadata is not None
        assert msg.usage_metadata["input_tokens"] == 10
        assert msg.usage_metadata["output_tokens"] == 3
        assert msg.usage_metadata["total_tokens"] == 13

    @pytest.mark.asyncio
    async def test_resposta_sem_candidates_vira_erro_tipado(self):
        """Erro/borda: bloqueio por safety filter — sem `candidates` — vira
        exceção tipada, nunca resposta vazia silenciosa."""

        def handler(_req):
            return httpx.Response(
                200, json={"promptFeedback": {"blockReason": "SAFETY"}}
            )

        with pytest.raises(GoogleGenAIResponseError, match="candidates"):
            await _modelo(handler)._agenerate([HumanMessage("oi")])


class TestConversaoDeMensagens:
    @pytest.mark.asyncio
    async def test_system_vira_system_instruction_top_level(self):
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        await _modelo(handler)._agenerate(
            [SystemMessage("sistema"), HumanMessage("usuário")]
        )

        assert capturado["systemInstruction"]["parts"][0]["text"] == "sistema"
        roles = [c["role"] for c in capturado["contents"]]
        assert roles == ["user"]

    @pytest.mark.asyncio
    async def test_safety_settings_permissivos_em_todas_categorias(self):
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        await _modelo(handler)._agenerate([HumanMessage("oi")])

        assert all(s["threshold"] == "BLOCK_NONE" for s in capturado["safetySettings"])
        assert len(capturado["safetySettings"]) == 5

    @pytest.mark.asyncio
    async def test_mensagem_de_role_desconhecido_falha(self):
        def handler(_req):
            return httpx.Response(200, json=_resposta_ok())

        estranha = HumanMessage("?")
        estranha.type = "extraterrestre"  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

        with pytest.raises(ValueError, match="extraterrestre"):
            await _modelo(handler)._agenerate([estranha])


class TestToolCalling:
    @pytest.mark.asyncio
    async def test_tools_vao_como_function_declarations(self):
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        ferramenta = {
            "type": "function",
            "function": {
                "name": "somar",
                "description": "soma dois números",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        modelo = _modelo(handler).bind_tools([ferramenta])  # type: ignore[attr-defined]
        await modelo._agenerate([HumanMessage("some 1 e 2")])

        decl = capturado["tools"][0]["functionDeclarations"][0]
        assert decl["name"] == "somar"
        assert "type" not in decl  # sem wrapper type:"function"

    @pytest.mark.asyncio
    async def test_tool_call_nao_streaming_volta_montada(self):
        def handler(_req):
            return httpx.Response(
                200,
                json=_resposta_ok(
                    "",
                    candidates=[
                        {
                            "content": {
                                "role": "model",
                                "parts": [
                                    {
                                        "functionCall": {
                                            "name": "somar",
                                            "args": {"a": 1, "b": 2},
                                        }
                                    }
                                ],
                            },
                            "finishReason": "STOP",
                        }
                    ],
                ),
            )

        resultado = await _modelo(handler)._agenerate([HumanMessage("some 1 e 2")])
        mensagem = resultado.generations[0].message
        assert isinstance(mensagem, AIMessage)
        assert mensagem.tool_calls[0]["name"] == "somar"
        assert mensagem.tool_calls[0]["args"] == {"a": 1, "b": 2}


class TestStreaming:
    @pytest.mark.asyncio
    async def test_chunks_de_texto_saem_na_ordem(self):
        corpo = (
            b"data: "
            + _sse_json(_resposta_ok("Oi"))
            + b"\n\n"
            + b"data: "
            + _sse_json(_resposta_ok(" mundo"))
            + b"\n\n"
        )

        def handler(_req):
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        texto = "".join(
            str(c.message.content) for c in chunks if isinstance(c.message.content, str)
        )

        assert texto == "Oi mundo"

    @pytest.mark.asyncio
    async def test_chunk_sem_candidates_e_sem_feedback_e_ignorado(self):
        corpo = b"data: " + _sse_json({}) + b"\n\n"

        def handler(_req):
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        assert chunks == []

    @pytest.mark.asyncio
    async def test_chunk_bloqueado_por_safety_vira_erro_tipado(self):
        corpo = (
            b"data: "
            + _sse_json({"promptFeedback": {"blockReason": "SAFETY"}})
            + b"\n\n"
        )

        def handler(_req):
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        with pytest.raises(GoogleGenAIResponseError, match="bloqueou"):
            _ = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]


class TestStreamingToolCallsEUsage:
    """Caso obrigatório de regressão: `functionCall` misturado com `text` no
    mesmo `parts[]`, streaming multi-chunk, confirma que nenhum dos dois se
    perde e a ordem de `parts[]` é respeitada."""

    @pytest.mark.asyncio
    async def test_text_e_function_call_no_mesmo_parts_nao_se_perdem(self):
        corpo = (
            b"data: "
            + _sse_json(
                {
                    "candidates": [
                        {
                            "content": {
                                "role": "model",
                                "parts": [
                                    {"text": "Vou checar o arquivo. "},
                                    {
                                        "functionCall": {
                                            "name": "file_read",
                                            "args": {"path": "a.py"},
                                        }
                                    },
                                ],
                            },
                            "finishReason": "STOP",
                        }
                    ]
                }
            )
            + b"\n\n"
        )

        def handler(_req):
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        acumulado = cast("AIMessageChunk", chunks[0].message)
        for c in chunks[1:]:
            acumulado = cast("AIMessageChunk", acumulado + c.message)

        assert "Vou checar o arquivo." in str(acumulado.content)
        assert acumulado.tool_calls[0]["name"] == "file_read"
        assert acumulado.tool_calls[0]["args"] == {"path": "a.py"}

    @pytest.mark.asyncio
    async def test_usage_do_ultimo_chunk_nao_e_somado_com_anteriores(self):
        """`usageMetadata` já embute o total até aquele ponto — se fosse
        somado entre chunks (comportamento padrão de merge do LangChain), o
        total ficaria inflado."""
        corpo = (
            b"data: "
            + _sse_json(
                _resposta_ok(
                    "a",
                    usageMetadata={
                        "promptTokenCount": 10,
                        "candidatesTokenCount": 1,
                        "totalTokenCount": 11,
                    },
                )
            )
            + b"\n\n"
            + b"data: "
            + _sse_json(
                _resposta_ok(
                    "b",
                    usageMetadata={
                        "promptTokenCount": 10,
                        "candidatesTokenCount": 3,
                        "totalTokenCount": 13,
                    },
                )
            )
            + b"\n\n"
        )

        def handler(_req):
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        mensagens = [cast("AIMessageChunk", c.message) for c in chunks]
        com_usage = [m for m in mensagens if m.usage_metadata]

        assert len(com_usage) == 1
        assert com_usage[0].usage_metadata is not None
        assert com_usage[0].usage_metadata["output_tokens"] == 3
        assert com_usage[0].usage_metadata["total_tokens"] == 13


def _sse_json(obj: dict) -> bytes:
    import json as _json

    return _json.dumps(obj).encode()
