"""Tests for backend/tools/web.py — Tavily + fallback via Chromium."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from backend.tools.web import fetch_url, web_search


class TestWebSearchFallback:
    def test_sem_tavily_api_key_usa_fallback_via_chromium(self):
        with (
            patch("backend.tools.web.settings") as ms,
            patch(
                "backend.browser.search_fallback.search_fallback",
                return_value=[{"title": "t", "content": "c", "url": "u"}],
            ) as mock_fallback,
        ):
            ms.tavily_api_key = None
            result = web_search.invoke({"query": "python"})

        mock_fallback.assert_called_once_with("python")
        data = json.loads(result)
        assert data == [{"title": "t", "content": "c", "url": "u"}]

    def test_sem_tavily_e_fallback_tambem_falha_retorna_erro_textual(self):
        # Par de erro: nem Tavily nem o fallback disponíveis — a tool nunca
        # propaga a exceção, sempre devolve JSON de erro pro agente.
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
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = {"results": [{"title": "tavily result"}]}
        with (
            patch("backend.tools.web.settings") as ms,
            patch("backend.tools.web._get_search_tool", return_value=mock_tool),
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
            patch(
                "backend.browser.search_fallback.fetch_fallback",
                return_value="conteúdo extraído",
            ) as mock_fallback,
        ):
            ms.tavily_api_key = None
            result = fetch_url.invoke({"url": "https://example.com"})

        mock_fallback.assert_called_once_with("https://example.com")
        assert result == "conteúdo extraído"

    def test_sem_tavily_e_fallback_tambem_falha_retorna_erro_textual(self):
        with (
            patch("backend.tools.web.settings") as ms,
            patch(
                "backend.browser.search_fallback.fetch_fallback",
                side_effect=RuntimeError("chromium ausente"),
            ),
        ):
            ms.tavily_api_key = None
            result = fetch_url.invoke({"url": "https://example.com"})

        assert "Error" in result
