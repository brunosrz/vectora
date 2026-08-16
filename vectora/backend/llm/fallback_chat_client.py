"""``FallbackChatClient`` — chat nativo com fallback automático de provider
por quota, implementa o Protocol ``ChatClient`` (``backend/llm/base.py``).
Fecha os 5 chat clients (openai/anthropic/google_genai/ollama/openrouter)
num único ponto de entrada com fallback.

Substitui ``backend/llm/fallback_chat_model.py`` (``FallbackChatModel``,
subclasse de ``BaseChatModel``). A troca de mecanismo elimina o hack de
``RunnableBinding``/``_unwrap_binding`` que existia só pra contornar
``bind_tools()`` — aqui ``tools=`` já é parâmetro explícito de
``astream``/``agenerate``, cada candidato recebe as mesmas tools sem
precisar de bind prévio. `adispatch_custom_event` (evento `model_switched`
via callback manager do LangGraph) vira um callback direto
(`on_model_switch`), passado pelo loop de conversa nativo em vez de
descoberto via contexto ambiente.

Arquivo separado dos 5 `chat_client.py` de provider por natureza — não é
mais um cliente de provider, é o orquestrador entre eles. Coexiste com
`fallback_chat_model.py` até o loop de conversa nativo existir e cortar o
dispatch pro motor nativo.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING

from backend.llm.provider_fallback import (
    QuotaExhaustedError,
    get_fallback_chain,
    is_provider_incompatible_error,
    is_quota_error,
    is_transient_error,
    record_switch,
)

if TYPE_CHECKING:
    from backend.llm.base import ChatClient
    from backend.tools.registry import ToolSpec
    from backend.vtypes.message import VMessage, VMessageChunk

logger = logging.getLogger(__name__)

OnModelSwitch = Callable[[str, str], Awaitable[None]]


def _has_images(messages: list[VMessage]) -> bool:
    return any(b.kind == "image_url" for m in messages for b in m.content)


def _candidates(primary_model_id: str, *, has_images: bool) -> list[str]:
    from backend.settings import VISION_CAPABLE_PROVIDERS, find_provider_for_model

    all_candidates = [primary_model_id, *get_fallback_chain(primary_model_id)]
    if not has_images:
        return all_candidates
    return [
        mid
        for mid in all_candidates
        if find_provider_for_model(mid) in VISION_CAPABLE_PROVIDERS
    ]


def load_chat_client(model_id: str) -> ChatClient:  # noqa: PLR0911
    """Resolve `"provider:model"` pro chat client nativo do provider.

    Espelha `backend/services/utils.py::_build_concrete_model`, mas devolve
    um `ChatClient` (Protocol nativo) em vez de `BaseChatModel`.
    """
    import os

    from backend.services.env import get_env

    provider, _sep, model_name = model_id.partition(":")
    provider = provider.replace("-", "_")

    match provider:
        case "openai":
            from backend.llm.openai.chat_client import OpenAIChatClient
            from backend.llm.openai.client import OpenAIClient

            return OpenAIChatClient(
                model=model_name,
                client=OpenAIClient(
                    api_key=get_env("OPENAI_API_KEY"),
                    organization=os.getenv("OPENAI_ORGANIZATION") or None,
                    project=os.getenv("OPENAI_PROJECT") or None,
                ),
            )
        case "anthropic":
            from backend.llm.anthropic.chat_client import AnthropicChatClient
            from backend.llm.anthropic.client import AnthropicClient

            return AnthropicChatClient(
                model=model_name,
                client=AnthropicClient(api_key=get_env("ANTHROPIC_API_KEY")),
            )
        case "cohere":
            from backend.llm.cohere.chat_client import CohereChatClient
            from backend.llm.cohere.client import CohereClient

            return CohereChatClient(
                model=model_name,
                client=CohereClient(api_key=get_env("COHERE_API_KEY")),
            )
        case "google_genai":
            from backend.llm.google.chat_client import GoogleChatClient
            from backend.llm.google.client import GoogleGenAIClient

            return GoogleChatClient(
                model=model_name,
                client=GoogleGenAIClient(api_key=get_env("GOOGLE_API_KEY")),
            )
        case "ollama":
            from backend.llm.ollama.chat_client import OllamaChatClient
            from backend.llm.ollama.client import OllamaClient

            return OllamaChatClient(
                model=model_name,
                client=OllamaClient(
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
                    api_key=os.getenv("OLLAMA_API_KEY", ""),
                ),
            )
        case "openrouter":
            from backend.llm.openrouter.chat_client import OpenRouterChatClient
            from backend.llm.openrouter.client import OpenRouterClient

            api_key = get_env("OPENROUTER_API_KEY")
            if not api_key:
                msg = (
                    "OPENROUTER_API_KEY não configurado. Adicione ao seu .env "
                    "para usar o provider openrouter."
                )
                raise ValueError(msg)
            return OpenRouterChatClient(
                model=model_name, client=OpenRouterClient(api_key=api_key)
            )
        case "nine_router":
            from backend.llm.openrouter.chat_client import OpenRouterChatClient
            from backend.llm.openrouter.client import OpenRouterClient
            from backend.settings import settings

            # Reusa o client do OpenRouter com base_url trocada: o 9Router
            # fala o mesmo protocolo OpenAI-compatível — mesma decisão já
            # tomada em _build_concrete_model.
            base_url = settings.nine_router_base_url
            api_key = settings.nine_router_api_key
            if not base_url or not api_key:
                msg = (
                    "9Router não configurado. Defina nine_router_base_url e "
                    "nine_router_api_key nas Settings (Environment Router) "
                    "para usar o provider nine_router."
                )
                raise ValueError(msg)
            return OpenRouterChatClient(
                model=model_name,
                client=OpenRouterClient(api_key=api_key, base_url=base_url),
            )
        case _:
            msg = (
                f"Provider de LLM nativo desconhecido: {provider!r}. Suportados: "
                "openai, anthropic, google_genai, cohere, ollama, openrouter, "
                "nine_router."
            )
            raise ValueError(msg)


async def _emit_switch(
    on_model_switch: OnModelSwitch | None, from_model: str, to_model: str
) -> None:
    if on_model_switch is None:
        return
    try:
        await on_model_switch(from_model, to_model)
    except Exception:
        logger.debug("fallback_chat_client: on_model_switch falhou", exc_info=True)


def _deve_tentar_proximo(exc: BaseException, *, indice: int) -> bool:
    """Troca em quota, falha transiente (timeout/conexão) ou incompatibilidade
    permanente de provider — ou qualquer erro depois do primeiro candidato
    (já estamos em fallback, não vale insistir no mesmo tipo de erro sem
    tentar o resto da cadeia)."""
    return (
        is_quota_error(exc)
        or is_transient_error(exc)
        or is_provider_incompatible_error(exc)
        or indice > 0
    )


class FallbackChatClient:
    """``ChatClient`` nativo com fallback automático de provider por quota
    (ver docstring do módulo)."""

    def __init__(
        self,
        primary_model_id: str,
        *,
        on_model_switch: OnModelSwitch | None = None,
    ) -> None:
        self.primary_model_id = primary_model_id
        self.on_model_switch = on_model_switch

    def _candidate_ids(self, messages: list[VMessage]) -> list[str]:
        candidatos = _candidates(
            self.primary_model_id, has_images=_has_images(messages)
        )
        if not candidatos:
            msg = "Nenhum provider de LLM disponível ou configurado para este modelo."
            raise QuotaExhaustedError(msg, model_id=self.primary_model_id)
        return candidatos

    async def agenerate(
        self,
        messages: list[VMessage],
        *,
        tools: list[ToolSpec] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> VMessage:
        candidatos = self._candidate_ids(messages)

        last_exc: BaseException | None = None
        for i, mid in enumerate(candidatos):
            try:
                client = load_chat_client(mid)
                return await client.agenerate(
                    messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                if not _deve_tentar_proximo(exc, indice=i):
                    raise
                last_exc = exc
                if i + 1 < len(candidatos):
                    record_switch(mid, candidatos[i + 1])
                    await _emit_switch(self.on_model_switch, mid, candidatos[i + 1])

        last_mid = candidatos[-1] if candidatos else self.primary_model_id
        msg = f"Todos os providers esgotaram a quota (último: {last_mid})."
        raise QuotaExhaustedError(msg, model_id=last_mid) from last_exc

    async def astream(
        self,
        messages: list[VMessage],
        *,
        tools: list[ToolSpec] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[VMessageChunk]:
        candidatos = self._candidate_ids(messages)

        last_exc: BaseException | None = None
        for i, mid in enumerate(candidatos):
            streamed = False
            try:
                client = load_chat_client(mid)
                async for chunk in client.astream(
                    messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    streamed = True
                    yield chunk
                return
            except Exception as exc:
                # Nunca troca de provider depois de já ter streamado chunks
                # (resposta parcial) — mesmo invariante do adapter antigo.
                if not _deve_tentar_proximo(exc, indice=i) or streamed:
                    raise
                last_exc = exc
                if i + 1 < len(candidatos):
                    record_switch(mid, candidatos[i + 1])
                    await _emit_switch(self.on_model_switch, mid, candidatos[i + 1])

        last_mid = candidatos[-1] if candidatos else self.primary_model_id
        msg = f"Todos os providers esgotaram a quota (último: {last_mid})."
        raise QuotaExhaustedError(msg, model_id=last_mid) from last_exc
