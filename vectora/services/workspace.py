"""WorkspaceRegistry — isolamento por projeto.

Cada diretório de trabalho tem um workspace único, identificado por um
sha256 truncado do caminho absoluto. Metadados ficam em
~/.vectora/workspaces.json e manifests em
~/.vectora/workspaces/<workspace_id>/.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from vectora.types import Workspace

logger = logging.getLogger(__name__)

_WORKSPACES_FILE = Path.home() / ".vectora" / "workspaces.json"


class WorkspaceRegistry:
    """Singleton que gerencia todos os workspaces do Vectora.

    Persiste em ~/.vectora/workspaces.json. Carregamento lazy — o arquivo
    só é lido na primeira operação que precisar dos dados.
    """

    _instance: ClassVar[WorkspaceRegistry | None] = None

    def __init__(self) -> None:
        self._workspaces: dict[str, Workspace] = {}
        self._loaded = False

    @classmethod
    def instance(cls) -> WorkspaceRegistry:
        """Retorna a instância singleton do registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def derive_id(cwd: str) -> str:
        """Deriva workspace_id determinístico a partir do caminho absoluto."""
        normalized = str(Path(cwd).resolve())
        return hashlib.sha256(normalized.encode()).hexdigest()[:8]

    def _load(self) -> None:
        """Carrega workspaces.json (idempotente)."""
        if self._loaded:
            return
        if _WORKSPACES_FILE.exists():
            try:
                data = json.loads(_WORKSPACES_FILE.read_text(encoding="utf-8"))
                for item in data.get("workspaces", []):
                    try:
                        ws = Workspace(**item)
                        self._workspaces[ws.id] = ws
                    except Exception:
                        logger.debug("Workspace inválido ignorado: %s", item)
            except Exception:
                logger.warning("Falha ao carregar workspaces.json", exc_info=True)
        self._loaded = True

    def _save(self) -> None:
        """Persiste workspaces.json."""
        try:
            _WORKSPACES_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {"workspaces": [ws.model_dump() for ws in self._workspaces.values()]}
            _WORKSPACES_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            logger.warning("Falha ao salvar workspaces.json", exc_info=True)

    def get_or_create(self, cwd: str | None = None) -> Workspace:
        """Retorna workspace existente ou cria um novo para o diretório.

        Ao criar, detecta automaticamente se o diretório contém um repositório
        git e preenche os campos is_git_repo, git_remote e git_current_branch.
        """
        self._load()
        resolved = str(Path(cwd).resolve() if cwd else Path.cwd())
        wid = self.derive_id(resolved)
        if wid not in self._workspaces:
            name = Path(resolved).name or "workspace"
            # G7 — auto-detecção de git
            git_info: dict = {}
            try:
                from vectora.tools.git import detect_git_info

                git_info = detect_git_info(resolved)
            except Exception:
                pass
            ws = Workspace(
                id=wid,
                name=name,
                cwd=resolved,
                created_at=datetime.now(UTC).isoformat(),
                is_git_repo=git_info.get("is_git_repo", False),
                git_remote=git_info.get("git_remote"),
                git_current_branch=git_info.get("git_current_branch"),
            )
            self._workspaces[wid] = ws
            self._save()
            logger.info(
                "Workspace criado: %s (%s) git=%s",
                name,
                wid,
                ws.is_git_repo,
            )
        return self._workspaces[wid]

    def get(self, workspace_id: str) -> Workspace | None:
        """Retorna workspace por ID ou None se não existir."""
        self._load()
        return self._workspaces.get(workspace_id)

    def list_all(self) -> list[Workspace]:
        """Lista todos os workspaces registrados."""
        self._load()
        return list(self._workspaces.values())

    def rename(self, workspace_id: str, new_name: str) -> bool:
        """Renomeia um workspace. Retorna True se encontrado."""
        self._load()
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False
        ws.name = new_name
        self._save()
        return True

    def delete(self, workspace_id: str) -> bool:
        """Remove um workspace do registry. Retorna True se existia."""
        self._load()
        if workspace_id not in self._workspaces:
            return False
        del self._workspaces[workspace_id]
        self._save()
        return True

    def bump_version(self, workspace_id: str) -> int:
        """Incrementa manifest_version e persiste. Retorna a nova versão.

        Chamado pelo curator (B4) após reescrever o MANIFEST.md. O orchestrator
        detecta o gap de versão e recarrega o contexto no próximo turno.
        """
        self._load()
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return 0
        ws.manifest_version += 1
        self._save()
        return ws.manifest_version


#: Singleton global — importar este objeto em vez de instanciar WorkspaceRegistry
workspace_registry: WorkspaceRegistry = WorkspaceRegistry.instance()
