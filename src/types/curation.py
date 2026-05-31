from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WebResultVerdict(BaseModel):
    """Veredito do LLM judge para um único resultado web."""

    index: int = Field(description="Índice do resultado na lista avaliada (base 0).")
    keep: bool = Field(
        description="True se o resultado é relevante e confiável para o projeto."
    )
    reason: str = Field(description="Uma frase curta justificando manter ou descartar.")

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class CurationDecision(BaseModel):
    """Decisão de curadoria do LLM judge para o lote de resultados web."""

    verdicts: list[WebResultVerdict] = Field(
        description="Um veredito por resultado avaliado."
    )

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)
