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


def _session_workspaces_root() -> Path:
    """Pasta base dos workspaces criados automaticamente por sessão."""
    return Path.home() / "Documents" / "vectora"


class WorkspaceRegistry:
    """Singleton que gerencia todos os workspaces do Vectora.

    Persiste em ~/.vectora/workspaces.json. Carregamento lazy — o arquivo
    só é lido na primeira operação que precisar dos dados.
    """

    _instance: ClassVar[WorkspaceRegistry | None] = None

    def __init__(self) -> None:
        self._workspaces: dict[str, Workspace] = {}
        #: workspace ativo por usuário ("local" quando sem auth)
        self._active: dict[str, str] = {}
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
                active = data.get("active")
                if isinstance(active, dict):
                    self._active = {str(k): str(v) for k, v in active.items()}
            except Exception:
                logger.warning("Falha ao carregar workspaces.json", exc_info=True)
        self._loaded = True

    def _save(self) -> None:
        """Persiste workspaces.json."""
        try:
            _WORKSPACES_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "workspaces": [ws.model_dump() for ws in self._workspaces.values()],
                "active": self._active,
            }
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
            # O diretório onde o processo foi iniciado é implicitamente
            # confiável — quem tem shell ali já tem controle total. Pastas
            # adicionadas depois (via UI) exigem confirmação explícita.
            launched_here = resolved == str(Path.cwd().resolve())
            now = datetime.now(UTC).isoformat()
            ws = Workspace(
                id=wid,
                name=name,
                cwd=resolved,
                created_at=now,
                is_git_repo=git_info.get("is_git_repo", False),
                git_remote=git_info.get("git_remote"),
                git_current_branch=git_info.get("git_current_branch"),
                trusted=launched_here,
                trusted_at=now if launched_here else None,
                trusted_by="local" if launched_here else None,
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

    def trust(self, workspace_id: str, user_id: str | None = None) -> bool:
        """Marca um workspace como confiável. Retorna True se encontrado.

        Tools de escrita, terminal e git só executam em workspaces confiáveis.
        """
        self._load()
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False
        ws.trusted = True
        ws.trusted_at = datetime.now(UTC).isoformat()
        ws.trusted_by = user_id
        self._save()
        logger.info("Workspace confiado: %s (%s) by=%s", ws.name, workspace_id, user_id)
        return True

    def is_trusted(self, workspace_id: str) -> bool:
        """True se o workspace existe e foi marcado como confiável."""
        self._load()
        ws = self._workspaces.get(workspace_id)
        return ws is not None and ws.trusted

    def create(
        self,
        path: str,
        *,
        trust: bool = False,
        git_init: bool = False,
        user_id: str | None = None,
    ) -> Workspace:
        """Registra (ou recupera) um workspace para o diretório informado.

        Opcionalmente inicializa um repositório git na pasta e a marca como
        confiável. Re-detecta o estado git após um eventual ``git init``.
        """
        ws = self.get_or_create(path)
        if git_init and not ws.is_git_repo:
            try:
                from vectora.tools.git import detect_git_info, git_init_repo

                git_init_repo(ws.cwd)
                info = detect_git_info(ws.cwd)
                ws.is_git_repo = info.get("is_git_repo", False)
                ws.git_current_branch = info.get("git_current_branch")
                ws.git_remote = info.get("git_remote")
                self._save()
            except Exception:
                logger.warning("git init falhou para %s", ws.cwd, exc_info=True)
        if trust:
            self.trust(ws.id, user_id)
        return self._workspaces[ws.id]

    def get_or_create_session_workspace(
        self, thread_id: str, user_id: str | None = None
    ) -> Workspace:
        """Workspace padrão de uma sessão: ``~/Documents/vectora/<thread_id>``.

        Usado quando o usuário inicia um chat sem escolher uma pasta. A pasta é
        criada sob demanda e marcada como confiável — foi gerada pelo próprio
        Vectora para aquela sessão, então não exige confirmação manual.
        """
        base = _session_workspaces_root() / thread_id
        base.mkdir(parents=True, exist_ok=True)
        return self.create(str(base), trust=True, user_id=user_id)

    def set_active(self, workspace_id: str, user_id: str | None = None) -> bool:
        """Define o workspace ativo do usuário. Retorna True se encontrado."""
        self._load()
        if workspace_id not in self._workspaces:
            return False
        self._active[user_id or "local"] = workspace_id
        self._save()
        return True

    def get_active(self, user_id: str | None = None) -> Workspace | None:
        """Retorna o workspace ativo do usuário, ou None se não houver."""
        self._load()
        wid = self._active.get(user_id or "local")
        if wid is None:
            return None
        return self._workspaces.get(wid)


#: Singleton global — importar este objeto em vez de instanciar WorkspaceRegistry
workspace_registry: WorkspaceRegistry = WorkspaceRegistry.instance()
