"""Web tools: busca e extração de conteúdo da internet via Tavily.

Migrado de `tavily-python` para `langchain-tavily` (TavilySearch / TavilyExtract).

Os wrappers `@tool web_search` e `fetch_url` preservam nome e formato de saída
— JSON list para `web_search`, texto puro para `fetch_url` — exigidos pelo
cascading downstream (`process_retrieval`, `rag_subgraph`). A migração apenas
troca o backend e desbloqueia novos parâmetros (topic, time_range, filtros de
domínio), sem mexer no contrato com o resto do grafo.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal

from langchain.tools import tool

from src.settings import settings

try:
    from langchain_tavily import TavilyExtract, TavilySearch
except ImportError:
    TavilySearch = None  # type: ignore[assignment,misc]  # ty: ignore[invalid-assignment]
    TavilyExtract = None  # type: ignore[assignment,misc]  # ty: ignore[invalid-assignment]

logger = logging.getLogger(__name__)

# Parâmetros que só podem ser definidos na instanciação (não por chamada).
_MAX_RESULTS = 5

# Singletons — instanciados sob demanda na primeira chamada.
_search_tool: Any = None
_extract_tool: Any = None


def _get_search_tool() -> Any:
    """Obtém o TavilySearch singleton.

    `max_results`, `search_depth` e `include_raw_content` são fixados aqui —
    a API do langchain-tavily só aceita esses na instanciação. Os parâmetros
    por-chamada (topic, time_range, filtros de domínio) vão no `.invoke()`.
    """
    global _search_tool
    if _search_tool is None and TavilySearch is not None:
        _search_tool = TavilySearch(
            tavily_api_key=settings.tavily_api_key,
            max_results=_MAX_RESULTS,
            search_depth="advanced",
            include_raw_content=True,
        )
    return _search_tool


def _get_extract_tool() -> Any:
    """Obtém o TavilyExtract singleton (extração de conteúdo de URLs)."""
    global _extract_tool
    if _extract_tool is None and TavilyExtract is not None:
        _extract_tool = TavilyExtract(
            tavily_api_key=settings.tavily_api_key,
            extract_depth="advanced",
        )
    return _extract_tool


def _is_quota_error(err: str) -> bool:
    """Retorna True se a mensagem de erro indica quota/rate-limit do Tavily."""
    el = err.lower()
    return (
        "429" in err or "too many requests" in el or "quota" in el or "rate limit" in el
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
    if TavilySearch is None:
        logger.error("langchain-tavily não instalado")
        return json.dumps(
            {"status": "error", "error": "langchain-tavily não instalado."}
        )

    if not settings.tavily_api_key:
        logger.error("TAVILY_API_KEY not configured")
        return json.dumps(
            {
                "status": "error",
                "error": "TAVILY_API_KEY not configured. Set TAVILY_API_KEY environment variable.",
            }
        )

    logger.info("web_search tool called", extra={"query": query, "topic": topic})

    t0 = time.perf_counter()
    try:
        from src.services.tracer import tracer as _tracer
    except Exception:
        _tracer = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

    invoke_args: dict[str, Any] = {"query": query, "topic": topic}
    if time_range:
        invoke_args["time_range"] = time_range
    if include_domains:
        invoke_args["include_domains"] = include_domains
    if exclude_domains:
        invoke_args["exclude_domains"] = exclude_domains

    try:
        response = _get_search_tool().invoke(invoke_args)
        # langchain-tavily devolve {"error": exc} em vez de levantar.
        if isinstance(response, dict) and response.get("error"):
            raise RuntimeError(str(response["error"]))

        results = response.get("results", []) if isinstance(response, dict) else []
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
            return json.dumps(
                {
                    "status": "quota_error",
                    "error": (
                        "**Tavily: quota/rate limit atingido.**\n"
                        "Aguarde alguns minutos ou verifique seu plano em app.tavily.com."
                    ),
                }
            )
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

    if TavilyExtract is None:
        logger.error("langchain-tavily não instalado")
        return "Error: langchain-tavily não instalado. Cannot fetch URL."

    if not settings.tavily_api_key:
        logger.error("TAVILY_API_KEY not configured")
        return "Error: TAVILY_API_KEY not configured. Cannot fetch URL."

    logger.info("fetch_url tool called", extra={"url": url})

    t0 = time.perf_counter()
    try:
        from src.services.tracer import tracer as _tracer
    except Exception:
        _tracer = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

    try:
        response = _get_extract_tool().invoke({"urls": [url]})
        if isinstance(response, dict) and response.get("error"):
            raise RuntimeError(str(response["error"]))

        results = response.get("results", []) if isinstance(response, dict) else []
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
            return (
                "**Tavily: quota/rate limit atingido.**\n"
                "Aguarde alguns minutos ou verifique seu plano em app.tavily.com."
            )
        if "no extracted results" in err.lower():
            return f"No content found at {url}"
        return "Error occurred fetching URL. Please check logs."
