"""Endpoint de classificação — POST /v1/classify.

Recebe texto + lista de labels e retorna a classificação com score de confiança.
Usa ``create_deep_agent(response_format=ClassificationResult)`` com detecção
automática de estratégia (ProviderStrategy ou ToolStrategy).

Exemplo de request:
    POST /v1/classify
    {
        "text": "Meu pedido ainda não chegou, já faz 10 dias!",
        "labels": ["reclamação", "elogio", "dúvida", "sugestão"],
        "multi_label": false
    }

Resposta:
    {"label": "reclamação", "confidence": 0.97, "all_scores": {"reclamação": 0.97, ...}}
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api.middleware.rate_limit import limiter, tier_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas de request/response
# ---------------------------------------------------------------------------


class ClassifyRequest(BaseModel):
    """Payload para classificação de texto."""

    text: str = Field(..., description="Texto a classificar.")
    labels: list[str] = Field(
        ..., min_length=2, description="Lista de labels possíveis."
    )
    multi_label: bool = Field(
        default=False,
        description="True para retornar múltiplos labels aplicáveis.",
    )
    description: str | None = Field(
        default=None,
        description="Contexto adicional para auxiliar a classificação.",
    )


class ClassifyResponse(BaseModel):
    """Resultado da classificação."""

    label: str = Field(..., description="Label mais provável (single-label).")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Score de confiança (0-1)."
    )
    labels: list[str] = Field(
        default_factory=list,
        description="Todos os labels aplicáveis (multi_label=True).",
    )
    reasoning: str | None = Field(
        default=None, description="Justificativa da classificação."
    )
    strategy: str = Field(default="auto")


# ---------------------------------------------------------------------------
# Modelo interno para structured output
# ---------------------------------------------------------------------------


class _SingleClassification(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str | None = None


class _MultiClassification(BaseModel):
    labels: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str | None = None


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


@router.post("/v1/classify", response_model=ClassifyResponse)
@limiter.limit(tier_rate_limit)
async def classify(
    request: Request, classify_request: ClassifyRequest
) -> ClassifyResponse:
    """Classifica texto em uma das labels fornecidas.

    Usa structured output (ProviderStrategy/ToolStrategy) via deepagents
    para garantir que a resposta seja sempre um dos labels válidos.
    """
    from langchain_core.messages import HumanMessage

    from backend.services.utils import load_llm

    response_format = (
        _MultiClassification if classify_request.multi_label else _SingleClassification
    )

    labels_str = "\n".join(f"- {label}" for label in classify_request.labels)
    system_prompt = (
        "Você é um classificador de texto. "
        f"Classifique o texto fornecido em UMA das seguintes categorias:\n{labels_str}\n\n"
        "Escolha a categoria mais adequada e forneça um score de confiança entre 0 e 1. "
        f"{'Pode retornar múltiplas categorias se aplicável.' if classify_request.multi_label else 'Retorne apenas UMA categoria.'}"
    )
    if classify_request.description:
        system_prompt += f"\n\nContexto adicional: {classify_request.description}"

    try:
        from typing import cast as _cast

        from deepagents import create_deep_agent
        from langchain_core.language_models.chat_models import BaseChatModel

        llm = _cast("BaseChatModel", load_llm())

        agent = create_deep_agent(
            llm,
            tools=[],
            system_prompt=system_prompt,
            response_format=response_format,
        )

        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=classify_request.text)]},
            config={"configurable": {}},
        )

        output = result.get("structured_response") or result.get("messages", [{}])[-1]
        if isinstance(output, _SingleClassification):
            return ClassifyResponse(
                label=_validate_label(output.label, classify_request.labels),
                confidence=output.confidence,
                reasoning=output.reasoning,
                strategy="auto",
            )
        if isinstance(output, _MultiClassification):
            valid_labels = [
                lbl for lbl in output.labels if lbl in classify_request.labels
            ]
            primary = valid_labels[0] if valid_labels else classify_request.labels[0]
            return ClassifyResponse(
                label=primary,
                confidence=output.confidence,
                labels=valid_labels,
                reasoning=output.reasoning,
                strategy="auto",
            )
        # Fallback: parse from dict/string
        data: dict[str, Any] = output if isinstance(output, dict) else {}
        return ClassifyResponse(
            label=_validate_label(
                str(data.get("label", classify_request.labels[0])),
                classify_request.labels,
            ),
            confidence=float(data.get("confidence", 0.5)),
            reasoning=data.get("reasoning"),
            strategy="auto",
        )

    except Exception as exc:
        logger.exception("classify: falha na classificação")
        raise HTTPException(
            status_code=500, detail=f"Erro na classificação: {exc}"
        ) from exc


def _validate_label(label: str, valid_labels: list[str]) -> str:
    """Garante que o label retornado é um dos válidos (case-insensitive fallback)."""
    if label in valid_labels:
        return label
    label_lower = label.lower()
    for valid in valid_labels:
        if valid.lower() == label_lower:
            return valid
    return valid_labels[0]
