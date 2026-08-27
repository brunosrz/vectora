"""Fallback de busca sem API key (`backend/browser/search_fallback.py`)
contra serviços reais: a API JSON do DuckDuckGo (`search_fallback`, requer
rede) e Chromium real (`fetch_fallback`, requer `playwright install
chromium` — skip limpo sem ele, mesmo padrão de `test_browser_session_real.py`).
"""

from __future__ import annotations

import pytest

from backend.browser import search_fallback


def _chromium_available() -> bool:
    from pathlib import Path

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    try:
        with sync_playwright() as p:
            return Path(p.chromium.executable_path).is_file()
    except Exception:
        return False


pytestmark = pytest.mark.browser


@pytest.fixture(autouse=True)
def _clean_fallback_browser():
    """Garante nenhum Chromium do fallback sobrando de um teste anterior."""
    search_fallback.close_search_fallback_browser()
    yield
    search_fallback.close_search_fallback_browser()


def test_search_fallback_retorna_resultados_reais_do_duckduckgo():
    results = search_fallback.search_fallback("python programming language")

    assert len(results) > 0
    for r in results:
        assert r["title"]
        assert "url" in r
        assert "content" in r


def test_search_fallback_query_sem_instant_answer_retorna_lista_vazia_sem_lancar():
    # Par de erro/borda: query sem AbstractText/RelatedTopics (ex.: string
    # aleatória sem entrada na base de instant-answers) não deve lançar —
    # só retorna lista vazia, e o caller trata isso normalmente.
    results = search_fallback.search_fallback("asdkjqwoiehjqwoiuhASDLKJQWEOIU9812739")
    assert results == []


@pytest.mark.skipif(
    not _chromium_available(),
    reason="Chromium não instalado — rode `playwright install chromium`",
)
def test_fetch_fallback_extrai_texto_visivel_de_uma_pagina_real():
    text = search_fallback.fetch_fallback("https://example.com")

    assert "Example Domain" in text


@pytest.mark.skipif(
    not _chromium_available(),
    reason="Chromium não instalado — rode `playwright install chromium`",
)
def test_fetch_fallback_url_invalida_levanta_em_vez_de_retornar_string_vazia():
    # Par de erro: URL inexistente/malformada deve levantar (o caller —
    # backend/tools/web.py — é quem decide degradar pro erro textual),
    # nunca retornar silenciosamente uma string vazia.
    #
    # `.invalid` é um TLD reservado (RFC 2606) que nunca resolve em DNS
    # nenhum — então `ssrf_guard.is_url_ssrf_safe` (fail-closed por design:
    # falha de resolução também é tratada como não-seguro, ver seu
    # docstring) sempre recusa essa URL ANTES de chegar no Chromium.
    # Esperar um erro do Playwright aqui pressupunha que o guard deixasse a
    # URL passar — nunca foi verdade em nenhum ambiente com DNS correto, só
    # não se manifestava porque este teste ficava skipped sem Chromium.
    with pytest.raises(ValueError, match="SSRF"):
        search_fallback.fetch_fallback(
            "https://este-dominio-nao-existe-de-verdade.invalid"
        )
