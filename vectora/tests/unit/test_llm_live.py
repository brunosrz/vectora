"""``load_llm()`` (``backend/services/utils.py``) contra APIs reais — Google
Gemini e Cohere. Sem mock: cada teste faz pelo menos uma chamada de rede de
verdade e consome quota real das chaves configuradas em ``~/.vectora/.env``.

Guardado em duas camadas:
- marker ``live`` (``pyproject.toml``) — só roda via ``scons tests-live``,
  nunca em ``scons tests``.
- skip guard por provider via ``Settings.configured_llm_providers()`` — sem
  a credencial real configurada, o teste some da suíte com razão clara em
  vez de falhar.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from pydantic import BaseModel, Field

from backend.services.utils import load_llm
from backend.settings import settings

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

pytestmark = pytest.mark.live

requires_google = pytest.mark.skipif(
    "google-genai" not in settings.configured_llm_providers(),
    reason="GOOGLE_API_KEY não configurado em ~/.vectora/.env",
)
requires_cohere = pytest.mark.skipif(
    "cohere" not in settings.configured_llm_providers(),
    reason="COHERE_API_KEY não configurado em ~/.vectora/.env",
)

_GOOGLE_MODEL_ID = "google_genai:gemini-2.5-flash"
_COHERE_MODEL_ID = "cohere:command-a-03-2025"


class _WeatherReport(BaseModel):
    city: str = Field(description="Nome da cidade consultada")
    condition: str = Field(description="Condição climática resumida em 1-3 palavras")


def _weather_tool():
    """Tool trivial e determinística — só existe para o modelo escolher chamar."""
    from langchain_core.tools import tool

    @tool
    def get_weather(city: str) -> str:
        """Devolve o clima atual de uma cidade."""
        return f"{city}: 21C, ensolarado"

    return get_weather


# ---------------------------------------------------------------------------
# Completion simples (.ainvoke)
# ---------------------------------------------------------------------------


@requires_google
async def test_completion_google_ainvoke_real():
    model = load_llm(_GOOGLE_MODEL_ID)
    result = await model.ainvoke("Responda só com a palavra OK, nada mais.")
    assert isinstance(result.content, str)
    assert result.content.strip()


@requires_cohere
async def test_completion_cohere_ainvoke_real():
    model = load_llm(_COHERE_MODEL_ID)
    result = await model.ainvoke("Responda só com a palavra OK, nada mais.")
    assert isinstance(result.content, str)
    assert result.content.strip()


@requires_google
async def test_completion_google_prompt_longo_real():
    # Borda: prompt bem maior que uma linha — confirma que o wrapper não trunca
    # nem quebra com payload de request maior.
    model = load_llm(_GOOGLE_MODEL_ID)
    prompt = "Resuma em uma frase: " + "Vectora é um agente de codificação. " * 40
    result = await model.ainvoke(prompt)
    assert result.content.strip()


# ---------------------------------------------------------------------------
# Streaming (.astream) — múltiplos chunks reais chegando token a token
# ---------------------------------------------------------------------------


@requires_google
async def test_streaming_google_astream_real():
    model = load_llm(_GOOGLE_MODEL_ID)
    chunks = [
        str(chunk.content)
        async for chunk in model.astream("Conte de 1 a 5, um número por linha.")
        if chunk.content
    ]
    assert len(chunks) > 1, "esperava múltiplos chunks reais do streaming"
    assert "".join(chunks).strip()


@requires_cohere
async def test_streaming_cohere_astream_real():
    model = load_llm(_COHERE_MODEL_ID)
    chunks = [
        str(chunk.content)
        async for chunk in model.astream("Conte de 1 a 5, um número por linha.")
        if chunk.content
    ]
    assert len(chunks) > 1, "esperava múltiplos chunks reais do streaming"
    assert "".join(chunks).strip()


# ---------------------------------------------------------------------------
# Tool calling real (.bind_tools)
# ---------------------------------------------------------------------------


@requires_google
async def test_tool_calling_google_bind_tools_real():
    model = cast("BaseChatModel", load_llm(_GOOGLE_MODEL_ID)).bind_tools(
        [_weather_tool()]
    )
    result = await model.ainvoke(
        "Qual é o clima em Lisboa agora? Use a tool disponível para responder."
    )
    assert result.tool_calls
    assert result.tool_calls[0]["name"] == "get_weather"
    assert "city" in result.tool_calls[0]["args"]


@requires_cohere
async def test_tool_calling_cohere_bind_tools_real():
    model = cast("BaseChatModel", load_llm(_COHERE_MODEL_ID)).bind_tools(
        [_weather_tool()]
    )
    result = await model.ainvoke(
        "Qual é o clima em Lisboa agora? Use a tool disponível para responder."
    )
    assert result.tool_calls
    assert result.tool_calls[0]["name"] == "get_weather"
    assert "city" in result.tool_calls[0]["args"]


# ---------------------------------------------------------------------------
# Structured output real (.with_structured_output)
# ---------------------------------------------------------------------------


@requires_google
async def test_structured_output_google_real():
    model = load_llm(_GOOGLE_MODEL_ID).with_structured_output(_WeatherReport)
    result = await model.ainvoke(
        "O clima em Lisboa está ensolarado e agradável. Preencha o relatório "
        "estruturado sobre essa cidade."
    )
    assert isinstance(result, _WeatherReport)
    assert result.city
    assert result.condition


@requires_cohere
async def test_structured_output_cohere_real():
    model = load_llm(_COHERE_MODEL_ID).with_structured_output(_WeatherReport)
    result = await model.ainvoke(
        "O clima em Lisboa está ensolarado e agradável. Preencha o relatório "
        "estruturado sobre essa cidade."
    )
    assert isinstance(result, _WeatherReport)
    assert result.city
    assert result.condition


# ---------------------------------------------------------------------------
# Erro claro em model_id inválido/inexistente
# ---------------------------------------------------------------------------


def test_load_llm_provider_desconhecido_levanta_erro_claro():
    with pytest.raises(ValueError, match="Provider de LLM desconhecido"):
        load_llm("provider-que-nao-existe:algum-modelo")


@requires_google
async def test_completion_google_model_id_inexistente_real_levanta_erro():
    # Provider válido, nome de modelo que a API do Google recusa de verdade —
    # não é validado localmente, o erro vem da chamada de rede real.
    model = load_llm("google_genai:modelo-que-nao-existe-9999")
    with pytest.raises(Exception):  # noqa: B017 — exceção real do SDK, não tipada aqui
        await model.ainvoke("oi")


# ---------------------------------------------------------------------------
# Fallback Google → Cohere real (backend/llm/provider_fallback.py)
# ---------------------------------------------------------------------------


@requires_google
@requires_cohere
async def test_fallback_google_para_cohere_real(monkeypatch: pytest.MonkeyPatch):
    """Exercita ``try_with_fallback`` de ponta a ponta com uma chamada de
    recuperação real ao Cohere.

    A chave do Google é forçada para um valor inválido via env (mesma
    resolução de ``load_llm`` → ``get_env("GOOGLE_API_KEY")``), então a
    primeira chamada falha de verdade contra a API do Google. Exceder
    quota de verdade não é reproduzível sob demanda num teste
    determinístico — por isso a classificação do erro como "quota" é
    forçada (``is_quota_error`` monkeypatchado só aqui); o mecanismo de
    troca de provider e a chamada de recuperação ao Cohere continuam
    reais.
    """
    from backend.llm import provider_fallback

    monkeypatch.setenv("GOOGLE_API_KEY", "invalid-key-forced-for-live-test")
    monkeypatch.setattr(provider_fallback, "is_quota_error", lambda exc: True)
    monkeypatch.setattr(provider_fallback, "_fallback_order", list)

    async def _call(model_id: str):
        model = load_llm(model_id)
        return await model.ainvoke("Responda só com a palavra OK.")

    result = await provider_fallback.try_with_fallback(_call, _GOOGLE_MODEL_ID)
    assert result.content.strip()


@requires_google
async def test_fallback_sem_cohere_configurado_propaga_quota_exhausted(
    monkeypatch: pytest.MonkeyPatch,
):
    # Par de erro/borda do teste anterior: cadeia de fallback vazia (nenhum
    # outro provider com key) esgota e levanta QuotaExhaustedError, em vez de
    # silenciosamente devolver uma resposta vazia ou travar.
    from backend.llm import provider_fallback

    monkeypatch.setenv("GOOGLE_API_KEY", "invalid-key-forced-for-live-test")
    monkeypatch.setattr(provider_fallback, "is_quota_error", lambda exc: True)
    monkeypatch.setattr(provider_fallback, "_fallback_order", list)
    monkeypatch.setattr(provider_fallback, "_provider_has_key", lambda provider: False)

    async def _call(model_id: str):
        model = load_llm(model_id)
        return await model.ainvoke("Responda só com a palavra OK.")

    with pytest.raises(provider_fallback.QuotaExhaustedError):
        await provider_fallback.try_with_fallback(_call, _GOOGLE_MODEL_ID)
