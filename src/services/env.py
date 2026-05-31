"""Environment Variable Management with Strict Validation.

Provides typed access to environment variables with optional strict mode.
Includes custom exceptions for missing required configuration.
"""

import os
from typing import Literal, overload


class GetEnvError(BaseException): ...


class CohereMissingError(GetEnvError):
    """Erro quando Cohere API key não está configurada."""

    def __init__(self) -> None:
        msg = (
            "\n"
            "[X] ERRO: Vectora depende 100% da Cohere para funcionar\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Vectora utiliza Cohere (integração first-class no LangChain) para:\n"
            "  • Embedding (gerar vetores via embed-multilingual-v3.0)\n"
            "  • Reranking (ordenar via rerank-multilingual-v3.0)\n\n"
            "Sem Cohere, Vectora não consegue executar RAG (Retrieval-Augmented Generation).\n\n"
            "SOLUÇÃO:\n"
            "  1. Obtenha uma API key GRATUITA em: https://dashboard.cohere.com/api-keys\n"
            "  2. Configure a variável COHERE_API_KEY em seu .env:\n\n"
            "     COHERE_API_KEY=...\n\n"
            "  3. Reinicie a aplicação\n\n"
            "A Cohere oferece um free tier com excelentes limites para uso.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        super().__init__(msg)


@overload
def get_env(name: str) -> str: ...


@overload
def get_env(name: str, *, strict: Literal[True]) -> str: ...


@overload
def get_env(name: str, *, strict: Literal[False]) -> str | None: ...


def get_env(name: str, *, strict: bool = True) -> str | None:
    """Get environment variable with optional strict validation."""
    value = os.getenv(name)

    if value is None and strict:
        msg = f"Env variable {name!r} does not exist"
        raise GetEnvError(msg)

    return value


def validate_cohere() -> None:
    """Valida que Cohere API key está configurada.

    Vectora depende 100% da Cohere para embedding e reranking.
    Sem ela, a aplicação não funciona.

    Raises:
        CohereMissingError: Se COHERE_API_KEY não está configurada
    """
    cohere_key = get_env("COHERE_API_KEY", strict=False)

    if not cohere_key:
        raise CohereMissingError
