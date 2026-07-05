"""Handlers REST API v1 — endpoints Vectora-nativos de structured output.

Cada submódulo expõe um `router: APIRouter` montado em
`backend.api.server.create_app()`: `extract` (extração estruturada),
`classify` (classificação) e `jobs` (consulta de status assíncrono).
"""

from __future__ import annotations

from backend.api.handlers.v1.classify import router as classify_router
from backend.api.handlers.v1.extract import router as extract_router
from backend.api.handlers.v1.jobs import router as jobs_router

__all__ = ["classify_router", "extract_router", "jobs_router"]
