"""``FallbackChatClient`` — orquestrador de fallback entre os 5 chat clients
nativos. Espelha o comportamento do antigo
``FallbackChatModel``: troca de provider em quota/timeout/incompatibilidade,
nunca depois de já ter streamado chunks, e erro não recuperável no primário
propaga sem tentar fallback.
"""

from __future__ import annotations

import pytest

from backend.llm.fallback_chat_client import FallbackChatClient
from backend.llm.provider_fallback import QuotaExhaustedError
from backend.vtypes.message import (
    ContentBlock,
    MessageRole,
    VMessage,
    VMessageChunk,
    text_message,
)


class _FakeChatClient:
    """Client controlável por teste: `agenerate`/`astream` seguem um script
    de resultados/exceções por chamada."""

    def __init__(self, comportamento):
        self._comportamento = comportamento

    async def agenerate(
        self, messages, *, tools=None, temperature=None, max_tokens=None
    ):
        resultado = self._comportamento
        if isinstance(resultado, BaseException):
            raise resultado
        return resultado

    async def astream(self, messages, *, tools=None, temperature=None, max_tokens=None):
        for item in self._comportamento:
            if isinstance(item, BaseException):
                raise item
            yield item


def _resposta_ok(texto: str = "ok") -> VMessage:
    return VMessage(
        role=MessageRole.ASSISTANT,
        content=[ContentBlock(kind="text", text=texto)],
        finish_reason="stop",
    )


def _make_client(
    monkeypatch, *, fallback_chain, clients_por_modelo, on_model_switch=None
):
    monkeypatch.setattr(
        "backend.llm.fallback_chat_client.get_fallback_chain",
        lambda _mid: fallback_chain,
    )
    monkeypatch.setattr(
        "backend.llm.fallback_chat_client.load_chat_client",
        lambda mid: clients_por_modelo[mid],
    )
    return FallbackChatClient("openai:gpt-4o", on_model_switch=on_model_switch)


class TestAgenerate:
    async def test_usa_o_primario_quando_nao_ha_erro(self, monkeypatch):
        cliente = _make_client(
            monkeypatch,
            fallback_chain=[],
            clients_por_modelo={
                "openai:gpt-4o": _FakeChatClient(_resposta_ok("do primário"))
            },
        )

        resultado = await cliente.agenerate([text_message(MessageRole.USER, "oi")])

        assert resultado.text() == "do primário"

    async def test_erro_de_quota_troca_para_o_proximo_da_cadeia(self, monkeypatch):
        trocas: list[tuple[str, str]] = []

        async def registrar(de, para):
            trocas.append((de, para))

        cliente = _make_client(
            monkeypatch,
            fallback_chain=["anthropic:claude-sonnet"],
            clients_por_modelo={
                "openai:gpt-4o": _FakeChatClient(
                    QuotaExhaustedError("429", model_id="openai:gpt-4o")
                ),
                "anthropic:claude-sonnet": _FakeChatClient(_resposta_ok("do fallback")),
            },
            on_model_switch=registrar,
        )

        resultado = await cliente.agenerate([text_message(MessageRole.USER, "oi")])

        assert resultado.text() == "do fallback"
        assert trocas == [("openai:gpt-4o", "anthropic:claude-sonnet")]

    async def test_erro_nao_recuperavel_no_primario_propaga_sem_fallback(
        self, monkeypatch
    ):
        cliente = _make_client(
            monkeypatch,
            fallback_chain=["anthropic:claude-sonnet"],
            clients_por_modelo={
                "openai:gpt-4o": _FakeChatClient(ValueError("payload inválido")),
                "anthropic:claude-sonnet": _FakeChatClient(
                    _resposta_ok("nunca chamado")
                ),
            },
        )

        with pytest.raises(ValueError, match="payload inválido"):
            await cliente.agenerate([text_message(MessageRole.USER, "oi")])

    async def test_todos_os_candidatos_esgotados_vira_quota_exhausted(
        self, monkeypatch
    ):
        cliente = _make_client(
            monkeypatch,
            fallback_chain=["anthropic:claude-sonnet"],
            clients_por_modelo={
                "openai:gpt-4o": _FakeChatClient(
                    QuotaExhaustedError("429", model_id="openai:gpt-4o")
                ),
                "anthropic:claude-sonnet": _FakeChatClient(
                    QuotaExhaustedError("429", model_id="anthropic:claude-sonnet")
                ),
            },
        )

        with pytest.raises(QuotaExhaustedError, match="anthropic:claude-sonnet"):
            await cliente.agenerate([text_message(MessageRole.USER, "oi")])

    async def test_sem_candidato_com_visao_para_mensagem_com_imagem_lanca_quota_exhausted(
        self, monkeypatch
    ):
        monkeypatch.setattr("backend.settings.VISION_CAPABLE_PROVIDERS", set())
        cliente = _make_client(monkeypatch, fallback_chain=[], clients_por_modelo={})
        mensagem = VMessage(
            role=MessageRole.USER,
            content=[
                ContentBlock(kind="image_url", image_url="data:image/png;base64,x")
            ],
        )

        with pytest.raises(QuotaExhaustedError, match=r"[Nn]enhum provider"):
            await cliente.agenerate([mensagem])


class TestAstream:
    async def test_chunks_do_primario_saem_direto(self, monkeypatch):
        cliente = _make_client(
            monkeypatch,
            fallback_chain=[],
            clients_por_modelo={
                "openai:gpt-4o": _FakeChatClient(
                    [VMessageChunk(delta_text="a"), VMessageChunk(delta_text="b")]
                )
            },
        )

        chunks = [
            c async for c in cliente.astream([text_message(MessageRole.USER, "oi")])
        ]

        assert "".join(c.delta_text for c in chunks) == "ab"

    async def test_erro_de_quota_antes_do_primeiro_chunk_troca_de_provider(
        self, monkeypatch
    ):
        cliente = _make_client(
            monkeypatch,
            fallback_chain=["anthropic:claude-sonnet"],
            clients_por_modelo={
                "openai:gpt-4o": _FakeChatClient(
                    [QuotaExhaustedError("429", model_id="openai:gpt-4o")]
                ),
                "anthropic:claude-sonnet": _FakeChatClient(
                    [VMessageChunk(delta_text="do fallback")]
                ),
            },
        )

        chunks = [
            c async for c in cliente.astream([text_message(MessageRole.USER, "oi")])
        ]

        assert "".join(c.delta_text for c in chunks) == "do fallback"

    async def test_erro_depois_de_ja_ter_streamado_chunk_propaga_sem_trocar(
        self, monkeypatch
    ):
        cliente = _make_client(
            monkeypatch,
            fallback_chain=["anthropic:claude-sonnet"],
            clients_por_modelo={
                "openai:gpt-4o": _FakeChatClient(
                    [
                        VMessageChunk(delta_text="parcial"),
                        QuotaExhaustedError("429", model_id="openai:gpt-4o"),
                    ]
                ),
                "anthropic:claude-sonnet": _FakeChatClient(
                    [VMessageChunk(delta_text="nunca chamado")]
                ),
            },
        )

        recebidos: list[VMessageChunk] = []

        async def _consumir() -> None:
            async for chunk in cliente.astream([text_message(MessageRole.USER, "oi")]):
                # Precisa reter o parcial já recebido antes da exceção — uma
                # list comprehension descartaria tudo se abortada no meio.
                recebidos.append(chunk)  # noqa: PERF401

        with pytest.raises(QuotaExhaustedError):
            await _consumir()

        assert [c.delta_text for c in recebidos] == ["parcial"]
