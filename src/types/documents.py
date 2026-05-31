from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Document(BaseModel):
    """Estrutura de documento recuperado do RAG (Pydantic)."""

    page_content: str = Field(description="Conteúdo do documento.")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadados associados."
    )
    relevance_score: float | None = Field(
        default=None, description="Score de relevância do RAG."
    )

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class ArtifactMetadata(BaseModel):
    """Metadado de um artifact persistido em disco (Pydantic)."""

    title: str = Field(description="Título do artifact.")
    path: str = Field(description="Caminho absoluto do arquivo no disco.")
    session_id: str = Field(description="ID da sessão que gerou o artifact.")
    created_at: str = Field(description="Timestamp ISO 8601 de criação.")
    content_preview: str | None = Field(
        default=None, description="Preview dos primeiros 200 caracteres."
    )

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)
