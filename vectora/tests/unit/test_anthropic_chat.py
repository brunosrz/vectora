"""``VectoraAnthropicChat`` — chat nativo da Anthropic (Messages API).

Substitui `ChatAnthropic` (`langchain_anthropic`). Caminho crítico do agente:
tool-calling e streaming com acumulação de `input_json_delta` (string JSON
parcial), incluindo o corte no meio de uma string (não só entre keys).
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
    ToolMessage,
)

from backend.llm.anthropic.chat import VectoraAnthropicChat
from backend.llm.anthropic.client import AnthropicClient, AnthropicResponseError


def _modelo(handler, **kwargs) -> VectoraAnthropicChat:
    client = AnthropicClient(
        api_key="sk-ant-test",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return VectoraAnthropicChat(model="claude-opus-5", client=client, **kwargs)


def _resposta_ok(texto: str = "Olá", **extra) -> dict:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": texto}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 3},
        **extra,
    }


class TestGenerate:
    @pytest.mark.asyncio
    async def test_prompt_simples_devolve_conteudo(self):
        def handler(_req):
            return httpx.Response(200, json=_resposta_ok("Olá da Anthropic"))

        resultado = await _modelo(handler)._agenerate([HumanMessage("oi")])

        assert resultado.generations[0].message.content == "Olá da Anthropic"

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
    async def test_resposta_sem_content_vira_erro_tipado(self):
        def handler(_req):
            return httpx.Response(200, json={"id": "msg_1"})

        with pytest.raises(AnthropicResponseError, match="content"):
            await _modelo(handler)._agenerate([HumanMessage("oi")])


class TestConversaoDeMensagens:
    @pytest.mark.asyncio
    async def test_system_vira_campo_top_level_nao_mensagem(self):
        """A Anthropic não tem role `system` em `messages` — é um campo
        próprio no corpo do request."""
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        await _modelo(handler)._agenerate(
            [SystemMessage("sistema"), HumanMessage("usuário")]
        )

        roles = [m["role"] for m in capturado["messages"]]
        assert roles == ["user"]

    @pytest.mark.asyncio
    async def test_system_prompt_marcado_com_cache_control_ephemeral(self):
        """Prompt caching (GA na Messages API) — substitui o
        `betas=["prompt-caching-2024-07-31"]` do `ChatAnthropic` antigo, que
        injetava esse marker automaticamente."""
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        await _modelo(handler)._agenerate(
            [SystemMessage("sistema longo"), HumanMessage("usuário")]
        )

        assert capturado["system"] == [
            {
                "type": "text",
                "text": "sistema longo",
                "cache_control": {"type": "ephemeral"},
            }
        ]

    @pytest.mark.asyncio
    async def test_cache_system_prompt_false_manda_string_pura(self):
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        modelo = _modelo(handler, cache_system_prompt=False)
        await modelo._agenerate([SystemMessage("sistema"), HumanMessage("usuário")])

        assert capturado["system"] == "sistema"

    @pytest.mark.asyncio
    async def test_tool_message_vira_user_com_tool_result(self):
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        await _modelo(handler)._agenerate(
            [
                HumanMessage("usuário"),
                AIMessage("assistente"),
                ToolMessage("resultado", tool_call_id="call_1"),
            ]
        )

        ultima = capturado["messages"][-1]
        assert ultima["role"] == "user"
        assert ultima["content"][0]["type"] == "tool_result"
        assert ultima["content"][0]["tool_use_id"] == "call_1"

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
    async def test_tools_vao_no_formato_input_schema(self):
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

        tool = capturado["tools"][0]
        assert tool["name"] == "somar"
        assert "input_schema" in tool
        assert "type" not in tool  # sem wrapper type:"function" (diferente da OpenAI)

    @pytest.mark.asyncio
    async def test_tool_call_nao_streaming_volta_montada(self):
        def handler(_req):
            return httpx.Response(
                200,
                json=_resposta_ok(
                    "",
                    content=[
                        {
                            "type": "tool_use",
                            "id": "call_1",
                            "name": "somar",
                            "input": {"a": 1, "b": 2},
                        }
                    ],
                ),
            )

        resultado = await _modelo(handler)._agenerate([HumanMessage("some 1 e 2")])
        mensagem = resultado.generations[0].message
        assert isinstance(mensagem, AIMessage)
        assert mensagem.tool_calls[0]["name"] == "somar"
        assert mensagem.tool_calls[0]["args"] == {"a": 1, "b": 2}
        assert mensagem.tool_calls[0]["id"] == "call_1"


class TestStreaming:
    @pytest.mark.asyncio
    async def test_chunks_de_texto_saem_na_ordem(self):
        corpo = (
            b'event: message_start\ndata: {"type":"message_start","message":'
            b'{"usage":{"input_tokens":5}}}\n\n'
            b'event: content_block_start\ndata: {"type":"content_block_start",'
            b'"index":0,"content_block":{"type":"text","text":""}}\n\n'
            b'event: content_block_delta\ndata: {"type":"content_block_delta",'
            b'"index":0,"delta":{"type":"text_delta","text":"Oi"}}\n\n'
            b'event: content_block_delta\ndata: {"type":"content_block_delta",'
            b'"index":0,"delta":{"type":"text_delta","text":" mundo"}}\n\n'
            b'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n'
            b'event: message_stop\ndata: {"type":"message_stop"}\n\n'
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
    async def test_ping_e_ignorado(self):
        corpo = (
            b'event: ping\ndata: {"type":"ping"}\n\n'
            b'event: message_stop\ndata: {"type":"message_stop"}\n\n'
        )

        def handler(_req):
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        assert chunks == []

    @pytest.mark.asyncio
    async def test_evento_error_no_meio_do_stream_vira_excecao_tipada(self):
        """Erro/borda: overload/erros aparecem como `event: error` no meio do
        stream (confirmado pela doc oficial) — não pode travar o turno
        silenciosamente."""
        corpo = (
            b'event: content_block_delta\ndata: {"type":"content_block_delta",'
            b'"index":0,"delta":{"type":"text_delta","text":"parcial"}}\n\n'
            b'event: error\ndata: {"type":"error","error":'
            b'{"type":"overloaded_error","message":"Overloaded"}}\n\n'
        )

        def handler(_req):
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        with pytest.raises(AnthropicResponseError, match="Overloaded"):
            _ = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]


class TestStreamingToolCallsEUsage:
    """Caso obrigatório de regressão: `input_json_delta` fragmentado em
    múltiplos chunks, incluindo corte no MEIO de uma string JSON (não só
    entre keys), reconstruído corretamente só depois de todos os fragmentos."""

    @pytest.mark.asyncio
    async def test_tool_call_fragmentada_com_corte_no_meio_de_string(self):
        corpo = (
            b'event: content_block_start\ndata: {"type":"content_block_start",'
            b'"index":0,"content_block":{"type":"tool_use","id":"call_1",'
            b'"name":"file_read","input":{}}}\n\n'
            b'event: content_block_delta\ndata: {"type":"content_block_delta",'
            b'"index":0,"delta":{"type":"input_json_delta","partial_json":'
            b'"{\\"path\\": \\"a"}}\n\n'
            b'event: content_block_delta\ndata: {"type":"content_block_delta",'
            b'"index":0,"delta":{"type":"input_json_delta","partial_json":'
            b'".py\\"}"}}\n\n'
            b'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n'
            b'event: message_stop\ndata: {"type":"message_stop"}\n\n'
        )

        def handler(_req):
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        acumulado = cast("AIMessageChunk", chunks[0].message)
        for c in chunks[1:]:
            acumulado = cast("AIMessageChunk", acumulado + c.message)

        assert acumulado.tool_calls == [
            {
                "name": "file_read",
                "args": {"path": "a.py"},
                "id": "call_1",
                "type": "tool_call",
            }
        ]

    @pytest.mark.asyncio
    async def test_usage_do_message_delta_vira_usage_metadata_cumulativo(self):
        corpo = (
            b'event: content_block_delta\ndata: {"type":"content_block_delta",'
            b'"index":0,"delta":{"type":"text_delta","text":"oi"}}\n\n'
            b'event: message_delta\ndata: {"type":"message_delta","delta":'
            b'{"stop_reason":"end_turn"},"usage":{"output_tokens":15}}\n\n'
            b'event: message_stop\ndata: {"type":"message_stop"}\n\n'
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
        assert com_usage[0].usage_metadata["output_tokens"] == 15
