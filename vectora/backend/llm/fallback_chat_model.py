"""FallbackChatModel — LLM do chat com fallback automático de provider por quota.

Envolve um modelo primário (``model_id``) e, em erro de quota (429) **antes do
primeiro token**, troca para o próximo provider da cadeia (``fallback_order``),
recarregando o LLM via ``load_llm`` e registrando a troca em
``provider_fallback.record_switch`` (o handler de chat drena e notifica a UI).

É um ``BaseChatModel`` (não ``with_fallbacks``) porque o deep-agent chama
``bind_tools`` no modelo — ``RunnableWithFallbacks`` não expõe ``bind_tools``.

Invariante de streaming: ``_astream`` delega DIRETO no
``_astream``/``_agenerate`` internos do provider (desembrulhando o
``RunnableBinding`` do bind_tools), nunca no ``.astream()``/``.ainvoke()``
públicos. O caminho público instrumenta um SEGUNDO run "chat_model" aninhado
no ``astream_events`` — cada token sai duas vezes no SSE (um do wrapper, um do
provider), com ``message_break`` espúrio entre eles (o nó emissor alterna),
que o frontend renderiza como token duplicado em linha própria. O run único é
o deste wrapper: o ``_agenerate_with_cache`` da base dispara ``on_llm_new_token``
por chunk re-yieldado, exatamente uma vez.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_core.runnables import RunnableBinding


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


def _unwrap_binding(inner: Any) -> tuple[Any, dict[str, Any]]:
    """Desembrulha ``RunnableBinding`` aninhados até o BaseChatModel concreto.

    ``bind_tools`` devolve ``RunnableBinding(bound=<modelo>, kwargs={tools...})``;
    os kwargs de bind precisam voltar como kwargs de chamada quando invocamos o
    ``_astream``/``_agenerate`` internos diretamente.
    """
    bind_kwargs: dict[str, Any] = {}
    while isinstance(inner, RunnableBinding):
        bind_kwargs = {**inner.kwargs, **bind_kwargs}
        inner = inner.bound
    return inner, bind_kwargs


def _is_reasoning_block(block: Any) -> bool:
    return isinstance(block, dict) and block.get("type") == "reasoning"


def _text_of(block: Any) -> str | None:
    """Texto do bloco se for um bloco ``text``; None caso contrário."""
    if isinstance(block, dict) and block.get("type") == "text":
        return str(block.get("text", ""))
    return None


def _strip_reasoning_blocks(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Sanitiza o content de AIMessages do histórico antes do replay.

    Modelos com raciocínio (ex.: Cohere Command A+) devolvem o content como
    lista de blocos incluindo ``{"type": "reasoning", ...}`` e blocos ``text``
    com metadados de streaming (``index``). O checkpointer persiste a mensagem
    como veio; no turno seguinte, o replay quebra o provider de dois jeitos:

    - ``reasoning`` não existe no schema do ``langchain_cohere``
      (ValidationError em ``AssistantChatMessageV2``);
    - o campo extra ``index`` dos blocos ``text`` vaza pro request e a API da
      Cohere rejeita com 422 ``unknown field: parameter 'index'``.

    Regras: remove blocos ``reasoning`` (raciocínio de turnos passados não
    precisa voltar); se o que sobra é só texto, colapsa pra string simples
    (formato que todo provider aceita sem risco de campos extras); se sobra
    mistura (tool_use/thinking + text), mantém a lista mas reduz os blocos
    ``text`` a ``{"type", "text"}``. Blocos ``thinking`` (Anthropic, exigidos
    no replay de tool-use) ficam intactos.
    """
    out: list[BaseMessage] = []
    for msg in messages:
        sanitized = msg
        if isinstance(msg, AIMessage) and isinstance(msg.content, list):
            kept = [b for b in msg.content if not _is_reasoning_block(b)]
            texts = [_text_of(b) for b in kept]
            if all(t is not None for t in texts):
                new_content: str | list[Any] = "".join(t or "" for t in texts)
            else:
                new_content = [
                    b if _text_of(b) is None else {"type": "text", "text": _text_of(b)}
                    for b in kept
                ]
            if new_content != msg.content:
                sanitized = msg.model_copy(update={"content": new_content})
        out.append(sanitized)
    return out


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
        from backend.llm.provider_fallback import get_fallback_chain

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
        from backend.llm.provider_fallback import (
            QuotaExhaustedError,
            is_quota_error,
            is_transient_error,
            record_switch,
        )

        messages = _strip_reasoning_blocks(messages)
        candidates = self._candidates()
        last_exc: BaseException | None = None
        for i, mid in enumerate(candidates):
            model, bind_kwargs = _unwrap_binding(self._inner(mid))
            streamed = False
            try:
                # _astream interno direto, com run_manager=None: o provider só
                # yielda chunks (implementações internas não emitem callbacks
                # sem run_manager) e o run/eventos ficam exclusivamente por
                # conta deste wrapper — um token = um on_chat_model_stream.
                async for chunk in model._astream(
                    messages, stop=stop, **{**bind_kwargs, **kwargs}
                ):
                    streamed = True
                    yield chunk
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
        from backend.llm.provider_fallback import (
            QuotaExhaustedError,
            is_quota_error,
            is_transient_error,
            record_switch,
        )

        messages = _strip_reasoning_blocks(messages)
        candidates = self._candidates()
        last_exc: BaseException | None = None
        for i, mid in enumerate(candidates):
            model, bind_kwargs = _unwrap_binding(self._inner(mid))
            try:
                # Mesmo invariante do _astream: _agenerate interno direto, sem
                # segundo run público instrumentado.
                return await model._agenerate(
                    messages, stop=stop, **{**bind_kwargs, **kwargs}
                )
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
        messages = _strip_reasoning_blocks(messages)
        model, bind_kwargs = _unwrap_binding(self._inner(self.primary_model_id))
        return model._generate(messages, stop=stop, **{**bind_kwargs, **kwargs})
