"""``VectoraOllamaChat`` — chat nativo do Ollama, sobre ``POST /api/chat``.

Substitui `init_chat_model(model_provider="ollama")`. Três coisas que a
camada LangChain não entrega e o endpoint nativo sim: `images` por mensagem
(vision), `think` com `message.thinking` **separado** do `content`, e os
contadores `prompt_eval_count`/`eval_count`.

Diferença que quebra quem copia o OpenRouter: o streaming aqui é **NDJSON**
(`application/x-ndjson`), um objeto por linha até `done: true`. Não é SSE,
não tem prefixo `data:`.

O Hermes usa o endpoint OpenAI-compat (`/v1`) pro chat e HTTP direto só pros
metadados — aqui o chat também é nativo, porque é o `/api/chat` que expõe
`thinking` em campo próprio.
"""

from __future__ import annotations

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from backend.llm.ollama.chat import VectoraOllamaChat
from backend.llm.ollama.client import OllamaClient, OllamaResponseError


def _modelo(handler, **kwargs) -> VectoraOllamaChat:
    client = OllamaClient(
        base_url="http://127.0.0.1:11434",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return VectoraOllamaChat(model="gpt-oss:20b", client=client, **kwargs)


def _resposta_ok(content: str = "Olá") -> dict:
    return {
        "model": "gpt-oss:20b",
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 12,
        "eval_count": 4,
    }


class TestGenerate:
    @pytest.mark.asyncio
    async def test_prompt_simples_devolve_conteudo(self):
        def handler(_req):
            return httpx.Response(200, json=_resposta_ok("Olá do Ollama"))

        resultado = await _modelo(handler)._agenerate([HumanMessage("oi")])

        assert resultado.generations[0].message.content == "Olá do Ollama"

    @pytest.mark.asyncio
    async def test_contadores_viram_usage_metadata(self):
        """`prompt_eval_count`/`eval_count` são o que o Ollama devolve no
        lugar de `usage` — o caminho antigo descartava os dois."""

        def handler(_req):
            return httpx.Response(200, json=_resposta_ok())

        resultado = await _modelo(handler)._agenerate([HumanMessage("oi")])
        msg = resultado.generations[0].message

        assert isinstance(msg, AIMessage)
        assert msg.usage_metadata is not None
        assert msg.usage_metadata["input_tokens"] == 12
        assert msg.usage_metadata["output_tokens"] == 4

    @pytest.mark.asyncio
    async def test_resposta_sem_message_vira_erro_tipado(self):
        """Erro/borda: sem este corte é `KeyError: 'message'` cru, que parece
        bug do Vectora e não do servidor local."""

        def handler(_req):
            return httpx.Response(200, json={"model": "x", "done": True})

        with pytest.raises(OllamaResponseError, match="message"):
            await _modelo(handler)._agenerate([HumanMessage("oi")])

    @pytest.mark.asyncio
    async def test_modelo_nao_baixado_vira_erro_com_instrucao(self):
        """Erro/borda: aqui o "provider" é a máquina do próprio usuário — a
        mensagem tem que dizer o que fazer (`ollama pull`), não só "404"."""
        from backend.llm.ollama.client import OllamaModelNotFoundError

        def handler(_req):
            return httpx.Response(404, json={"error": 'model "x" not found'})

        with pytest.raises(OllamaModelNotFoundError, match="pull"):
            await _modelo(handler)._agenerate([HumanMessage("oi")])

    @pytest.mark.asyncio
    async def test_servidor_fora_do_ar_vira_erro_com_instrucao(self):
        from backend.llm.ollama.client import OllamaUnreachableError

        def handler(_req):
            raise httpx.ConnectError("connection refused")

        with pytest.raises(OllamaUnreachableError, match="11434"):
            await _modelo(handler)._agenerate([HumanMessage("oi")])


class TestConversaoDeMensagens:
    @pytest.mark.asyncio
    async def test_roles_traduzidos(self):
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

        assert [m["role"] for m in capturado["messages"]] == [
            "system",
            "user",
            "assistant",
            "tool",
        ]

    @pytest.mark.asyncio
    async def test_imagem_vai_em_images_base64_puro(self):
        """O Ollama recebe imagem no array `images` da mensagem, em base64
        **sem** o prefixo `data:` — não é content block multimodal da OpenAI.
        Mandar no formato da OpenAI faz o modelo não ver a imagem."""
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        msg = HumanMessage(
            content=[
                {"type": "text", "text": "o que é isto?"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,QUJD"},
                },
            ]
        )
        await _modelo(handler)._agenerate([msg])

        enviada = capturado["messages"][0]
        assert enviada["images"] == ["QUJD"], "prefixo data: não foi removido"
        assert enviada["content"] == "o que é isto?"

    @pytest.mark.asyncio
    async def test_role_desconhecido_falha_em_vez_de_virar_user(self):
        def handler(_req):
            return httpx.Response(200, json=_resposta_ok())

        estranha = HumanMessage("?")
        estranha.type = "extraterrestre"  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

        with pytest.raises(ValueError, match="extraterrestre"):
            await _modelo(handler)._agenerate([estranha])


class TestToolCalling:
    @pytest.mark.asyncio
    async def test_tool_call_volta_montada(self):
        def handler(_req):
            return httpx.Response(
                200,
                json={
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "somar",
                                    "arguments": {"a": 1, "b": 2},
                                }
                            }
                        ],
                    },
                    "done": True,
                },
            )

        ferramenta = {
            "type": "function",
            "function": {
                "name": "somar",
                "description": "soma",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        modelo = _modelo(handler).bind_tools([ferramenta])
        resultado = await modelo._agenerate([HumanMessage("some")])  # type: ignore[attr-defined]

        msg = resultado.generations[0].message
        assert isinstance(msg, AIMessage)
        assert msg.tool_calls[0]["name"] == "somar"
        # O Ollama devolve `arguments` como objeto, não string JSON — quem
        # copia o formato da OpenAI aqui faz json.loads de um dict e estoura.
        assert msg.tool_calls[0]["args"] == {"a": 1, "b": 2}

    @pytest.mark.asyncio
    async def test_arguments_como_string_tambem_e_aceito(self):
        """Erro/borda: versões antigas do Ollama mandam string. Aceitar os
        dois formatos evita quebrar em servidor desatualizado."""

        def handler(_req):
            return httpx.Response(
                200,
                json={
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {"function": {"name": "somar", "arguments": '{"a": 1}'}}
                        ],
                    },
                    "done": True,
                },
            )

        resultado = await _modelo(handler)._agenerate([HumanMessage("x")])
        msg = resultado.generations[0].message
        assert isinstance(msg, AIMessage)
        assert msg.tool_calls[0]["args"] == {"a": 1}


