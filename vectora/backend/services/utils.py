"""Utility Functions and Multi-Provider LLM Loading.

Provides LLM factory function supporting Google Gemini, OpenAI, Anthropic,
Cohere, Ollama e OpenRouter:
    google-genai  → langchain-google-genai  (ChatGoogleGenerativeAI)
    openai        → cliente nativo           (VectoraOpenAIChat, Responses API)
    anthropic     → langchain-anthropic     (ChatAnthropic, prompt caching)
    cohere        → langchain-cohere        (ChatCohere; embeddings/rerank já
                                             nativos — ver backend/llm/cohere/)
    ollama        → cliente nativo           (VectoraOllamaChat, /api/chat)
    openrouter    → cliente nativo           (VectoraOpenRouterChat)

Inclui async context managers e helpers de variáveis de ambiente.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, cast

from backend.services.env import get_env

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.language_models.base import BaseLanguageModel


def _get_env_with_default(name: str, default: str) -> str:
    """Get environment variable with a default value."""
    value = get_env(name, strict=False)
    return value if value is not None else default


# provider canônico (underscore) → (env var do modelo, modelo default).
# A UI/LLM_PROVIDER pode usar hífen ("google-genai"); normalizamos p/ underscore.
_PROVIDER_SPEC: dict[str, tuple[str, str]] = {
    "google_genai": ("GOOGLE_MODEL", "gemini-2.5-flash"),
    "openai": ("OPENAI_MODEL", "gpt-4o"),
    "anthropic": ("ANTHROPIC_MODEL", "claude-opus-4-1"),
    "cohere": ("COHERE_CHAT_MODEL", "command-a-03-2025"),
    "ollama": ("OLLAMA_MODEL", "gpt-oss:20b"),
    "openrouter": ("OPENROUTER_MODEL", "openrouter/auto"),
    "nine_router": ("NINE_ROUTER_MODEL", ""),
}


def _gemini_safety_settings() -> dict:
    """Threshold mais permissivo em toda categoria que o SDK do Google aceita.

    O Vectora não filtra conteúdo — o que o modelo aceita gerar é decisão do
    modelo. Sem este dict valem os defaults do Google, que bloqueiam algumas
    categorias em nível médio. Parte das categorias o Google não deixa
    desligar de fato: isso é limite da plataforma, não escolha nossa.

    Só o Gemini expõe esta configuração. Mandar o kwarg pros outros providers
    estoura na instanciação — ver o par de erro em
    ``tests/unit/test_no_content_guardrails.py``.
    """
    from langchain_google_genai import HarmBlockThreshold, HarmCategory

    return {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY: HarmBlockThreshold.BLOCK_NONE,
    }


def _build_concrete_model(  # noqa: PLR0911
    provider: str, model_name: str, temperature: float
) -> Any:
    """Constrói o ``BaseChatModel`` concreto do provider (SDK oficial LangChain).

    Concreto de propósito — **não** um modelo configurável: o deepagents
    (``create_deep_agent`` → ``resolve_model``) só aceita um ``BaseChatModel``
    instanciado (ou uma string de spec). Um ``_ConfigurableModel`` quebra o
    ``apply_provider_profile`` dele (trata o objeto como string e chama
    ``.count(":")``). A troca de modelo por request é feita uma camada acima
    (``agent_factory`` cacheia um grafo por modelo), não por configurable aqui.
    """
    import os

    match provider:
        case "google_genai":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=get_env("GOOGLE_API_KEY"),  # type: ignore[arg-type]
                temperature=temperature,
                timeout=None,
                max_retries=0,
                safety_settings=_gemini_safety_settings(),
            )
        case "openai":
            from backend.llm.openai.chat import VectoraOpenAIChat
            from backend.llm.openai.client import OpenAIClient

            # Cliente nativo, não `ChatOpenAI`: controla o timeout HTTP
            # diretamente (sem o timeout de 120s entre chunks que o SDK
            # aplicava por padrão) e usa a Responses API (sucessora
            # recomendada da Chat Completions desde 2026).
            return VectoraOpenAIChat(
                model=model_name,
                client=OpenAIClient(
                    api_key=get_env("OPENAI_API_KEY"),
                    organization=os.getenv("OPENAI_ORGANIZATION") or None,
                    project=os.getenv("OPENAI_PROJECT") or None,
                ),
                temperature=temperature,
            )
        case "anthropic":
            from langchain_anthropic import ChatAnthropic
            from pydantic import SecretStr

            prompt_cache = os.getenv("ANTHROPIC_PROMPT_CACHE", "true").lower() not in {
                "false",
                "0",
                "no",
            }
            betas = ["prompt-caching-2024-07-31"] if prompt_cache else []
            return ChatAnthropic(
                model_name=model_name,
                api_key=SecretStr(get_env("ANTHROPIC_API_KEY")),
                temperature=temperature,
                betas=betas,
                timeout=None,
                max_retries=0,
            )
        case "cohere":
            from langchain_cohere import ChatCohere
            from pydantic import SecretStr

            api_key = get_env("COHERE_API_KEY")
            if not api_key:
                msg = "COHERE_API_KEY não configurado. Adicione ao seu .env para usar o provider cohere."
                raise ValueError(msg)
            # ChatCohere aceita a key como SecretStr (o SDK do chat resolve
            # internamente); o CohereEmbeddings exige string crua — ver
            # backend/embedding/background.py.
            return ChatCohere(
                cohere_api_key=SecretStr(api_key),
                model=model_name,
            )
        case "ollama":
            from backend.llm.ollama.chat import VectoraOllamaChat
            from backend.llm.ollama.client import OllamaClient

            # Cliente nativo, não `init_chat_model`: o `/api/chat` expõe
            # `message.thinking` em campo próprio, `images` por mensagem
            # (vision) e os contadores de token — a camada LangChain esconde
            # os três.
            return VectoraOllamaChat(
                model=model_name,
                client=OllamaClient(
                    base_url=_get_env_with_default(
                        "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
                    ),
                    api_key=os.getenv("OLLAMA_API_KEY", ""),
                ),
                temperature=temperature,
            )
        case "openrouter":
            from backend.llm.openrouter.chat import VectoraOpenRouterChat
            from backend.llm.openrouter.client import OpenRouterClient

            api_key = get_env("OPENROUTER_API_KEY")
            if not api_key:
                msg = "OPENROUTER_API_KEY não configurado. Adicione ao seu .env para usar o provider openrouter."
                raise ValueError(msg)
            # Cliente nativo, não `ChatOpenAI` com base_url trocado: a API é
            # OpenAI-compatível, mas o cliente da OpenAI descarta `usage.cost`,
            # o bloco `provider` de roteamento e o `reasoning` do delta. Ids de
            # modelo usam "/" (ex.: "openai/gpt-4o"), nunca colidem com o split
            # por ":" de model_id em load_llm().
            return VectoraOpenRouterChat(
                model=model_name,
                client=OpenRouterClient(api_key=api_key),
                temperature=temperature,
            )
        case "nine_router":
            from langchain_openai import ChatOpenAI
            from pydantic import SecretStr

            from backend.settings import settings

            base_url = settings.nine_router_base_url
            api_key = settings.nine_router_api_key
            if not base_url or not api_key:
                msg = (
                    "9Router não configurado. Defina nine_router_base_url e "
                    "nine_router_api_key nas Settings (Environment Router) "
                    "para usar o provider nine_router."
                )
                raise ValueError(msg)
            # ChatOpenAI comum, não um client nativo: o 9Router já fala o
            # protocolo OpenAI completo (chat/completions, streaming, tool
            # calling) e não expõe nada além disso (sem usage.cost/provider
            # routing/endpoints próprios como o OpenRouter) — integração
            # leve por design, não uma dependência nativa absorvida.
            return ChatOpenAI(
                model=model_name,
                base_url=base_url,
                api_key=SecretStr(api_key),
                temperature=temperature,
            )
        case _:
            msg = (
                f"Provider de LLM desconhecido: {provider!r}. Suportados: "
                "google_genai, openai, anthropic, cohere, ollama, openrouter, "
                "nine_router"
            )
            raise ValueError(msg)


def load_llm(model_id: str = "") -> BaseLanguageModel:
    """Carrega o LLM de acordo com as configurações de ambiente.

    ``model_id`` (opcional, formato ``"provider:model"``) sobrepõe o
    provider/modelo padrão — usado pela troca de modelo por request (o
    ``agent_factory`` cacheia um grafo por ``model_id``). Vazio = padrão de
    env/settings.

    A precedência é: variáveis de ambiente > ``~/.vectora/settings.json``
    (runtime_settings) > defaults.

    Provedores suportados (``LLM_PROVIDER``):
        google-genai  — Google Gemini (padrão)
        openai        — OpenAI Chat
        anthropic     — Anthropic Claude, com prompt caching habilitado
        cohere        — Cohere Command
        ollama        — Ollama local

    Variáveis de ambiente:
        LLM_PROVIDER          — provider (google-genai | openai | anthropic |
                                 cohere | ollama)
        GOOGLE_API_KEY        — chave Google Gemini
        GOOGLE_MODEL          — modelo (default: gemini-2.5-flash)
        OPENAI_API_KEY        — chave OpenAI
        OPENAI_MODEL          — modelo (default: gpt-4o)
        ANTHROPIC_API_KEY     — chave Anthropic
        ANTHROPIC_MODEL       — modelo (default: claude-opus-4-1)
        ANTHROPIC_PROMPT_CACHE — habilita prompt caching (default: true)
        COHERE_API_KEY        — chave Cohere
        COHERE_CHAT_MODEL     — modelo (default: command-a-03-2025)
        OLLAMA_BASE_URL       — URL do servidor Ollama (default:
                                 http://127.0.0.1:11434)
        OLLAMA_MODEL          — modelo (default: gpt-oss:20b)
        LLM_TEMPERATURE       — temperatura (default: 0.2)
    """
    import os

    from backend.workspace.runtime_settings import runtime_settings

    temperature = float(_get_env_with_default("LLM_TEMPERATURE", "0.2"))

    if model_id:
        # Override por request: "provider:model" (o provider já vem normalizado
        # p/ underscore em handlers/chat.py::_build_configurable; aceitamos
        # hífen por robustez). O nome do modelo do request tem precedência.
        prov, _sep, name = model_id.partition(":")
        provider = prov.replace("-", "_")
        spec = _PROVIDER_SPEC.get(provider)
        env_var = spec[0] if spec else ""
        model_name = (
            name
            or (os.getenv(env_var) if env_var else None)
            or (spec[1] if spec else "")
        )
    else:
        provider = (
            os.getenv("LLM_PROVIDER") or runtime_settings.active_provider
        ).replace("-", "_")
        spec = _PROVIDER_SPEC.get(provider)
        if spec is None:
            msg = (
                f"LLM_PROVIDER desconhecido: {provider!r}. Suportados: "
                "google_genai, openai, anthropic, cohere, ollama"
            )
            raise ValueError(msg)
        env_var, default_model = spec
        # active_model só vale se o provider ativo bater com o resolvido.
        active = (
            runtime_settings.active_model
            if runtime_settings.active_provider.replace("-", "_") == provider
            else ""
        )
        model_name = os.getenv(env_var) or active or default_model

    if not model_name and provider == "nine_router":
        from backend.settings import settings

        model_name = settings.nine_router_default_model or ""

    if not model_name:
        msg = f"Modelo de LLM não resolvido para provider {provider!r}."
        raise ValueError(msg)

    model: BaseLanguageModel = cast(
        "BaseLanguageModel",
        _build_concrete_model(provider, model_name, temperature),
    )

    if not hasattr(model, "bind_tools"):
        msg = "Model must support bind_tools"
        raise TypeError(msg)
    if not hasattr(model, "invoke"):
        msg = "Model must support invoke"
        raise TypeError(msg)
    if not hasattr(model, "with_config"):
        msg = "Model must support with_config"
        raise TypeError(msg)

    return model


@asynccontextmanager
async def async_lifespan() -> AsyncGenerator[None]:
    """Async context manager for application lifecycle.

    Inicia o BackgroundEmbeddingWorker na entrada e para gracefully na saída.
    O worker lê da fila SQLite e escreve embeddings no LanceDB.

    Sem este lifespan, os documentos enfileirados pela tool `embedding` ficam
    em status "pending" indefinidamente — nada os processa.

    Usage:
        async with async_lifespan():
            # Application runs here
            pass
    """
    import logging

    from backend.embedding.background import get_background_worker

    _log = logging.getLogger(__name__)

    worker = await get_background_worker()
    await worker.start()
    _log.info("BackgroundEmbeddingWorker iniciado via async_lifespan")

    try:
        yield
    finally:
        await worker.stop()
        _log.info("BackgroundEmbeddingWorker parado via async_lifespan")
