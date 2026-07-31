"""Integração nativa com o Ollama — HTTP direto, sem camada LangChain.

`langchain-ollama` cobre chat de texto e esconde o que o endpoint nativo
expõe: `images` por mensagem (vision), `message.thinking` separado do
conteúdo, e os contadores de token. O `/api/show` — fonte de verdade das
capacidades por modelo — nem aparece por lá.
"""

from backend.llm.ollama.client import (
    OllamaClient,
    OllamaError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaUnreachableError,
)

__all__ = [
    "OllamaClient",
    "OllamaError",
    "OllamaModelNotFoundError",
    "OllamaResponseError",
    "OllamaUnreachableError",
]
