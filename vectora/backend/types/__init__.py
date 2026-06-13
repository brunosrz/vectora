# consumidores acessam via `src.types.*` — sem colisão com stdlib
from __future__ import annotations

from backend.types.agents import (
    AgentName,
    CoderResult,
    MemoryEntry,
    OrchestratorDecision,
    ParallelResult,
    SearchResult,
    SubTask,
    UIMetrics,
)
from backend.types.context import VectoraContext, ctx_from_config
from backend.types.curation import CurationDecision, WebResultVerdict
from backend.types.documents import ArtifactMetadata, Document
from backend.types.safe_root import SafeRoot
from backend.types.session import SessionMetadata
from backend.types.workspace import Workspace

__all__ = [
    "AgentName",
    "ArtifactMetadata",
    "CoderResult",
    "CurationDecision",
    "Document",
    "MemoryEntry",
    "OrchestratorDecision",
    "ParallelResult",
    "SafeRoot",
    "SearchResult",
    "SessionMetadata",
    "SubTask",
    "UIMetrics",
    "VectoraContext",
    "WebResultVerdict",
    "Workspace",
    "ctx_from_config",
]
