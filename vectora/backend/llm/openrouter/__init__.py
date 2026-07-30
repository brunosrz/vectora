"""Integração nativa com o OpenRouter — HTTP direto, sem camada LangChain.

A integração LangChain (`langchain-openrouter`) cobre só chat; embeddings,
rerank, imagem, TTS, STT e vídeo ficariam de fora. E o caminho anterior
(`ChatOpenAI` com `base_url` trocado) amarra o comportamento ao que o cliente
da OpenAI expõe: provider routing, `usage.cost` e reasoning do OpenRouter não
têm caminho de primeira classe por ali.
"""

from backend.llm.openrouter.client import (
    OpenRouterAuthError,
    OpenRouterClient,
    OpenRouterCreditError,
    OpenRouterError,
    OpenRouterRateLimitError,
    OpenRouterResponseError,
    OpenRouterServerError,
)

__all__ = [
    "OpenRouterAuthError",
    "OpenRouterClient",
    "OpenRouterCreditError",
    "OpenRouterError",
    "OpenRouterRateLimitError",
    "OpenRouterResponseError",
    "OpenRouterServerError",
]
