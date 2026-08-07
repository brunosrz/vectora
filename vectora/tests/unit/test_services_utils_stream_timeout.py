"""``backend/services/utils.py::_build_concrete_model`` — nenhum provider pode
impor timeout de silêncio entre chunks. Modelos de raciocínio (reasoning)
ficam minutos "pensando" sem emitir nenhum token — isso é comportamento
normal, não falha de conexão.

"openai", "openrouter" e "nine_router" saíram do ``ChatOpenAI`` e usam
clients nativos, que controlam o timeout HTTP diretamente — sem o
`stream_chunk_timeout` de 120s que o `langchain_openai` aplicava por padrão.
A dependência `langchain-openai` foi removida do projeto na Sprint 13 — não
há mais nenhum caminho de código capaz de instanciar `ChatOpenAI`, então o
guard de regressão vira o próprio isinstance positivo na classe nativa.
"""

from __future__ import annotations

import pytest

from backend.services.env import GetEnvError
from backend.services.utils import _build_concrete_model


def test_openai_usa_cliente_nativo_e_nao_chat_openai(monkeypatch):
    """O caminho antigo (`ChatOpenAI`) tinha `stream_chunk_timeout=120s` por
    padrão — o client nativo (Responses API) controla o timeout HTTP
    diretamente, sem esse problema."""
    from backend.llm.openai.chat import VectoraOpenAIChat

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    modelo = _build_concrete_model("openai", "gpt-5", 0.7)

    assert isinstance(modelo, VectoraOpenAIChat)


def test_openrouter_usa_cliente_nativo_e_nao_chat_openai(monkeypatch):
    """O caminho antigo (`ChatOpenAI` com base_url trocado) descartava
    `usage.cost`, o bloco `provider` e o `reasoning` do delta."""
    from backend.llm.openrouter.chat import VectoraOpenRouterChat

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    modelo = _build_concrete_model("openrouter", "openrouter/auto", 0.7)

    assert isinstance(modelo, VectoraOpenRouterChat)


def test_openrouter_sem_api_key_levanta_erro_claro(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(GetEnvError, match="OPENROUTER_API_KEY"):
        _build_concrete_model("openrouter", "openrouter/auto", 0.7)


def test_nine_router_reusa_cliente_nativo_do_openrouter_com_base_url_trocada(
    monkeypatch,
):
    """9Router fala o mesmo protocolo Chat Completions que o adapter nativo
    do OpenRouter já implementa — reusa `VectoraOpenRouterChat`/
    `OpenRouterClient` com `base_url` apontando pro 9Router, em vez da
    Responses API que `VectoraOpenAIChat` consome (9Router não a expõe)."""
    from backend.llm.openrouter.chat import VectoraOpenRouterChat
    from backend.settings import settings

    monkeypatch.setattr(settings, "nine_router_base_url", "http://localhost:20128/v1")
    monkeypatch.setattr(settings, "nine_router_api_key", "9r-test-key")

    modelo = _build_concrete_model("nine_router", "cc/claude-opus-4-7", 0.7)

    assert isinstance(modelo, VectoraOpenRouterChat)
    assert modelo.client._base_url == "http://localhost:20128/v1"
    assert modelo.model == "cc/claude-opus-4-7"


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