class TestStreamingNdjson:
    @pytest.mark.asyncio
    async def test_ndjson_vira_chunks_na_ordem(self):
        corpo = (
            b'{"message":{"content":"Oi"},"done":false}\n'
            b'{"message":{"content":" mundo"},"done":false}\n'
            b'{"message":{"content":""},"done":true}\n'
        )

        def handler(_req):
            return httpx.Response(
                200, content=corpo, headers={"content-type": "application/x-ndjson"}
            )

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]

        assert "".join(str(c.message.content) for c in chunks) == "Oi mundo"

    @pytest.mark.asyncio
    async def test_thinking_sai_separado_do_conteudo(self):
        """`think` faz o Ollama devolver `message.thinking` num campo próprio.
        Concatenar no content mistura raciocínio e resposta na tela."""
        corpo = (
            b'{"message":{"thinking":"hmm...","content":""},"done":false}\n'
            b'{"message":{"content":"resposta"},"done":false}\n'
            b'{"message":{"content":""},"done":true}\n'
        )

        def handler(_req):
            return httpx.Response(200, content=corpo)

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        texto = "".join(
            str(c.message.content) for c in chunks if isinstance(c.message.content, str)
        )

        assert "hmm..." not in texto
        assert texto == "resposta"

    @pytest.mark.asyncio
    async def test_linha_ndjson_malformada_nao_derruba_o_turno(self):
        """Erro/borda: uma linha corrompida não pode abortar a resposta —
        o que já chegou é conteúdo válido que o usuário está lendo."""
        corpo = (
            b'{"message":{"content":"antes"},"done":false}\n'
            b"{isso nao e json}\n"
            b'{"message":{"content":"depois"},"done":false}\n'
            b'{"message":{"content":""},"done":true}\n'
        )

        def handler(_req):
            return httpx.Response(200, content=corpo)

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        assert "".join(str(c.message.content) for c in chunks) == "antesdepois"

    @pytest.mark.asyncio
    async def test_nao_parseia_como_sse(self):
        """Erro/borda que motiva o teste: NDJSON tratado como SSE devolve
        zero chunk, porque nenhuma linha começa com `data:`."""
        corpo = b'{"message":{"content":"texto"},"done":true}\n'

        def handler(_req):
            return httpx.Response(200, content=corpo)

        chunks = [c async for c in _modelo(handler)._astream([HumanMessage("oi")])]
        assert chunks, "parseou como SSE e engoliu todos os chunks"


class TestThink:
    @pytest.mark.asyncio
    async def test_nivel_de_esforco_vai_no_campo_think(self):
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        await _modelo(handler, think="high")._agenerate([HumanMessage("oi")])

        assert capturado["think"] == "high"

    @pytest.mark.asyncio
    async def test_sem_think_o_campo_nao_e_enviado(self):
        """Erro/borda: mandar `think: false` num modelo sem a capacidade é
        diferente de não mandar nada — o campo tem que sumir do payload."""
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        await _modelo(handler)._agenerate([HumanMessage("oi")])

        assert "think" not in capturado


class TestNumCtxNumPredict:
    """`options.num_ctx`/`num_predict` faltavam no payload — o Ollama caía no
    default do servidor (variável por VRAM/Modelfile), sem controle nenhum
    pelo Vectora sobre a janela de contexto disponível pro uso agêntico."""

    @pytest.mark.asyncio
    async def test_num_ctx_e_num_predict_sempre_no_payload(self, monkeypatch):
        from backend.settings import settings as _s

        monkeypatch.setattr(_s, "ollama_num_ctx", 16384, raising=False)
        monkeypatch.setattr(_s, "ollama_num_predict", 2048, raising=False)

        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        await _modelo(handler)._agenerate([HumanMessage("oi")])

        assert capturado["options"]["num_ctx"] == 16384
        assert capturado["options"]["num_predict"] == 2048

    @pytest.mark.asyncio
    async def test_temperature_convive_com_num_ctx_no_mesmo_options(self):
        """Erro/borda: `temperature` não sobrescreve `options` — os dois
        entram no mesmo dict, não em chamadas separadas de `_payload`."""
        capturado: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            import json as _json

            capturado.update(_json.loads(req.content))
            return httpx.Response(200, json=_resposta_ok())

        await _modelo(handler, temperature=0.3)._agenerate([HumanMessage("oi")])

        assert capturado["options"]["temperature"] == 0.3
        assert "num_ctx" in capturado["options"]
        assert "num_predict" in capturado["options"]
