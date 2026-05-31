from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Workspace(BaseModel):
    """Representa um workspace — projeto isolado por diretório (Pydantic)."""

    id: str = Field(description="ID do workspace (sha256[:8] do cwd).")
    name: str = Field(description="Nome do workspace/projeto.")
    cwd: str = Field(description="Diretório de trabalho correspondente.")
    created_at: str = Field(description="Timestamp ISO 8601 de criação.")
    bucket_names: list[str] = Field(
        default_factory=list, description="Buckets ativos associados."
    )
    manifest_version: int = Field(default=0, description="Versão atual do manifest.")

    # G7 — campos git (preenchidos por detect_git_info ao criar o workspace)
    is_git_repo: bool = Field(
        default=False, description="True se o cwd é um repositório git."
    )
    git_remote: str | None = Field(
        default=None, description="URL do primeiro remote (origin)."
    )
    git_current_branch: str | None = Field(
        default=None, description="Branch ativa no momento do registro."
    )
    git_default_branch: str | None = Field(
        default=None, description="Branch padrão (main/master)."
    )

    trusted: bool = Field(
        default=False,
        description="True quando o usuário confiou na pasta. Tools de escrita, "
        "terminal e git só executam em workspaces confiáveis.",
    )
    trusted_at: str | None = Field(
        default=None, description="Timestamp ISO 8601 da confirmação de confiança."
    )
    trusted_by: str | None = Field(
        default=None, description="ID do usuário que confiou na pasta."
    )

    def manifest_dir(self) -> Path:
        """Diretório de manifests do workspace."""
        return Path.home() / ".vectora" / "workspaces" / self.id

    def manifest_path(self) -> Path:
        """Caminho do MANIFEST.md principal."""
        return self.manifest_dir() / "MANIFEST.md"

    def bucket_manifest_path(self, bucket: str) -> Path:
        """Caminho do manifest de um bucket específico."""
        return self.manifest_dir() / "buckets" / f"{bucket}.md"

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)
