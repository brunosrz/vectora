"""E2E do pipeline de streaming: FallbackChatModel → astream_events → adapt_stream.

Regressão do bug crítico "cada token duplicado, cada ocorrência em linha
própria": os testes unitários anteriores chamavam ``fcm._astream`` direto com
fakes duck-typed e ficavam verdes mesmo com o produto quebrado, porque nunca
exercitavam a instrumentação real de callbacks do ``astream_events`` (que é
onde o run aninhado do provider interno duplicava cada ``on_chat_model_stream``).

Aqui o caminho é o de produção: um ``BaseChatModel`` REAL (GenericFakeChatModel)
por baixo do ``FallbackChatModel``, invocado via ``ainvoke`` dentro de um
runnable (como o nó `model` do LangGraph faz), com os eventos do
``astream_events`` v2 alimentando o ``adapt_stream`` — exatamente o SSE que o
frontend consome.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from itertools import pairwise
from typing import Any
from unittest.mock import patch

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_core.runnables import RunnableLambda

from backend.api.adapters import adapt_stream
from backend.llm import provider_fallback as pf
from backend.llm.fallback_chat_model import FallbackChatModel


def _parse(sse: str) -> dict:
    assert sse.startswith("data: ")
    return json.loads(sse[len("data: ") :].strip())


def _fake_model(text: str) -> GenericFakeChatModel:
    """Modelo real (BaseChatModel) que streama `text` token a token."""
    return GenericFakeChatModel(messages=iter([AIMessage(content=text)]))


class _RaisingChatModel(BaseChatModel):
    """BaseChatModel real que levanta um erro ANTES do primeiro chunk.

    Usado para exercitar o fallback de quota/transiente no pipeline real (o
    FallbackChatModel só troca de provider se a exceção vier antes do 1º token).
    """

    model_config = {"arbitrary_types_allowed": True}
    error: Exception = RuntimeError("boom")

    @property
    def _llm_type(self) -> str:
        return "raising"

    async def _astream(
        self, messages, stop=None, run_manager=None, **kwargs
    ) -> AsyncIterator[ChatGenerationChunk]:
        raise self.error
        yield  # pragma: no cover — torna a função um gerador

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        raise self.error

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        raise self.error


async def _run_pipeline(
    inner: Any,
    messages: list[BaseMessage] | None = None,
    load_llm: Any = None,
    primary_model_id: str = "primary:m",
    fallback_chain: list[str] | None = None,
) -> list[dict]:
    """Roda o pipeline de produção completo e devolve os eventos SSE.

    ``inner`` é o BaseChatModel real por baixo do FallbackChatModel;
    ``load_llm`` opcional permite mapear model_id → modelo (fallback de quota);
    ``fallback_chain`` popula a cadeia de fallback (default vazia).
    """
    fcm = FallbackChatModel(primary_model_id=primary_model_id)
    msgs = messages or [HumanMessage(content="hi")]

    async def _node(_input: object) -> object:
        # Igual ao nó `model` do agente: ainvoke (que internamente streama
        # quando há handler de streaming ativo — o do astream_events).
        return await fcm.ainvoke(msgs)

    chain = RunnableLambda(_node)
    with (
        patch("backend.services.utils.load_llm", load_llm or (lambda _mid: inner)),
        patch.object(pf, "get_fallback_chain", return_value=fallback_chain or []),
    ):
        events = chain.astream_events("go", version="v2")
        return [_parse(s) async for s in adapt_stream(events, "tid")]


async def _tokens_via_pipeline(text: str) -> list[dict]:
    return await _run_pipeline(_fake_model(text))


def _token_contents(out: list[dict]) -> list[str]:
    return [e["content"] for e in out if e["type"] == "token"]


class TestStreamDedupE2E:
    @pytest.mark.asyncio
    async def test_cada_token_aparece_exatamente_uma_vez(self):
        out = await _tokens_via_pipeline("Olá tudo bem")
        tokens = [e["content"] for e in out if e["type"] == "token"]
        assert "".join(tokens) == "Olá tudo bem"
        # A regressão duplicava cada token (um do wrapper, um do provider
        # interno aninhado) — aqui garantimos unicidade token a token.
        assert tokens == ["Olá", " ", "tudo", " ", "bem"], (
            f"tokens duplicados ou fora de ordem: {tokens}"
        )

    @pytest.mark.asyncio
    async def test_nenhum_message_break_espurio(self):
        # A duplicação vinha acompanhada de um message_break entre cada par
        # (o nó emissor alternava wrapper ↔ provider), que o frontend
        # renderizava como quebra de linha a cada token.
        out = await _tokens_via_pipeline("Olá tudo bem")
        assert not any(e["type"] == "message_break" for e in out)

    @pytest.mark.asyncio
    async def test_resposta_de_um_unico_token(self):
        out = await _tokens_via_pipeline("Oi")
        tokens = [e["content"] for e in out if e["type"] == "token"]
        assert tokens == ["Oi"]

    @pytest.mark.asyncio
    async def test_conteudo_final_integro_com_pontuacao(self):
        text = "Olá! Estou bem, obrigado. E você?"
        out = await _tokens_via_pipeline(text)
        joined = "".join(e["content"] for e in out if e["type"] == "token")
        assert joined == text

    @pytest.mark.asyncio
    async def test_texto_longo_sem_duplicacao(self):
        # >50 tokens — a duplicação escalava com o tamanho; texto longo é o
        # cenário onde o bug era mais gritante.
        words = " ".join(f"palavra{i}" for i in range(60))
        out = await _tokens_via_pipeline(words)
        joined = "".join(_token_contents(out))
        assert joined == words
        assert not any(e["type"] == "message_break" for e in out)
        # Nenhum token repetido consecutivamente (assinatura da duplicação).
        toks = _token_contents(out)
        assert all(a != b for a, b in pairwise(toks) if a.strip())

    @pytest.mark.asyncio
    async def test_resposta_vazia_nao_emite_token(self):
        out = await _tokens_via_pipeline("")
        assert _token_contents(out) == []
        assert out[0]["type"] == "thread"
        assert out[-1]["type"] == "done"

    @pytest.mark.asyncio
    async def test_unicode_emoji_acentos_intactos(self):
        text = "Café ☕ com açúcar 🍬 e pão 🥖 — tudo ótimo!"
        out = await _tokens_via_pipeline(text)
        assert "".join(_token_contents(out)) == text
        assert not any(e["type"] == "message_break" for e in out)

    @pytest.mark.asyncio
    async def test_quebras_de_linha_reais_preservadas(self):
        # Quebras de linha DENTRO da resposta do modelo são conteúdo legítimo
        # e não podem virar bolhas separadas nem sumir.
        text = "linha um\nlinha dois\n\nparágrafo novo"
        out = await _tokens_via_pipeline(text)
        assert "".join(_token_contents(out)) == text

    @pytest.mark.asyncio
    async def test_markdown_code_fence_intacto(self):
        text = "Veja:\n```python\nprint('oi')\n```\nfim"
        out = await _tokens_via_pipeline(text)
        assert "".join(_token_contents(out)) == text
        assert not any(e["type"] == "message_break" for e in out)

    @pytest.mark.asyncio
    async def test_fallback_de_quota_streama_sem_duplicar(self):
        # 1º provider estoura quota ANTES do 1º token → 2º provider streama.
        # O dedup precisa continuar valendo no provider final, e o
        # model_switched sai exatamente uma vez.
        pf.drain_switches()
        primary = _RaisingChatModel(error=Exception("429 RESOURCE_EXHAUSTED quota"))
        fallback = _fake_model("resposta do fallback")
        mapping = {"primary:m": primary, "fallback:m": fallback}
        out = await _run_pipeline(
            primary,
            load_llm=lambda mid: mapping[mid],
            fallback_chain=["fallback:m"],
        )
        joined = "".join(_token_contents(out))
        assert joined == "resposta do fallback"
        assert not any(e["type"] == "message_break" for e in out)
        switches = [e for e in out if e["type"] == "model_switched"]
        assert len(switches) == 1

    @pytest.mark.asyncio
    async def test_fallback_transiente_streama_sem_duplicar(self):
        primary = _RaisingChatModel(error=Exception("ReadTimeout connecting"))
        fallback = _fake_model("ok apos timeout")
        mapping = {"primary:m": primary, "fallback:m": fallback}
        out = await _run_pipeline(
            primary,
            load_llm=lambda mid: mapping[mid],
            fallback_chain=["fallback:m"],
        )
        assert "".join(_token_contents(out)) == "ok apos timeout"
        assert not any(e["type"] == "message_break" for e in out)

    @pytest.mark.asyncio
    async def test_replay_com_reasoning_no_historico_streama_limpo(self):
        # Integração end-to-end do _strip_reasoning_blocks: histórico com um
        # AIMessage do Command A+ (content = lista reasoning+text) não pode
        # quebrar o stream do turno seguinte (era o crash do langchain_cohere).
        history: list[BaseMessage] = [
            HumanMessage(content="Olá"),
            AIMessage(
                content=[
                    {"type": "reasoning", "reasoning": "cumprimento", "index": 0},
                    {"type": "text", "text": "Olá! Como vai?", "index": 1},
                ]
            ),
            HumanMessage(content="Tudo bem, e você?"),
        ]
        out = await _run_pipeline(_fake_model("Também estou bem!"), messages=history)
        assert "".join(_token_contents(out)) == "Também estou bem!"
        assert not any(e["type"] == "message_break" for e in out)
        assert not any(e["type"] == "error" for e in out)
