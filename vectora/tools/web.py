"""Web tools: busca e extração de conteúdo da internet via Tavily."""

import json
import logging
import time

from langchain.tools import tool
from tavily import TavilyClient

from vectora.config.settings import settings

logger = logging.getLogger(__name__)


@tool
def web_search(query: str) -> str:
    """Busca a web por informações atuais usando Tavily (otimizado para agentes).

    Tavily retorna resultados estruturados, prontos para RAG, com conteúdo já extraído.

    Args:
        query: String da consulta de busca

    Returns:
        JSON com resultados estruturados (url, title, content) prontos para embedding
    """
    if not settings.tavily_api_key:
        logger.error("TAVILY_API_KEY not configured")
        return json.dumps(
            {
                "status": "error",
                "error": "TAVILY_API_KEY not configured. Set TAVILY_API_KEY environment variable.",
            }
        )

    logger.info("web_search tool called", extra={"query": query})

    t0 = time.perf_counter()
    try:
        from vectora.services.tracer import tracer as _tracer
    except Exception:
        _tracer = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

    try:
        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(query=query, search_depth="advanced", max_results=5)
        n_results = len(response.get("results", []))

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
        return json.dumps(response["results"])
    except Exception as e:
        err = str(e)
        err_lower = err.lower()
        logger.exception("web_search failed", extra={"query": query})
        if _tracer:
            _tracer.record_sync(
                "web_search",
                "call",
                time.perf_counter() - t0,
                {"query": query[:120]},
                status="error",
            )
        if "429" in err or "too many requests" in err_lower or "quota" in err_lower:
            return json.dumps(
                {
                    "status": "quota_error",
                    "error": (
                        "**⚠️ Tavily: quota/rate limit atingido.**\n"
                        "Aguarde alguns minutos ou verifique seu plano em app.tavily.com."
                    ),
                }
            )
        return json.dumps(
            {
                "status": "error",
                "error": "Web search failed. Please try again.",
            }
        )


@tool
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
        logger.error("TAVILY_API_KEY not configured")
        return "Error: TAVILY_API_KEY not configured. Cannot fetch URL."

    logger.info("fetch_url tool called", extra={"url": url})

    t0 = time.perf_counter()
    try:
        from vectora.services.tracer import tracer as _tracer
    except Exception:
        _tracer = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

    try:
        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.extract(urls=[url])

        results = response.get("results", [])
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
        err_lower = err.lower()
        logger.exception("fetch_url failed", extra={"url": url})
        if _tracer:
            _tracer.record_sync(
                "fetch_url",
                "call",
                time.perf_counter() - t0,
                {"url": url[:120]},
                status="error",
            )
        if "429" in err or "too many requests" in err_lower or "quota" in err_lower:
            return (
                "**⚠️ Tavily: quota/rate limit atingido.**\n"
                "Aguarde alguns minutos ou verifique seu plano em app.tavily.com."
            )
        return "Error occurred fetching URL. Please check logs."
