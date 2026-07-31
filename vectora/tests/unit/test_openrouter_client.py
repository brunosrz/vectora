"""``backend/llm/openrouter/client.py`` — cliente HTTP nativo do OpenRouter.

Fundação das 7 capacidades (chat, embeddings, rerank, imagem, TTS, STT,
vídeo). O tratamento de erro mora aqui uma vez só: cada capacidade herda o
mapeamento status → exceção tipada em vez de repetir.
"""

from __future__ import annotations

import httpx
import pytest

from backend.llm.openrouter.client import (
    OpenRouterAuthError,
    OpenRouterClient,
    OpenRouterCreditError,
    OpenRouterRateLimitError,
    OpenRouterResponseError,
    OpenRouterServerError,
)


def _client(handler) -> OpenRouterClient:
    """Client apontando pra um transporte mockado — nada sai pra rede."""
    transport = httpx.MockTransport(handler)
    return OpenRouterClient(
        api_key="sk-or-test",
        http_client=httpx.AsyncClient(transport=transport),
    )


class TestAuthEHeaders:
    @pytest.mark.asyncio
    async def test_manda_bearer_e_headers_de_atribuicao(self):
        capturado: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            capturado.update(request.headers)
            return httpx.Response(200, json={"ok": True})

        async with _client(handler) as c:
            await c.post_json("/chat/completions", {"model": "x"})

        assert capturado["authorization"] == "Bearer sk-or-test"
        # OpenRouter usa estes dois pra atribuir o tráfego ao app na listagem
        # pública — sem eles o uso aparece como anônimo.
        assert capturado["http-referer"]
        assert capturado["x-title"]

    def test_sem_api_key_levanta_antes_de_qualquer_request(self):
        """Erro/borda: key vazia tem que falhar na construção. Deixar passar
        rende um 401 confuso lá na frente, longe da causa."""
        with pytest.raises(OpenRouterAuthError, match="OPENROUTER_API_KEY"):
            OpenRouterClient(api_key="")


class TestMapeamentoDeErro:
    @pytest.mark.parametrize(
        ("status", "excecao"),
        [
            (401, OpenRouterAuthError),
            (402, OpenRouterCreditError),
            (429, OpenRouterRateLimitError),
            (500, OpenRouterServerError),
            (503, OpenRouterServerError),
        ],
    )
    @pytest.mark.asyncio
    async def test_status_vira_excecao_tipada(self, status, excecao):
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(status, json={"error": {"message": "falhou"}})

        async with _client(handler) as c:
            with pytest.raises(excecao):
                await c.post_json("/chat/completions", {"model": "x"})

    @pytest.mark.asyncio
    async def test_corpo_nao_json_vira_erro_tipado_e_nao_json_decode_error(self):
        """Erro/borda: proxy/CDN no meio devolve HTML numa falha. Sem este
        tratamento o `.json()` estoura com JSONDecodeError cru, que não diz
        nada ao usuário sobre o que aconteceu."""

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html>gateway timeout</html>")

        async with _client(handler) as c:
            with pytest.raises(OpenRouterResponseError):
                await c.post_json("/chat/completions", {"model": "x"})

    @pytest.mark.asyncio
    async def test_mensagem_do_erro_do_provider_chega_na_excecao(self):
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                402, json={"error": {"message": "Insufficient credits"}}
            )

        async with _client(handler) as c:
            with pytest.raises(OpenRouterCreditError, match="Insufficient credits"):
                await c.post_json("/chat/completions", {"model": "x"})


class TestStreamNdjsonSse:
    @pytest.mark.asyncio
    async def test_stream_sse_entrega_um_evento_por_data(self):
        corpo = (
            b'data: {"choices":[{"delta":{"content":"Oi"}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":" mundo"}}]}\n\n'
            b"data: [DONE]\n\n"
        )

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        async with _client(handler) as c:
            eventos = [e async for e in c.stream_sse("/chat/completions", {})]

        assert [e["choices"][0]["delta"]["content"] for e in eventos] == [
            "Oi",
            " mundo",
        ]

    @pytest.mark.asyncio
    async def test_linha_malformada_no_meio_do_stream_nao_derruba_o_turno(self):
        """Erro/borda: um chunk corrompido não pode abortar a resposta inteira
        — o que já chegou é conteúdo válido que o usuário está lendo."""
        corpo = (
            b'data: {"choices":[{"delta":{"content":"antes"}}]}\n\n'
            b"data: {isso nao e json}\n\n"
            b'data: {"choices":[{"delta":{"content":"depois"}}]}\n\n'
            b"data: [DONE]\n\n"
        )

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, content=corpo, headers={"content-type": "text/event-stream"}
            )

        async with _client(handler) as c:
            eventos = [e async for e in c.stream_sse("/chat/completions", {})]

        assert [e["choices"][0]["delta"]["content"] for e in eventos] == [
            "antes",
            "depois",
        ]
