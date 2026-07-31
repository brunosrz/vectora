"""Web tools: busca e extração de conteúdo da internet via Tavily.

Cliente HTTP nativo (`backend/tools/tavily/`), não `langchain-tavily`: o
pacote cobria só `/search` e `/extract` e prendia `search_depth`/`max_results`
na instanciação.

Os wrappers `@tool web_search` e `fetch_url` preservam nome e formato de saída
— JSON list para `web_search`, texto puro para `fetch_url`. Esse é o contrato
com o LLM e não muda.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Literal

from langchain.tools import tool

from backend.settings import settings

logger = logging.getLogger(__name__)

#: `max_results` e `search_depth` agora são por chamada — o cliente nativo
#: não os prende na construção como o `langchain-tavily` fazia.
_MAX_RESULTS = 5


def _tavily_client() -> Any:
    """Cliente Tavily novo por chamada — barato (só monta o httpx sob demanda)
    e evita segurar conexão entre turnos do agente."""
    from backend.tools.tavily.client import TavilyClient

    return TavilyClient(api_key=settings.tavily_api_key or "")


def _run_sync(coro: Any) -> Any:
    """Roda a corrotina do cliente async a partir da tool síncrona."""
    return asyncio.run(coro)


def _is_quota_error(err: str) -> bool:
    """Retorna True se a mensagem de erro indica quota/rate-limit do Tavily."""
    el = err.lower()
    return (
        "429" in err or "too many requests" in el or "quota" in el or "rate limit" in el
    )


def _search_via_fallback(query: str) -> str:
    """Fallback sem API key: API JSON oficial do DuckDuckGo (sem chave).

    Nunca propaga — qualquer falha (rede, DNS) vira o mesmo erro textual
    que já existia sem Tavily configurado.
    """
    try:
        from backend.browser.search_fallback import search_fallback

        results = search_fallback(query)
        logger.info(
            "web_search fallback completed",
            extra={"query": query, "num_results": len(results)},
        )
        return json.dumps(results)
    except Exception:
        logger.exception("web_search fallback failed", extra={"query": query})
        return json.dumps(
            {
                "status": "error",
                "error": (
                    "TAVILY_API_KEY not configured and the fallback search "
                    "failed (network error). Set TAVILY_API_KEY to retry via "
                    "Tavily."
                ),
            }
        )


def _fetch_via_fallback(url: str) -> str:
    """Fallback sem API key para `fetch_url`: Chromium real (Playwright).
    Mesmo contrato de `_search_via_fallback` — nunca propaga."""
    try:
        from backend.browser.search_fallback import fetch_fallback

        content = fetch_fallback(url)
        logger.info(
            "fetch_url fallback completed",
            extra={"url": url, "content_length": len(content)},
        )
        return content
    except Exception:
        logger.exception("fetch_url fallback failed", extra={"url": url})
        return (
            "Error: TAVILY_API_KEY not configured and the Chromium fallback "
            "failed. Set TAVILY_API_KEY or run `playwright install chromium`."
        )


@tool(
    extras={
        "render_hint": "search_results",
        "category": "web",
        "destructive": False,
        "icon": "globe",
    }
)
def web_search(
    query: str,
    topic: Literal["general", "news", "finance"] = "general",
    time_range: Literal["day", "week", "month", "year"] | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> str:
    """Busca a web por informações atuais usando Tavily (otimizado para agentes).

    Tavily retorna resultados estruturados, prontos para RAG, com conteúdo já extraído.

    Args:
        query: String da consulta de busca
        topic: "general" (padrão), "news" (notícias) ou "finance" (finanças)
        time_range: filtro temporal opcional — "day", "week", "month" ou "year"
        include_domains: restringe a busca a estes domínios (ex: ["github.com"]).
            Use quando souber a fonte canônica — reduz ruído e contaminação.
        exclude_domains: exclui estes domínios dos resultados

    Returns:
        JSON com lista de resultados (url, title, content, raw_content) prontos
        para embedding, ou um objeto JSON com status de erro
    """
    if not settings.tavily_api_key:
        logger.warning("TAVILY_API_KEY not configured — usando fallback via Chromium")
        return _search_via_fallback(query)

    logger.info("web_search tool called", extra={"query": query, "topic": topic})

    t0 = time.perf_counter()
    try:
        from backend.persistence.tracer import tracer as _tracer
    except Exception:
        _tracer = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

    try:
        client = _tavily_client()
        results = _run_sync(
            client.search(
                query,
                topic=topic,
                time_range=time_range,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                max_results=_MAX_RESULTS,
                search_depth="advanced",
                include_raw_content=True,
            )
        )
        n_results = len(results)

        logger.info(
            "web_search completed",
            extra={"query": query, "num_results": n_results},
        )
        if _tracer:
            _tracer.record_sync(
                "web_search",
                "call",
                time.perf_counter() - t0,
                {"query": query[:120], "n_results": n_results},
            )
        return json.dumps(results)
    except Exception as e:
        err = str(e)
        logger.exception("web_search failed", extra={"query": query})
        if _tracer:
            _tracer.record_sync(
                "web_search",
                "call",
                time.perf_counter() - t0,
                {"query": query[:120]},
                status="error",
            )
        if _is_quota_error(err):
            logger.warning(
                "Tavily quota/rate limit atingido — usando fallback via Chromium",
                extra={"query": query},
            )
            return _search_via_fallback(query)
        # TavilySearch levanta ToolException quando não há resultados —
        # para o cascading isso é uma lista vazia, não um erro.
        if "no search results found" in err.lower():
            return json.dumps([])
        return json.dumps(
            {
                "status": "error",
                "error": "Web search failed. Please try again.",
            }
        )


@tool(
    extras={
        "render_hint": "code_block",
        "category": "web",
        "destructive": False,
        "icon": "link",
    }
)
def fetch_url(url: str) -> str:
    """Busca e extrai conteúdo de texto de uma URL específica usando Tavily.

    Args:
        url: URL para buscar (deve começar com http:// ou https://)

    Returns:
        Conteúdo de texto extraído da página
    """
    if not url.startswith(("http://", "https://")):
        logger.warning("fetch_url called with invalid URL", extra={"url": url})
        return "Error: URL must start with http:// or https://"

    if not settings.tavily_api_key:
        logger.warning("TAVILY_API_KEY not configured — usando fallback via Chromium")
        return _fetch_via_fallback(url)

    logger.info("fetch_url tool called", extra={"url": url})

    t0 = time.perf_counter()
    try:
        from backend.persistence.tracer import tracer as _tracer
    except Exception:
        _tracer = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

    try:
        client = _tavily_client()
        results = _run_sync(client.extract([url], extract_depth="advanced"))
        if not results:
            logger.warning("fetch_url returned no content", extra={"url": url})
            if _tracer:
                _tracer.record_sync(
                    "fetch_url",
                    "call",
                    time.perf_counter() - t0,
                    {"url": url[:120], "content_length": 0},
                )
            return f"No content found at {url}"

        content = results[0].get("raw_content", "") or results[0].get("content", "")

        logger.info(
            "fetch_url completed",
            extra={"url": url, "content_length": len(content)},
        )
        if _tracer:
            _tracer.record_sync(
                "fetch_url",
                "call",
                time.perf_counter() - t0,
                {"url": url[:120], "content_length": len(content)},
            )
        return content

    except Exception as e:
        err = str(e)
        logger.exception("fetch_url failed", extra={"url": url})
        if _tracer:
            _tracer.record_sync(
                "fetch_url",
                "call",
                time.perf_counter() - t0,
                {"url": url[:120]},
                status="error",
            )
        if _is_quota_error(err):
            logger.warning(
                "Tavily quota/rate limit atingido — usando fallback via Chromium",
                extra={"url": url},
            )
            return _fetch_via_fallback(url)
        if "no extracted results" in err.lower():
            return f"No content found at {url}"
        return "Error occurred fetching URL. Please check logs."
