"""Tests for backend/tools/web.py — Tavily + fallback via Chromium."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from backend.tools.web import fetch_url, web_search


class TestWebSearchFallback:
    def test_sem_tavily_api_key_usa_fallback_via_chromium(self, monkeypatch):
        """Sem chave nenhuma o roteador elege o DuckDuckGo — o comportamento
        histórico. O patch vai em `backend.settings.settings`, a fonte que o
        roteador lê: mockar só o alias do módulo da tool deixaria o roteador
        vendo a chave real do ambiente."""
        from backend.settings import settings as _s

        monkeypatch.setattr(_s, "tavily_api_key", "", raising=False)
        monkeypatch.setattr(_s, "ollama_api_key", "", raising=False)

        with patch(
            "backend.browser.search_fallback.search_fallback",
            return_value=[{"title": "t", "content": "c", "url": "u"}],
        ) as mock_fallback:
            result = web_search.invoke({"query": "python"})

        mock_fallback.assert_called_once_with("python", max_results=5)
        data = json.loads(result)
        assert data == [{"title": "t", "content": "c", "url": "u"}]

    def test_sem_tavily_e_fallback_tambem_falha_retorna_erro_textual(self, monkeypatch):
        # Par de erro: nem Tavily nem o fallback disponíveis — a tool nunca
        # propaga a exceção, sempre devolve JSON de erro pro agente.
        from backend.settings import settings as _s

        monkeypatch.setattr(_s, "tavily_api_key", "", raising=False)
        monkeypatch.setattr(_s, "ollama_api_key", "", raising=False)
        with (
            patch("backend.tools.web.settings") as ms,
            patch(
                "backend.browser.search_fallback.search_fallback",
                side_effect=RuntimeError("chromium ausente"),
            ),
        ):
            ms.tavily_api_key = None
            result = web_search.invoke({"query": "python"})

        data = json.loads(result)
        assert data["status"] == "error"

    def test_tavily_configurado_nao_usa_fallback(self):
        """Com key válida a busca vai pelo cliente nativo, e o contrato de
        saída (`json.dumps(results)`) continua o mesmo — é o contrato com o
        LLM, não muda com a troca de backend."""
        mock_client = MagicMock()
        mock_client.search = AsyncMock(return_value=[{"title": "tavily result"}])
        with (
            patch("backend.tools.web.settings") as ms,
            patch("backend.tools.web._tavily_client", return_value=mock_client),
            patch("backend.browser.search_fallback.search_fallback") as mock_fallback,
        ):
            ms.tavily_api_key = "real-key"
            result = web_search.invoke({"query": "python"})

        mock_fallback.assert_not_called()
        data = json.loads(result)
        assert data == [{"title": "tavily result"}]


class TestFetchUrlFallback:
    def test_sem_tavily_api_key_usa_fallback_via_chromium(self):
        with (
            patch("backend.tools.web.settings") as ms,
            patch("backend.browser.ssrf_guard.is_url_ssrf_safe", return_value=True),
            patch(
                "backend.browser.search_fallback.fetch_fallback",
                return_value="conteúdo extraído",
            ) as mock_fallback,
        ):
            ms.tavily_api_key = None
            result = fetch_url.invoke({"url": "https://example.com"})

        mock_fallback.assert_called_once_with("https://example.com")
        # Sprint 35 — conteúdo de fetch_url chega envelopado como não-confiável.
        assert "conteúdo extraído" in result
        assert result.startswith('<untrusted_content source="https://example.com">')

    def test_sem_tavily_e_fallback_tambem_falha_retorna_erro_textual(self):
        with (
            patch("backend.tools.web.settings") as ms,
            patch("backend.browser.ssrf_guard.is_url_ssrf_safe", return_value=True),
            patch(
                "backend.browser.search_fallback.fetch_fallback",
                side_effect=RuntimeError("chromium ausente"),
            ),
        ):
            ms.tavily_api_key = None
            result = fetch_url.invoke({"url": "https://example.com"})

        assert "Error" in result


class TestFetchUrlSsrfGuard:
    """Sprint 34 — fetch_url recusa URLs que resolvem pra IP privado/loopback/
    link-local/metadata, antes de tentar Tavily ou o fallback Chromium."""

    def test_refuses_metadata_url_without_calling_tavily_or_fallback(self):
        with (
            patch("backend.tools.web.settings") as ms,
            patch("backend.browser.ssrf_guard.is_url_ssrf_safe", return_value=False),
            patch("backend.tools.web._get_extract_tool") as mock_extract,
            patch("backend.browser.search_fallback.fetch_fallback") as mock_fallback,
        ):
            ms.tavily_api_key = "real-key"
            result = fetch_url.invoke({"url": "http://169.254.169.254/latest/"})

        assert "Error" in result
        mock_extract.assert_not_called()
        mock_fallback.assert_not_called()

    def test_allows_public_url_with_tavily_configured(self):
        mock_client = MagicMock()
        with (
            patch("backend.tools.web.settings") as ms,
            patch("backend.browser.ssrf_guard.is_url_ssrf_safe", return_value=True),
            patch("backend.tools.web._get_extract_tool", return_value=mock_client),
            patch(
                "backend.tools.web._invoke_backend",
                new=AsyncMock(return_value=[{"content": "ok", "raw_content": ""}]),
            ),
        ):
            ms.tavily_api_key = "real-key"
            result = fetch_url.invoke({"url": "https://example.com"})

        # Sprint 35 — conteúdo de fetch_url chega envelopado como não-confiável.
        assert "ok" in result
        assert result.startswith('<untrusted_content source="https://example.com">')


class TestCrawlEMapExigemKey:
    """`web_crawl`/`web_map` não têm fallback: varredura de site não dá pra
    fazer com a API JSON do DuckDuckGo nem com uma sessão de browser."""

    def test_crawl_sem_key_devolve_erro_claro(self):
        from backend.tools.web import web_crawl

        with patch("backend.tools.web.settings") as ms:
            ms.tavily_api_key = None
            resultado = json.loads(web_crawl.invoke({"url": "https://x.test"}))

        assert "TAVILY_API_KEY" in resultado["error"]

    def test_crawl_com_url_invalida_nem_chega_a_checar_a_key(self):
        """Erro/borda: validar a URL antes evita mensagem enganosa sobre
        credencial quando o problema é o argumento."""
        from backend.tools.web import web_crawl

        with patch("backend.tools.web.settings") as ms:
            ms.tavily_api_key = "real-key"
            resultado = json.loads(web_crawl.invoke({"url": "ftp://x.test"}))

        assert "http" in resultado["error"]

    def test_map_com_key_chama_o_cliente(self):
        from backend.tools.web import web_map

        mock_client = MagicMock()
        mock_client.map = AsyncMock(return_value={"results": ["/a", "/b"]})
        with (
            patch("backend.tools.web.settings") as ms,
            patch("backend.tools.web._tavily_client", return_value=mock_client),
        ):
            ms.tavily_api_key = "real-key"
            resultado = json.loads(web_map.invoke({"url": "https://x.test"}))

        assert resultado == ["/a", "/b"]
