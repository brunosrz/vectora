"""Título da sessão atribuído pela IA (``_ai_title``).

Cobre o caminho feliz (LLM resume em poucas palavras, limpo) e o fallback
defensivo (falha do LLM → primeiras palavras da mensagem do usuário). Nunca
propaga exceção.
"""

from __future__ import annotations

import pytest

from backend.api.handlers import threads as threads_mod


class _FakeMsg:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeLLM:
    def __init__(self, content: str) -> None:
        self._content = content

    async def ainvoke(self, _messages):
        return _FakeMsg(self._content)


@pytest.mark.asyncio
async def test_ai_title_happy(monkeypatch):
    monkeypatch.setattr(
        "backend.services.utils.load_llm",
        lambda: _FakeLLM("Plano de migração do banco"),
    )
    title = await threads_mod._ai_title("como migro o banco?", "vamos planejar")
    assert title == "Plano de migração do banco"


@pytest.mark.asyncio
async def test_ai_title_trims_to_six_words_and_strips(monkeypatch):
    monkeypatch.setattr(
        "backend.services.utils.load_llm",
        lambda: _FakeLLM('"Uma sete oito nove dez onze doze".'),
    )
    title = await threads_mod._ai_title("oi", "olá")
    # Sem aspas, sem ponto final, no máximo 6 palavras.
    assert title == "Uma sete oito nove dez onze"


@pytest.mark.asyncio
async def test_ai_title_fallback_on_llm_failure(monkeypatch):
    def _boom():
        raise RuntimeError("provider down")

    monkeypatch.setattr("backend.services.utils.load_llm", _boom)
    title = await threads_mod._ai_title("preciso de ajuda com o deploy agora", "ok")
    assert title == "preciso de ajuda com o deploy"


@pytest.mark.asyncio
async def test_ai_title_fallback_empty_user(monkeypatch):
    def _boom():
        raise RuntimeError("provider down")

    monkeypatch.setattr("backend.services.utils.load_llm", _boom)
    title = await threads_mod._ai_title("", "")
    assert title == "Nova conversa"
