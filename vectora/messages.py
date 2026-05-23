"""Tipos de mensagem customizados do Vectora.

ArtifactMetadata — metadado de um artifact gerado automaticamente pelo agent.
Artifacts são saídas estruturadas e reutilizáveis (planos, specs, guias, código
de referência) persistidas em ~/.vectora/artifacts/{session_id}/{slug}.md.

Não são enviados ao LLM — apenas rastreados no State para que o orchestrator
possa saber o que já foi gerado na sessão.
"""

from vectora.types.documents import ArtifactMetadata

__all__ = ["ArtifactMetadata"]
