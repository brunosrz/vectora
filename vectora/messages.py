"""Tipos de mensagem customizados do Vectora.

ArtifactMetadata — metadado de um artifact gerado automaticamente pelo agent.
Artifacts são saídas estruturadas e reutilizáveis (planos, specs, guias, código
de referência) persistidas em ~/.vectora/artifacts/{session_id}/{slug}.md.

Não são enviados ao LLM — apenas rastreados no State para que o orchestrator
possa saber o que já foi gerado na sessão.
"""

from typing import NotRequired, TypedDict


class ArtifactMetadata(TypedDict, total=False):
    """Metadado de um artifact persistido em disco.

    Campos:
    - title: Título extraído do conteúdo (primeiro # ou primeiras 6 palavras)
    - path: Caminho absoluto do arquivo no disco
    - session_id: ID da sessão que gerou o artifact
    - created_at: ISO 8601 timestamp
    - content_preview: Primeiros 200 chars do conteúdo (para exibição no orchestrator)
    """

    title: str
    path: str
    session_id: str
    created_at: str
    content_preview: NotRequired[str]
