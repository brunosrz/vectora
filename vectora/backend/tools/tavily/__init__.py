"""Integração nativa com o Tavily — HTTP direto, sem `langchain-tavily`.

O pacote LangChain cobre só `/search` e `/extract`, e ainda prende
`search_depth`/`max_results` na instanciação. A API tem seis endpoints:
`/search`, `/extract`, `/crawl`, `/map`, `/research` e `/usage`.

O Hermes chegou à mesma conclusão — `plugins/web/tavily/provider.py:42` usa
`httpx` direto, nem `tavily-python` nem LangChain — mas também só implementa
search e extract.
"""

from backend.tools.tavily.client import (
    TavilyAuthError,
    TavilyClient,
    TavilyError,
    TavilyQuotaError,
    TavilyResponseError,
)

__all__ = [
    "TavilyAuthError",
    "TavilyClient",
    "TavilyError",
    "TavilyQuotaError",
    "TavilyResponseError",
]
