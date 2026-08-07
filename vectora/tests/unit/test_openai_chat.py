"""``VectoraOpenAIChat`` — chat nativo da OpenAI (Responses API).

Substitui `ChatOpenAI` (`langchain_openai`). Caminho crítico do agente:
tool-calling, streaming e o edge case confirmado por pesquisa da doc oficial
— `response.function_call_arguments.done` pode chegar sem nenhum delta
anterior, com o JSON completo já no próprio evento.
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

from backend.llm.openai.chat import VectoraOpenAIChat
from backend.llm.openai.client import OpenAIClient, OpenAIResponseError


def _modelo(handler, **kwargs) -> VectoraOpenAIChat:
    client = OpenAIClient(
        api_key="sk-test",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return VectoraOpenAIChat(model="gpt-5", client=client, **kwargs)


def _resposta_ok(texto: str = "Olá", **extra) -> dict:
    return {
        "id": "resp_1",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": texto}],
            }
        ],
        "usage": {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13},
        **extra,
    }


class TestGenerate:
    @pytest.mark.asyncio
    async def test_prompt_simples_devolve_conteudo(self):
        def handler(_req):
            return httpx.Response(200, json=_resposta_ok("Olá da OpenAI"))

        resultado = await _modelo(handler)._agenerate([HumanMessage("oi")])

        assert resultado.generations[0].message.content == "Olá da OpenAI"

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
    async def test_resposta_sem_output_vira_erro_tipado(self):
        def handler(_req):
            return httpx.Response(200, json={"id": "resp_1"})

        with pytest.raises(OpenAIResponseError, match="output"):
            await _modelo(handler)._agenerate([HumanMessage("oi")])


class TestConversaoDeMensagens:
    @pytest.mark.asyncio
    async def test_roles_traduzidos_e_tool_message_vira_function_call_output(self):
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        await _modelo(handler)._agenerate(
            [
                SystemMessage("sistema"),
                HumanMessage("usuário"),
                AIMessage("assistente"),
                ToolMessage("resultado", tool_call_id="call_1"),
            ]
        )

        tipos = [item.get("type") for item in capturado["input"]]
        roles = [item.get("role") for item in capturado["input"]]
        assert roles == ["system", "user", "assistant", None]
        assert tipos[-1] == "function_call_output"
        assert capturado["input"][-1]["call_id"] == "call_1"

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
    async def test_strict_schema_normaliza_opcionais(self):
        """`strict:true` exige `additionalProperties:false` e todo campo em
        `required` — campos opcionais viram `type:[tipo, "null"]`."""
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        ferramenta = {
            "type": "function",
            "function": {
                "name": "buscar",
                "description": "busca algo",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            },
        }
        modelo = _modelo(handler).bind_tools([ferramenta])  # type: ignore[attr-defined]
        await modelo._agenerate([HumanMessage("busca x")])

        tool = capturado["tools"][0]
        assert tool["strict"] is True
        assert tool["parameters"]["additionalProperties"] is False
        assert set(tool["parameters"]["required"]) == {"query", "limit"}
        assert tool["parameters"]["properties"]["limit"]["type"] == ["integer", "null"]
        assert tool["parameters"]["properties"]["query"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_tool_call_nao_streaming_volta_montada(self):
        def handler(_req):
            return httpx.Response(
                200,
                json={
                    "id": "resp_1",
                    "status": "completed",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_1",
                            "name": "somar",
                            "arguments": '{"a": 1, "b": 2}',
                        }
                    ],
                },
            )

        resultado = await _modelo(handler)._agenerate([HumanMessage("some 1 e 2")])
        mensagem = resultado.generations[0].message
        assert isinstance(mensagem, AIMessage)
        assert mensagem.tool_calls[0]["name"] == "somar"
        assert mensagem.tool_calls[0]["args"] == {"a": 1, "b": 2}
        assert mensagem.tool_calls[0]["id"] == "call_1"

    @pytest.mark.asyncio
    async def test_arguments_invalido_nao_derruba_a_resposta(self):
        def handler(_req):
            return httpx.Response(
                200,
                json={
                    "id": "resp_1",
                    "status": "completed",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_1",
                            "name": "somar",
                            "arguments": "{isso nao e json",
                        }
                    ],
                },
            )

        resultado = await _modelo(handler)._agenerate([HumanMessage("x")])
        msg = resultado.generations[0].message
        assert isinstance(msg, AIMessage)
        assert msg.invalid_tool_calls
        assert msg.invalid_tool_calls[0]["name"] == "somar"


class TestStreaming:
    @pytest.mark.asyncio
    async def test_chunks_de_texto_saem_na_ordem(self):
        corpo = (
            b'data: {"type":"response.output_text.delta","delta":"Oi"}\n\n'
            b'data: {"type":"response.output_text.delta","delta":" mundo"}\n\n'
            b'data: {"type":"response.completed","response":{}}\n\n'
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
    async def test_stream_sem_nenhum_chunk_util_nao_trava(self):
        def handler(_req):
            return httpx.Response(
                200,
                content=b'data: {"type":"response.completed","response":{}}\n\n',
                headers={"content-type": "text/event-stream"},
            )

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        assert chunks == []


class TestStreamingToolCallsEUsage:
    """Caso obrigatório de regressão (achado da pesquisa da doc oficial):
    tool call fragmentada em múltiplos `response.function_call_arguments.delta`
    E o caso `.done` sem nenhum delta anterior — ambos precisam reconstruir a
    tool call completa."""

    @pytest.mark.asyncio
    async def test_tool_call_fragmentada_em_varios_deltas_sai_completa(self):
        corpo = (
            b'data: {"type":"response.output_item.added","item":'
            b'{"id":"item_1","type":"function_call","name":"file_read",'
            b'"call_id":"call_1"}}\n\n'
            b'data: {"type":"response.function_call_arguments.delta",'
            b'"item_id":"item_1","delta":"{\\"path\\":"}\n\n'
            b'data: {"type":"response.function_call_arguments.delta",'
            b'"item_id":"item_1","delta":"\\"a.py\\"}"}\n\n'
            b'data: {"type":"response.function_call_arguments.done",'
            b'"item_id":"item_1","arguments":"{\\"path\\":\\"a.py\\"}"}\n\n'
            b'data: {"type":"response.completed","response":{}}\n\n'
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
    async def test_done_sem_delta_anterior_traz_json_completo(self):
        """Edge case confirmado pela doc oficial: o servidor pode pular os
        deltas e mandar o JSON completo direto no `.done`."""
        corpo = (
            b'data: {"type":"response.output_item.added","item":'
            b'{"id":"item_1","type":"function_call","name":"somar",'
            b'"call_id":"call_1"}}\n\n'
            b'data: {"type":"response.function_call_arguments.done",'
            b'"item_id":"item_1","arguments":"{\\"a\\":1,\\"b\\":2}"}\n\n'
            b'data: {"type":"response.completed","response":{}}\n\n'
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
                "name": "somar",
                "args": {"a": 1, "b": 2},
                "id": "call_1",
                "type": "tool_call",
            }
        ]

    @pytest.mark.asyncio
    async def test_usage_do_response_completed_vira_usage_metadata(self):
        corpo = (
            b'data: {"type":"response.output_text.delta","delta":"oi"}\n\n'
            b'data: {"type":"response.completed","response":'
            b'{"usage":{"input_tokens":10,"output_tokens":3,"total_tokens":13}}}\n\n'
        )

        def handler(_req):
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        mensagens = [cast("AIMessageChunk", c.message) for c in chunks]
        com_usage = [m for m in mensagens if m.usage_metadata]

        assert len(com_usage) == 1
        usage_metadata = com_usage[0].usage_metadata
        assert usage_metadata is not None
        assert usage_metadata["input_tokens"] == 10
        assert usage_metadata["output_tokens"] == 3
        assert usage_metadata["total_tokens"] == 13
