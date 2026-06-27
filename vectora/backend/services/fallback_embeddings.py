"""FallbackEmbeddings — embeddings com fallback automático de provider por quota.

Envolve um provider primário (Cohere) e um secundário (VoyageAI). Em erro de
quota (429) no primário, troca para o secundário, registra a troca em
``provider_fallback.record_switch`` e — quando há um callback manager ativo (RAG
disparado dentro do grafo do chat) — emite ``model_switched`` para a UI avisar.

Indexação em background não tem callback manager: o ``_emit_switch`` é defensivo
(no-op), mas a troca ainda ocorre e é registrada/logada.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


class FallbackEmbeddings(Embeddings):
    """Embeddings que caem do primário para o secundário em quota esgotada."""

    def __init__(
        self,
        primary: Embeddings,
        secondary: Embeddings,
        *,
        primary_id: str,
        secondary_id: str,
    ) -> None:
        self.primary = primary
        self.secondary = secondary
        self.primary_id = primary_id
        self.secondary_id = secondary_id

    # -- sync -------------------------------------------------------------------

    def _run(self, method: str, *args: Any) -> Any:
        from backend.services.provider_fallback import is_quota_error, record_switch

        try:
            return getattr(self.primary, method)(*args)
        except Exception as exc:
            if not is_quota_error(exc):
                raise
            record_switch(self.primary_id, self.secondary_id)
            logger.warning(
                "embeddings provider switch por quota",
                extra={"from": self.primary_id, "to": self.secondary_id},
            )
            return getattr(self.secondary, method)(*args)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._run("embed_documents", texts)

    def embed_query(self, text: str) -> list[float]:
        return self._run("embed_query", text)

    # -- async ------------------------------------------------------------------

    async def _arun(self, method: str, *args: Any) -> Any:
        from backend.services.fallback_chat_model import _emit_switch
        from backend.services.provider_fallback import is_quota_error, record_switch

        try:
            return await getattr(self.primary, method)(*args)
        except Exception as exc:
            if not is_quota_error(exc):
                raise
            record_switch(self.primary_id, self.secondary_id)
            await _emit_switch(self.primary_id, self.secondary_id)
            logger.warning(
                "embeddings provider switch por quota (async)",
                extra={"from": self.primary_id, "to": self.secondary_id},
            )
            return await getattr(self.secondary, method)(*args)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._arun("aembed_documents", texts)

    async def aembed_query(self, text: str) -> list[float]:
        return await self._arun("aembed_query", text)
