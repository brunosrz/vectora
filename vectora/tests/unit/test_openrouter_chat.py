"""``VectoraOpenRouterChat`` — chat nativo do OpenRouter.

Expõe os campos específicos do OpenRouter que uma integração OpenAI-
compatível genérica não tem onde encaixar: `usage.cost`, roteamento por
`provider` e os blocos de `reasoning`, além de streaming e tool calling
(caminho crítico do agente).
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

from backend.llm.openrouter.chat import VectoraOpenRouterChat
from backend.llm.openrouter.client import OpenRouterClient, OpenRouterResponseError


def _modelo(handler, **kwargs) -> VectoraOpenRouterChat:
    client = OpenRouterClient(
        api_key="sk-or-test",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return VectoraOpenRouterChat(model="openai/gpt-4o", client=client, **kwargs)


def _resposta_ok(content: str = "Olá", **extra) -> dict:
    return {
        "id": "gen-1",
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 3, "cost": 0.000123},
        **extra,
    }


class TestGenerate:
    @pytest.mark.asyncio
    async def test_prompt_simples_devolve_conteudo(self):
        def handler(_req):
            return httpx.Response(200, json=_resposta_ok("Olá do OpenRouter"))

        resultado = await _modelo(handler)._agenerate([HumanMessage("oi")])

        assert resultado.generations[0].message.content == "Olá do OpenRouter"

    @pytest.mark.asyncio
    async def test_usage_metadata_traz_o_custo(self):
        """`usage.cost` (campo específico do OpenRouter) é propagado pro
        `response_metadata` — é o que alimenta o medidor de gasto por turno."""

        def handler(_req):
            return httpx.Response(200, json=_resposta_ok())

        resultado = await _modelo(handler)._agenerate([HumanMessage("oi")])
        msg = resultado.generations[0].message

        assert isinstance(msg, AIMessage)
        assert msg.usage_metadata is not None
        assert msg.usage_metadata["input_tokens"] == 10
        assert msg.usage_metadata["output_tokens"] == 3
        assert msg.response_metadata["cost"] == pytest.approx(0.000123)

    @pytest.mark.asyncio
    async def test_resposta_sem_choices_vira_erro_tipado(self):
        """Erro/borda: sem este corte é `KeyError: 'choices'` cru — que não
        diz nada e ainda parece bug do Vectora, não do provider."""

        def handler(_req):
            return httpx.Response(200, json={"id": "gen-1"})

        with pytest.raises(OpenRouterResponseError, match="choices"):
            await _modelo(handler)._agenerate([HumanMessage("oi")])

    @pytest.mark.asyncio
    async def test_choices_vazio_tambem_vira_erro_tipado(self):
        def handler(_req):
            return httpx.Response(200, json={"id": "gen-1", "choices": []})

        with pytest.raises(OpenRouterResponseError):
            await _modelo(handler)._agenerate([HumanMessage("oi")])


class TestConversaoDeMensagens:
    @pytest.mark.asyncio
    async def test_roles_traduzidos_e_tool_message_com_tool_call_id(self):
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

        roles = [m["role"] for m in capturado["messages"]]
        assert roles == ["system", "user", "assistant", "tool"]
        # `tool_call_id` é obrigatório no formato OpenAI-compatível: sem ele o
        # provider recusa a mensagem de tool com 400.
        assert capturado["messages"][3]["tool_call_id"] == "call_1"

    @pytest.mark.asyncio
    async def test_mensagem_de_role_desconhecido_falha_em_vez_de_virar_user(self):
        """Erro/borda: mapear silenciosamente pra `user` faz o modelo receber
        contexto errado sem ninguém perceber — falha alto é melhor."""

        def handler(_req):
            return httpx.Response(200, json=_resposta_ok())

        estranha = HumanMessage("?")
        estranha.type = "extraterrestre"  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

        with pytest.raises(ValueError, match="extraterrestre"):
            await _modelo(handler)._agenerate([estranha])


class TestToolCalling:
    @pytest.mark.asyncio
    async def test_tools_vao_no_payload_e_tool_call_volta_montada(self):
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(
                200,
                json={
                    "id": "gen-1",
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "somar",
                                            "arguments": '{"a": 1, "b": 2}',
                                        },
                                    }
                                ],
                            }
                        }
                    ],
                },
            )

        ferramenta = {
            "type": "function",
            "function": {
                "name": "somar",
                "description": "soma dois números",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        modelo = _modelo(handler).bind_tools([ferramenta])
        resultado = await modelo._agenerate([HumanMessage("some 1 e 2")])  # type: ignore[attr-defined]

        assert capturado["tools"][0]["function"]["name"] == "somar"
        mensagem = resultado.generations[0].message
        assert isinstance(mensagem, AIMessage)
        chamadas = mensagem.tool_calls
        assert chamadas[0]["name"] == "somar"
        assert chamadas[0]["args"] == {"a": 1, "b": 2}
        assert chamadas[0]["id"] == "call_1"

    @pytest.mark.asyncio
    async def test_arguments_invalido_nao_derruba_a_resposta(self):
        """Erro/borda: modelo devolvendo JSON quebrado em `arguments` é comum.
        A tool call entra com args vazio e o grafo segue — abortar o turno
        perderia todo o texto já gerado."""

        def handler(_req):
            return httpx.Response(
                200,
                json={
                    "id": "gen-1",
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "somar",
                                            "arguments": "{isso nao e json",
                                        },
                                    }
                                ],
                            }
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
            b'data: {"choices":[{"delta":{"content":"Oi"}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":" mundo"}}]}\n\n'
            b"data: [DONE]\n\n"
        )

        def handler(_req):
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]

        assert "".join(str(c.message.content) for c in chunks) == "Oi mundo"

    @pytest.mark.asyncio
    async def test_reasoning_sai_separado_do_conteudo(self):
        """O OpenRouter manda `reasoning` num campo próprio do delta. Concatenar
        no `content` mistura o raciocínio com a resposta na tela."""
        corpo = (
            b'data: {"choices":[{"delta":{"reasoning":"pensando..."}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":"resposta"}}]}\n\n'
            b"data: [DONE]\n\n"
        )

        def handler(_req):
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        texto = "".join(
            str(c.message.content) for c in chunks if isinstance(c.message.content, str)
        )

        assert "pensando..." not in texto
        assert "resposta" in texto

    @pytest.mark.asyncio
    async def test_stream_sem_nenhum_chunk_util_nao_trava(self):
        """Erro/borda: só o [DONE] (modelo devolveu nada) termina o gerador em
        vez de pendurar o turno esperando token que não vem."""

        def handler(_req):
            return httpx.Response(
                200,
                content=b"data: [DONE]\n\n",
                headers={"content-type": "text/event-stream"},
            )

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        assert chunks == []


class TestStreamingToolCallsEUsage:
    """`_astream` monta tool calls a partir dos fragmentos de `delta.tool_calls`
    entre chunks e propaga `usage` (incluindo `cost`) do último evento SSE."""

    @pytest.mark.asyncio
    async def test_tool_call_fragmentada_em_varios_chunks_sai_completa(self):
        corpo = (
            b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1",'
            b'"function":{"name":"file_read","arguments":""}}]}}]}\n\n'
            b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,'
            b'"function":{"arguments":"{\\"path\\":"}}]}}]}\n\n'
            b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,'
            b'"function":{"arguments":"\\"a.py\\"}"}}]}}]}\n\n'
            b"data: [DONE]\n\n"
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
    async def test_usage_do_ultimo_evento_sse_vira_usage_metadata_e_cost(self):
        corpo = (
            b'data: {"choices":[{"delta":{"content":"oi"}}]}\n\n'
            b'data: {"choices":[],"usage":{"prompt_tokens":10,'
            b'"completion_tokens":3,"cost":0.0004}}\n\n'
            b"data: [DONE]\n\n"
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
        assert com_usage[0].response_metadata["cost"] == 0.0004


class TestProviderRouting:
    @pytest.mark.asyncio
    async def test_bloco_provider_vai_no_payload(self):
        """O bloco `provider` (roteamento por ordem de provedores) vai no
        payload quando configurado no construtor."""
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        modelo = _modelo(handler, provider={"order": ["Anthropic", "OpenAI"]})
        await modelo._agenerate([HumanMessage("oi")])

        assert capturado["provider"] == {"order": ["Anthropic", "OpenAI"]}

    @pytest.mark.asyncio
    async def test_sem_provider_configurado_o_campo_nao_e_enviado(self):
        """Erro/borda: mandar `provider: null` restringe o roteamento em vez de
        deixar o OpenRouter escolher — o campo tem que sumir do payload."""
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        await _modelo(handler)._agenerate([HumanMessage("oi")])

        assert "provider" not in capturado
