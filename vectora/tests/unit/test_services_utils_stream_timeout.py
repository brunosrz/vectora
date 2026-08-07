"""``backend/services/utils.py::_build_concrete_model`` — nenhum provider pode
impor timeout de silêncio entre chunks. Modelos de raciocínio (reasoning)
ficam minutos "pensando" sem emitir nenhum token — isso é comportamento
normal, não falha de conexão.

"openai" e "openrouter" saíram do ``ChatOpenAI`` e usam clients nativos, que
controlam o timeout HTTP diretamente — sem o `stream_chunk_timeout` de 120s
que o `langchain_openai` aplicava por padrão. Os testes travam a classe usada
em vez de inspecionar kwargs que não existem mais nesse caminho.
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


def test_openai_usa_cliente_nativo_e_nao_chat_openai(monkeypatch):
    """O caminho antigo (`ChatOpenAI`) tinha `stream_chunk_timeout=120s` por
    padrão — o client nativo (Responses API) controla o timeout HTTP
    diretamente, sem esse problema."""
    from backend.llm.openai.chat import VectoraOpenAIChat

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    modelo = _build_concrete_model("openai", "gpt-5", 0.7)

    assert isinstance(modelo, VectoraOpenAIChat)
    # Erro/borda: se voltar a cair no ChatOpenAI, o fake teria capturado
    # kwargs — nenhuma chamada é a prova de que o caminho mudou.
    assert _FakeChatOpenAI.last_kwargs is None


def test_openrouter_usa_cliente_nativo_e_nao_chat_openai(monkeypatch):
    """O caminho antigo (`ChatOpenAI` com base_url trocado) descartava
    `usage.cost`, o bloco `provider` e o `reasoning` do delta."""
    from backend.llm.openrouter.chat import VectoraOpenRouterChat

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    modelo = _build_concrete_model("openrouter", "openrouter/auto", 0.7)

    assert isinstance(modelo, VectoraOpenRouterChat)
    # Erro/borda: se voltar a cair no ChatOpenAI, o fake teria capturado
    # kwargs — nenhuma chamada é a prova de que o caminho mudou.
    assert _FakeChatOpenAI.last_kwargs is None


def test_openrouter_sem_api_key_levanta_erro_claro(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(GetEnvError, match="OPENROUTER_API_KEY"):
        _build_concrete_model("openrouter", "openrouter/auto", 0.7)


def test_nine_router_usa_chat_openai_comum(monkeypatch):
    """9Router é integração leve, não client nativo: já fala o protocolo
    OpenAI completo, sem capacidade extra a justificar código próprio
    (diferente do OpenRouter, que ganhou usage.cost/provider/reasoning)."""
    from backend.settings import settings

    monkeypatch.setattr(settings, "nine_router_base_url", "http://localhost:20128/v1")
    monkeypatch.setattr(settings, "nine_router_api_key", "9r-test-key")

    modelo = _build_concrete_model("nine_router", "cc/claude-opus-4-7", 0.7)

    assert isinstance(modelo, _FakeChatOpenAI)
    assert _FakeChatOpenAI.last_kwargs is not None
    assert _FakeChatOpenAI.last_kwargs["base_url"] == "http://localhost:20128/v1"
    assert _FakeChatOpenAI.last_kwargs["model"] == "cc/claude-opus-4-7"


def test_nine_router_sem_config_levanta_erro_claro(monkeypatch):
    from backend.settings import settings

    monkeypatch.setattr(settings, "nine_router_base_url", None)
    monkeypatch.setattr(settings, "nine_router_api_key", None)

    with pytest.raises(ValueError, match="9Router"):
        _build_concrete_model("nine_router", "cc/claude-opus-4-7", 0.7)


def test_ollama_usa_cliente_nativo_e_nao_init_chat_model(monkeypatch):
    """O caminho antigo (`init_chat_model(model_provider="ollama")`) escondia
    `thinking`, `images` e os contadores de token."""
    from backend.llm.ollama.chat import VectoraOllamaChat
    from backend.services.utils import _build_concrete_model

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    modelo = _build_concrete_model("ollama", "gpt-oss:20b", 0.7)

    assert isinstance(modelo, VectoraOllamaChat)
    assert modelo.client.base_url == "http://127.0.0.1:11434"
    # Erro/borda: cair de volta no ChatOpenAI seria regressão silenciosa —
    # continuaria "funcionando" e perderia os três campos de novo.
    assert _FakeChatOpenAI.last_kwargs is None
