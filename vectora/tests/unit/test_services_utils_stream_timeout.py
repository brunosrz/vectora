"""``backend/services/utils.py::_build_concrete_model`` — nenhum provider pode
impor timeout de silêncio entre chunks. Modelos de raciocínio (reasoning)
ficam minutos "pensando" sem emitir nenhum token — isso é comportamento
normal, não falha de conexão. ``ChatOpenAI`` (usado por "openai" e
"openrouter") tem um `stream_chunk_timeout` de 120s ligado por padrão
(langchain_openai) — precisa ser desligado explicitamente aqui.
"""

from __future__ import annotations

import pytest

from backend.services.env import GetEnvError
from backend.services.utils import _build_concrete_model


class _FakeChatOpenAI:
    """Captura os kwargs recebidos, sem chamar a API real."""

    last_kwargs: dict | None = None

    def __init__(self, **kwargs):
        _FakeChatOpenAI.last_kwargs = kwargs


@pytest.fixture(autouse=True)
def _fake_chat_openai(monkeypatch):
    _FakeChatOpenAI.last_kwargs = None
    monkeypatch.setattr("langchain_openai.ChatOpenAI", _FakeChatOpenAI)


def test_openai_desliga_stream_chunk_timeout(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    _build_concrete_model("openai", "gpt-4o", 0.7)

    assert _FakeChatOpenAI.last_kwargs is not None
    assert _FakeChatOpenAI.last_kwargs["stream_chunk_timeout"] is None


def test_openrouter_desliga_stream_chunk_timeout(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    _build_concrete_model("openrouter", "openrouter/auto", 0.7)

    assert _FakeChatOpenAI.last_kwargs is not None
    assert _FakeChatOpenAI.last_kwargs["stream_chunk_timeout"] is None


def test_openrouter_sem_api_key_levanta_erro_claro(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(GetEnvError, match="OPENROUTER_API_KEY"):
        _build_concrete_model("openrouter", "openrouter/auto", 0.7)
