"""MCP env bootstrap — persiste keys recebidas via env vars na primeira execução.

Quando o Vectora é instalado via MCP registry (Smithery, mcp.so, etc.), o cliente
MCP passa as API keys como variáveis de ambiente do processo antes de iniciar o
servidor. Este módulo detecta esse cenário e persiste os segredos em
~/.vectora/.env para que o chat interativo (`vectora`) também funcione sem
precisar do wizard. ``LLM_PROVIDER`` não é segredo — vai pra ``app_settings``
(SQLite, `backend/workspace/runtime_settings.py`), tratado à parte de
``_MCP_ENV_KEYS``.

Fluxo:
  1. MCP client instala vectora e coleta COHERE_API_KEY, TAVILY_API_KEY, etc.
  2. Inicia `vectora mcp-server` com essas vars no ambiente do processo.
  3. _bootstrap_env_from_mcp() roda na inicialização do servidor.
  4. Se ~/.vectora/.env não existir (primeira execução), cria com as keys presentes.
  5. Se já existir, só adiciona keys que ainda não estão lá (nunca sobrescreve).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from backend.settings import settings

logger = logging.getLogger(__name__)

# Keys secretas que o server.json declara em environmentVariables.
# Ordem importa: aparecerão nessa ordem no .env gerado.
_MCP_ENV_KEYS: list[tuple[str, str]] = [
    # (env var name, comentário descritivo)
    ("GOOGLE_API_KEY", "Google Gemini API key"),
    ("OPENAI_API_KEY", "OpenAI API key"),
    ("ANTHROPIC_API_KEY", "Anthropic API key"),
    ("COHERE_API_KEY", "Cohere API key — embeddings + reranking + optional LLM"),
    ("TAVILY_API_KEY", "Tavily API key — web search + URL extraction"),
    ("LANGSMITH_API_KEY", "LangSmith API key (optional — tracing)"),
    ("LANGSMITH_TRACING", "LangSmith tracing enabled (true/false)"),
    ("LANGSMITH_PROJECT", "LangSmith project name"),
]

_ENV_FILE = settings.vectora_home / ".env"


def _bootstrap_llm_provider_from_mcp() -> bool:
    """Persiste LLM_PROVIDER do ambiente MCP em app_settings (SQLite), se ainda
    não houver um provider configurado. Não é segredo — não vai pro ``.env``.
    """
    provider = os.environ.get("LLM_PROVIDER")
    if not provider:
        return False
    from backend.workspace.runtime_settings import runtime_settings

    if runtime_settings.has("active_provider"):
        return False
    runtime_settings.set("active_provider", provider)
    logger.info("env_bootstrap: LLM_PROVIDER=%s persistido em app_settings", provider)
    return True


def _read_existing_keys(env_file: Path) -> set[str]:
    """Lê as keys já presentes no .env (linhas KEY=...). Ignora comentários."""
    keys: set[str] = set()
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                keys.add(stripped.split("=", 1)[0].strip())
    except Exception:
        pass
    return keys


def bootstrap_env_from_mcp() -> bool:
    """Detecta keys no ambiente do processo e persiste (segredos em ~/.vectora/.env,
    LLM_PROVIDER em app_settings/SQLite).

    Só age se houver pelo menos uma key reconhecida em os.environ.
    Nunca sobrescreve valores já existentes.

    Returns:
        True se alguma key foi escrita, False caso contrário.
    """
    provider_written = _bootstrap_llm_provider_from_mcp()

    # Coleta keys presentes no ambiente do processo
    available = {
        key: os.environ[key] for key, _ in _MCP_ENV_KEYS if os.environ.get(key)
    }
    if not available:
        return provider_written

    _ENV_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing_keys = _read_existing_keys(_ENV_FILE) if _ENV_FILE.exists() else set()
    new_entries: list[str] = []

    for key, comment in _MCP_ENV_KEYS:
        if key in available and key not in existing_keys:
            new_entries.append(f"# {comment}")
            new_entries.append(f"{key}={available[key]}")

    if not new_entries:
        logger.debug("env_bootstrap: nenhuma key nova para persistir")
        return provider_written

    # Append (ou cria) o arquivo
    separator = (
        "\n# --- configurado via MCP registry ---\n" if _ENV_FILE.exists() else ""
    )
    block = separator + "\n".join(new_entries) + "\n"

    with _ENV_FILE.open("a", encoding="utf-8") as f:
        f.write(block)

    logger.info(
        "env_bootstrap: %d key(s) persistidas em %s: %s",
        len(new_entries) // 2,
        _ENV_FILE,
        ", ".join(
            k for k, _ in _MCP_ENV_KEYS if k in available and k not in existing_keys
        ),
    )
    return True


def validate_required_keys() -> list[str]:
    """Retorna lista de keys obrigatórias ausentes tanto no env quanto no .env.

    Usado para logar um aviso claro se o servidor iniciar sem as keys mínimas.
    """
    required = {"COHERE_API_KEY", "TAVILY_API_KEY"}
    existing_in_file = _read_existing_keys(_ENV_FILE) if _ENV_FILE.exists() else set()
    return [
        key
        for key in required
        if not os.environ.get(key) and key not in existing_in_file
    ]
