"""Text Processing Service — Tokenização e Chunking.

Fonte única de verdade para splitting de documentos e contagem de tokens.
Qualquer mudança de estratégia (encoding, chunk_size, overlap) acontece aqui,
não espalhada por tools ou nodes.

Design:
- TextService é um singleton leve: criado uma vez, reutilizado em todo o processo.
- O splitter usa tiktoken (cl100k_base) via langchain-text-splitters — sem
  HuggingFace Hub, sem download em runtime.
- O token_counter usa o mesmo encoding para consistência com o splitter:
  trim_messages() e ingest_docs() falam a mesma língua de tokens.

Usage:
    from vectora.services.text import text_service

    chunks = text_service.split(long_text)
    n_tokens = text_service.count_tokens("hello world")
    trimmed = text_service.count_messages_tokens(messages)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


class TextService:
    """Serviço de tokenização e chunking de documentos.

    Centraliza toda lógica de splitting para que:
    - tools/rag.py (ingestão) e nodes/engine.py (trim_messages) usem
      o MESMO encoding e as mesmas regras de contagem.
    - Mudanças de estratégia (encoding, chunk_size, overlap) ocorram
      em um único lugar — settings.py → TextService.

    Attributes:
        encoding_name: Nome do encoding tiktoken (ex: cl100k_base).
        chunk_size: Tamanho máximo de chunk em tokens.
        chunk_overlap: Sobreposição entre chunks em tokens.
    """

    def __init__(
        self,
        encoding_name: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        self.encoding_name = encoding_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Encoding tiktoken — carregado uma vez, cacheado pelo próprio tiktoken
        self._enc = tiktoken.get_encoding(encoding_name)

        # Splitter configurado com o mesmo encoding para consistência
        self._splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name=encoding_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        logger.debug(
            "TextService initialized",
            extra={
                "encoding": encoding_name,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            },
        )

    # ── Chunking ─────────────────────────────────────────────────────────────

    def split(self, text: str) -> list[str]:
        """Divide texto em chunks respeitando limites de tokens.

        Args:
            text: Texto a dividir.

        Returns:
            Lista de chunks, cada um com no máximo `chunk_size` tokens.
        """
        return self._splitter.split_text(text)

    # ── Token counting ────────────────────────────────────────────────────────

    def count_tokens(self, text: str) -> int:
        """Conta tokens em uma string usando tiktoken.

        Args:
            text: Texto para contar tokens.

        Returns:
            Número de tokens.
        """
        return len(self._enc.encode(text))

    def count_messages_tokens(self, messages: Sequence[BaseMessage]) -> int:
        """Conta tokens em uma lista de mensagens LangChain.

        Usado pelo trim_messages() em nodes/engine.py como token_counter.
        Suporta content como str ou lista de blocos (multimodal).

        Args:
            messages: Lista de BaseMessage (HumanMessage, AIMessage, etc.).

        Returns:
            Total de tokens em todas as mensagens.
        """
        total = 0
        for msg in messages:
            content = msg.content or ""
            if isinstance(content, str):
                total += len(self._enc.encode(content))
            elif isinstance(content, list):
                # Mensagens multimodais: cada bloco pode ter "text"
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        total += len(self._enc.encode(str(block["text"])))
        return total


# ── Singleton ─────────────────────────────────────────────────────────────────
# Criado uma vez na importação do módulo, guiado pelos Settings.
# Importar de outros módulos: `from vectora.services.text import text_service`


def _build() -> TextService:
    from vectora.config.settings import settings

    return TextService(
        encoding_name=settings.tiktoken_encoding,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


text_service: TextService = _build()
