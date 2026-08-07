"""Interface de vector store — molde direto da ABC `MemoryProvider` do Hermes
Agent (escrita à mão, sem herdar de framework): um contrato pequeno que
`LanceDBBackend` (lite) e `QdrantBackend` (complete) implementam, pra
`tools/rag.py`/`embedding/background.py` pararem de hardcodar LanceDB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class VectorRow:
    """Um documento indexado — shape comum entre LanceDB e Qdrant."""

    id: str
    vector: list[float]
    text: str
    metadata: dict[str, Any]


@dataclass
class VectorHit:
    """Resultado de busca — mesmo shape que `tools/rag.py::vector_search`
    já monta hoje a partir do LanceDB, pra reranking/resposta não mudarem."""

    id: str
    score: float
    content: str
    metadata: dict[str, Any]
    collection: str


class VectorStoreBackend(Protocol):
    """Contrato nativo de storage vetorial — sem LangChain no meio.

    Erros de rede/timeout são responsabilidade de cada implementação tratar
    (nunca deixar subir cru pro tool caller) — mesma defensividade que
    `_search_one_collection`/`_write_to_lancedb` já praticam hoje.
    """

    async def search(
        self, collection: str, query_vector: list[float], limit: int
    ) -> list[VectorHit]:
        """Top-k por similaridade. Coleção ausente devolve lista vazia."""
        ...

    async def upsert(self, collection: str, rows: list[VectorRow]) -> None:
        """Insere/atualiza documentos. Cria a coleção se não existir."""
        ...

    async def list_rows(self, collection: str) -> list[VectorRow]:
        """Todos os documentos da coleção. Coleção ausente devolve `[]`."""
        ...

    async def delete(self, collection: str, ids: list[str]) -> int:
        """Remove por id. Devolve quantos foram de fato removidos."""
        ...

    async def purge(self, collection: str) -> None:
        """Apaga a coleção inteira. Idempotente — coleção ausente não é erro."""
        ...

    async def list_collections(self) -> list[str]:
        """Nomes de todas as coleções existentes. Backend vazio devolve `[]`."""
        ...

    async def count(self, collection: str) -> int | None:
        """Quantidade de documentos na coleção. `None` se não conseguir
        determinar (coleção corrompida/erro transitório) — nunca lança."""
        ...
