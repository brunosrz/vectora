"""``web_search``/``fetch_url`` (``backend/tools/web.py``) contra o Tavily
real. Sem mock: cada teste chama a API do Tavily de verdade e consome quota
real da chave configurada em ``~/.vectora/.env``.

Guardado pelo marker ``live`` (só via ``scons tests-live``) e por
``settings.tavily_api_key`` truthy — mesmo padrão de guard que
``backend/tools/web.py:161`` já usa para decidir entre Tavily e o fallback
via DuckDuckGo/Chromium.

Complementa (não duplica) ``test_browser_search_fallback_real.py`` — aquele
arquivo testa o caminho SEM Tavily (fallback DuckDuckGo/Chromium); este
testa especificamente o caminho COM Tavily configurado.
"""

from __future__ import annotations

import json

import pytest

from backend.settings import settings
from backend.tools.web import fetch_url, web_search

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not settings.tavily_api_key,
        reason="TAVILY_API_KEY não configurado em ~/.vectora/.env",
    ),
]


def _results(raw: str) -> list[dict]:
    data = json.loads(raw)
    assert isinstance(data, list), f"esperava lista de resultados, veio: {data!r}"
    return data


# ---------------------------------------------------------------------------
# web_search — queries reais, estrutura da resposta
# ---------------------------------------------------------------------------


def test_web_search_query_generica_real():
    raw = web_search.invoke({"query": "LangChain framework"})
    results = _results(raw)
    assert len(results) > 0
    for r in results:
        assert r.get("url")
        assert r.get("title") is not None
        assert r.get("content") is not None


def test_web_search_query_local_com_time_range_real():
    raw = web_search.invoke(
        {"query": "clima em São Paulo hoje", "topic": "general", "time_range": "day"}
    )
    results = _results(raw)
    assert len(results) > 0


def test_web_search_query_tecnica_especifica_real():
    raw = web_search.invoke({"query": "LangGraph StateGraph checkpointer async"})
    results = _results(raw)
    assert len(results) > 0
    assert any("content" in r and r["content"] for r in results)


def test_web_search_topic_finance_real():
    raw = web_search.invoke({"query": "Nvidia stock price", "topic": "finance"})
    results = _results(raw)
    assert len(results) > 0


def test_web_search_com_include_domains_real():
    raw = web_search.invoke(
        {"query": "python asyncio", "include_domains": ["github.com"]}
    )
    results = _results(raw)
    # Tavily pode devolver menos resultados quando restrito a um domínio —
    # o importante é que nenhum resultado escape do domínio pedido.
    for r in results:
        assert "github.com" in r.get("url", "")


def test_web_search_com_exclude_domains_real():
    raw = web_search.invoke(
        {"query": "python asyncio tutorial", "exclude_domains": ["github.com"]}
    )
    results = _results(raw)
    for r in results:
        assert "github.com" not in r.get("url", "")


def test_web_search_query_vazia_borda():
    # Par de erro/borda: query vazia não deve derrubar a tool nem propagar
    # exceção — TavilySearch trata como sem resultados/erro tipado, mas o
    # contrato da tool (nunca lançar) tem que se manter.
    raw = web_search.invoke({"query": ""})
    data = json.loads(raw)
    assert isinstance(data, (list, dict))
    if isinstance(data, dict):
        assert "error" in data or "status" in data


# ---------------------------------------------------------------------------
# fetch_url — extração de conteúdo real
# ---------------------------------------------------------------------------


def test_fetch_url_pagina_real():
    content = fetch_url.invoke({"url": "https://python.langchain.com/"})
    assert isinstance(content, str)
    assert content.strip()
    assert not content.startswith("Error:")


def test_fetch_url_url_invalida_sem_lancar():
    # Borda: URL sem esquema não bate rede nenhuma — validação local, mas
    # ainda cobre o contrato "nunca lança, sempre devolve string de erro".
    result = fetch_url.invoke({"url": "not-a-real-url"})
    assert result.startswith("Error:")


def test_fetch_url_pagina_inexistente_real_nao_lanca():
    # Domínio real, path que garantidamente não existe — extração real
    # falha, mas a tool deve degradar para texto de erro, nunca propagar.
    content = fetch_url.invoke(
        {"url": "https://python.langchain.com/este-path-nao-existe-vectora-test-404"}
    )
    assert isinstance(content, str)
