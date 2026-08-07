"""Services Layer: Domain-specific business logic without UI dependencies.

Each service encapsulates one responsibility domain and can be tested in isolation.
All services depend only on Settings and standard library/third-party packages.

Services:
- TelemetryService: Logging and audit trails
- Security (module): Security validation utilities (is_safe_* functions)

Nota: Embeddings são gerenciados por BackgroundEmbeddingWorker (services/background.py),
iniciado via async_lifespan() em services/utils.py. Não há mais EmbeddingService aqui.
"""

from __future__ import annotations

from backend.services.telemetry import TelemetryService

__all__ = [
    "TelemetryService",
]
