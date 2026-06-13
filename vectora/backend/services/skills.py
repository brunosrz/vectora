"""Registry de skills por usuário — Bloco S8.

Cada usuário tem uma pasta ``~/.vectora/skills/<user_id>/`` com:

- ``index.json`` — lista das skills instaladas (metadados).
- ``<skill_id>/`` — uma subpasta por skill, contendo o ``SKILL.md`` extraído
  + corpo (recursos, scripts, etc.).

Fontes suportadas:

- **git URL** (``https://...`` ou ``git@...``): clone shallow via ``git`` CLI.
- **path local** (absoluto, na máquina do servidor): cópia recursiva.

Validação: a raiz da skill deve ter ``SKILL.md`` com frontmatter declarando
``name`` e ``description``. Sem isso, a instalação é rejeitada.

O resolver do agente (``graph`` no Bloco U) consulta
``list_skill_paths(user_id)`` para montar o ``skills=[...]`` do Deep Agent.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess  # nosec B404 — git clone controlado, sem shell=True
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from backend.types.skill import Skill

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_KV_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+?)\s*$")

#: Versão por usuário — bumpada em add/remove para invalidar caches downstream
#: (resolver de skills do agent_factory).
_versions: dict[str, int] = {}


def skills_version(user_id: str) -> int:
    """Versão atual do conjunto de skills do usuário."""
    return _versions.get(user_id, 0)


def _bump_version(user_id: str) -> None:
    _versions[user_id] = _versions.get(user_id, 0) + 1


# ---------------------------------------------------------------------------
# Layout em disco
# ---------------------------------------------------------------------------


def _skills_dir(user_id: str) -> Path:
    safe = user_id.replace("/", "_").replace("\\", "_") or "local"
    return Path.home() / ".vectora" / "skills" / safe


def _index_file(user_id: str) -> Path:
    return _skills_dir(user_id) / "index.json"


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip().lower())
    return s.strip("-") or "skill"


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


def _load_index(user_id: str) -> list[Skill]:
    path = _index_file(user_id)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("skills: index corrompido para %s", user_id)
        return []
    out: list[Skill] = []
    for item in raw.get("skills", []):
        try:
            out.append(Skill(**item))
        except Exception:
            logger.debug("skills: entry inválida ignorada: %s", item)
    return out


def _save_index(user_id: str, skills: list[Skill]) -> None:
    path = _index_file(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"skills": [s.model_dump() for s in skills]}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Frontmatter parsing (subset de YAML — chave: valor por linha)
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Lê o frontmatter YAML do SKILL.md.

    Implementa apenas o subset ``key: value`` por linha (suficiente para
    ``name``/``description``). Valores entre aspas são desempacotados.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    out: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        kv = _KV_RE.match(line)
        if not kv:
            continue
        key, value = kv.group(1), kv.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        out[key] = value
    return out


def _read_skill_metadata(skill_root: Path) -> tuple[str, str]:
    """Lê ``name`` e ``description`` do ``SKILL.md`` da pasta.

    Falha → ``ValueError`` com mensagem útil para o handler.
    """
    md = skill_root / "SKILL.md"
    if not md.is_file():
        raise ValueError("SKILL.md ausente na raiz da skill.")
    try:
        text = md.read_text(encoding="utf-8")
    except Exception as exc:
        raise ValueError(f"Falha ao ler SKILL.md: {exc}") from exc
    fm = _parse_frontmatter(text)
    name = fm.get("name", "").strip()
    description = fm.get("description", "").strip()
    if not name:
        raise ValueError("Frontmatter do SKILL.md não declara 'name'.")
    if not description:
        raise ValueError("Frontmatter do SKILL.md não declara 'description'.")
    return name, description


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def list_skills(user_id: str) -> list[Skill]:
    """Lista as skills instaladas para o usuário."""
    return _load_index(user_id)


def list_skill_paths(user_id: str) -> list[Path]:
    """Paths absolutos das skills instaladas — consumido pelo agent_factory."""
    return [Path(s.path) for s in _load_index(user_id) if Path(s.path).is_dir()]


def _is_git_url(source: str) -> bool:
    return source.startswith(("http://", "https://", "git@", "git://", "ssh://"))


class InstallSkillRequest(BaseModel):
    source: str
    """URL git ou path absoluto."""


def install_skill(user_id: str, source: str) -> Skill:
    """Instala uma skill a partir de URL git ou path local.

    - URL git: ``git clone --depth 1`` em diretório temporário, depois move.
    - Path local: cópia recursiva.

    A pasta de destino é o slug do ``name`` do frontmatter — se já existir uma
    skill com o mesmo slug, a operação é rejeitada (use remove + install).
    """
    source = source.strip()
    if not source:
        raise ValueError("source vazio.")

    base = _skills_dir(user_id)
    base.mkdir(parents=True, exist_ok=True)

    # Pasta de staging: clonamos / copiamos em <base>/.staging antes de
    # mover para o slug final (que só conhecemos após ler o SKILL.md).
    staging = base / ".staging"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)

    try:
        if _is_git_url(source):
            # `shutil.which("git")` devolve path absoluto — boot do binário
            # Nuitka inicializa com PATH minimizado, sem isso o spawn falha.
            git_exe = shutil.which("git")
            if git_exe is None:
                raise ValueError(
                    "git não encontrado no PATH. Instale o git para usar "
                    "URLs como fonte de skills."
                )
            try:
                # `source` é prefix-validado por `_is_git_url`; `staging` vem
                # de Path interno (não-usuário). `--` impede source = "-X".
                subprocess.run(  # noqa: S603  # nosec B603
                    [
                        git_exe,
                        "clone",
                        "--depth",
                        "1",
                        "--",
                        source,
                        str(staging),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=60,
                )
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr.decode("utf-8", errors="replace")
                raise ValueError(f"git clone falhou: {stderr}") from exc
            except FileNotFoundError as exc:
                raise ValueError(
                    "git CLI não encontrado — instale git para usar URLs."
                ) from exc
            shutil.rmtree(staging / ".git", ignore_errors=True)
        else:
            src = Path(source).expanduser().resolve()
            if not src.is_dir():
                raise ValueError(f"Path local não é uma pasta: {src}")
            shutil.copytree(src, staging)

        name, description = _read_skill_metadata(staging)
        skill_id = _slugify(name)
        target = base / skill_id
        if target.exists():
            raise ValueError(
                f"Skill '{skill_id}' já instalada — remova antes de reinstalar."
            )
        shutil.move(str(staging), str(target))
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    skill = Skill(
        id=skill_id,
        name=name,
        description=description,
        source=source,
        path=str(target),
        installed_at=datetime.now(UTC).isoformat(),
        installed_by=user_id,
    )
    skills = [s for s in _load_index(user_id) if s.id != skill_id]
    skills.append(skill)
    _save_index(user_id, skills)
    _bump_version(user_id)
    return skill


def remove_skill(user_id: str, skill_id: str) -> bool:
    """Remove uma skill instalada. Retorna True se existia."""
    skills = _load_index(user_id)
    target = next((s for s in skills if s.id == skill_id), None)
    if target is None:
        return False
    p = Path(target.path)
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=True)
    _save_index(user_id, [s for s in skills if s.id != skill_id])
    _bump_version(user_id)
    return True


def verify_skill(user_id: str, skill_id: str) -> dict:
    """Revalida o ``SKILL.md`` — útil quando o usuário editou a skill no disco."""
    target = next((s for s in _load_index(user_id) if s.id == skill_id), None)
    if target is None:
        return {"ok": False, "error": "skill não encontrada"}
    root = Path(target.path)
    if not root.is_dir():
        return {"ok": False, "error": "pasta da skill ausente"}
    try:
        name, description = _read_skill_metadata(root)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    # Atualiza name/description se mudaram.
    if name != target.name or description != target.description:
        skills = _load_index(user_id)
        for i, s in enumerate(skills):
            if s.id == skill_id:
                skills[i] = target.model_copy(
                    update={"name": name, "description": description}
                )
                break
        _save_index(user_id, skills)
        _bump_version(user_id)
    return {"ok": True, "name": name, "description": description}
