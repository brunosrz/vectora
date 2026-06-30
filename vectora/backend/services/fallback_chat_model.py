"""FallbackChatModel — LLM do chat com fallback automático de provider por quota.

Envolve um modelo primário (``model_id``) e, em erro de quota (429) **antes do
primeiro token**, troca para o próximo provider da cadeia (``fallback_order``),
recarregando o LLM via ``load_llm`` e registrando a troca em
``provider_fallback.record_switch`` (o handler de chat drena e notifica a UI).

É um ``BaseChatModel`` (não ``with_fallbacks``) porque o deep-agent chama
``bind_tools`` no modelo — ``RunnableWithFallbacks`` não expõe ``bind_tools``.

Streaming preservado: ``_astream`` apenas re-yielda os ``ChatGenerationChunk`` do
modelo interno; a base ``BaseChatModel.astream`` dispara ``on_llm_new_token`` por
chunk (o que alimenta ``on_chat_model_stream`` consumido pelo handler de chat).
A troca só ocorre se a quota estourar **antes** do primeiro chunk — depois disso
o stream já começou e não dá para reiniciar.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult


async def _emit_switch(from_model: str, to_model: str) -> None:
    """Emite um evento custom ``model_switched`` no stream do grafo.

    Flui pelo ``astream_events`` (como ``on_custom_event``), que o handler de chat
    converte em SSE para o frontend trocar o model selector + mostrar o toast.
    Defensivo: se não houver callback manager ativo, não faz nada.
    """
    try:
        from langchain_core.callbacks.manager import adispatch_custom_event

        await adispatch_custom_event(
            "model_switched", {"from": from_model, "to": to_model}
        )
    except Exception:
        pass


class FallbackChatModel(BaseChatModel):
    """Modelo de chat com fallback de provider por quota (ver módulo)."""

    model_config = {"arbitrary_types_allowed": True}

    primary_model_id: str = ""
    bound_tools: Any = None
    bind_kwargs: dict[str, Any] = {}

    @property
    def _llm_type(self) -> str:
        return "vectora-fallback"

    # -- candidatos / modelo interno --------------------------------------------

    def _candidates(self) -> list[str]:
        from backend.services.provider_fallback import get_fallback_chain

        return [self.primary_model_id, *get_fallback_chain(self.primary_model_id)]

    def _inner(self, model_id: str) -> Any:
        from backend.services.utils import load_llm

        llm = load_llm(model_id)
        if self.bound_tools is not None:
            # load_llm devolve BaseChatModel concreto (tem bind_tools); a base
            # tipada é BaseLanguageModel, daí o ignore.
            llm = llm.bind_tools(  # ty: ignore[unresolved-attribute]
                self.bound_tools, **self.bind_kwargs
            )
        return llm

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> FallbackChatModel:
        """Propaga as tools — cada candidato recebe ``bind_tools`` ao ser usado."""
        return self.__class__(
            primary_model_id=self.primary_model_id,
            bound_tools=list(tools),
            bind_kwargs=kwargs,
        )

    # -- streaming async (caminho principal do chat) ----------------------------

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        from backend.services.provider_fallback import (
            QuotaExhaustedError,
            is_quota_error,
            is_transient_error,
            record_switch,
        )

        candidates = self._candidates()
        last_exc: BaseException | None = None
        for i, mid in enumerate(candidates):
            inner = self._inner(mid)
            streamed = False
            try:
                async for msg_chunk in inner.astream(messages, stop=stop, **kwargs):
                    streamed = True
                    yield ChatGenerationChunk(message=msg_chunk)
                return
            except Exception as exc:
                # Troca em quota ou falha transiente (timeout/conexão), mas
                # nunca depois de já ter streamado chunks (resposta parcial).
                if not (is_quota_error(exc) or is_transient_error(exc)) or streamed:
                    raise
                last_exc = exc
                if i + 1 < len(candidates):
                    record_switch(mid, candidates[i + 1])
                    await _emit_switch(mid, candidates[i + 1])
        raise QuotaExhaustedError(
            f"Todos os providers esgotaram a quota (último: {candidates[-1]}).",
            model_id=candidates[-1],
        ) from last_exc

    # -- geração não-streaming --------------------------------------------------

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        from backend.services.provider_fallback import (
            QuotaExhaustedError,
            is_quota_error,
            is_transient_error,
            record_switch,
        )

        candidates = self._candidates()
        last_exc: BaseException | None = None
        for i, mid in enumerate(candidates):
            inner = self._inner(mid)
            try:
                msg = await inner.ainvoke(messages, stop=stop, **kwargs)
                return ChatResult(generations=[ChatGeneration(message=msg)])
            except Exception as exc:
                if not (is_quota_error(exc) or is_transient_error(exc)):
                    raise
                last_exc = exc
                if i + 1 < len(candidates):
                    record_switch(mid, candidates[i + 1])
        raise QuotaExhaustedError(
            f"Todos os providers esgotaram a quota (último: {candidates[-1]}).",
            model_id=candidates[-1],
        ) from last_exc

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Caminho síncrono (raro no chat) — usa o primário, sem fallback.
        msg = self._inner(self.primary_model_id).invoke(messages, stop=stop, **kwargs)
        return ChatResult(generations=[ChatGeneration(message=msg)])
