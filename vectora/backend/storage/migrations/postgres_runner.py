"""Runner de schema migrations para PostgreSQL (asyncpg).

Mesmo contrato do SQLite runner (runner.py), mas usa asyncpg:
  - params posicionais ($1, $2) em vez de ?
  - execute() suporta múltiplos statements sem executescript()
  - applied_at gravado como TIMESTAMPTZ via now()

Uso:
    async with pool.acquire() as conn:
        runner = PostgresMigrationRunner(conn)
        await runner.upgrade()
        await runner.downgrade("0001")
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CONTROL_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT        PRIMARY KEY,
    name       TEXT        NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    checksum   TEXT        NOT NULL
);
"""

_SECTION_RE = re.compile(r"^--\s*(up|down)\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass
class MigrationFile:
    version: str
    name: str
    path: Path
    up_sql: str
    down_sql: str
    checksum: str


@dataclass
class MigrationStatus:
    version: str
    name: str
    applied: bool
    applied_at: str | None
    drift: bool


def _parse_sql_file(path: Path) -> MigrationFile:
    stem = path.stem
    m = re.match(r"^(\d{4})_(.+)$", stem)
    if not m:
        raise ValueError(
            f"Nome de migration inválido: {path.name!r}. "
            "Esperado: NNNN_<nome>.sql (ex: 0001_sessions.sql)"
        )
    version, name = m.group(1), m.group(2)
    content = path.read_text(encoding="utf-8")
    checksum = hashlib.sha256(content.encode()).hexdigest()

    parts = _SECTION_RE.split(content)
    sections: dict[str, str] = {}
    i = 1
    while i < len(parts) - 1:
        sections[parts[i].strip().lower()] = parts[i + 1]
        i += 2

    return MigrationFile(
        version=version,
        name=name,
        path=path,
        up_sql=sections.get("up", ""),
        down_sql=sections.get("down", ""),
        checksum=checksum,
    )


class PostgresMigrationRunner:
    """Aplica e reverte migrations em uma conexão asyncpg.

    Args:
        conn:           asyncpg.Connection aberta.
        migrations_dir: Diretório com os arquivos ``NNNN_*.sql``.
                        Default: subdiretório ``postgres/`` junto a este arquivo.
    """

    def __init__(
        self,
        conn: Any,
        migrations_dir: str | Path | None = None,
    ) -> None:
        self._conn = conn
        self._dir = (
            Path(migrations_dir)
            if migrations_dir
            else Path(__file__).parent / "postgres"
        )

    async def _ensure_control_table(self) -> None:
        await self._conn.execute(_CONTROL_SCHEMA)

    def _load_files(self) -> list[MigrationFile]:
        files = sorted(
            self._dir.glob("*.sql"),
            key=lambda p: p.stem.split("_")[0],
        )
        result = []
        for f in files:
            try:
                result.append(_parse_sql_file(f))
            except ValueError as exc:
                logger.warning(
                    "storage/migrations/postgres: ignorando arquivo: %s", exc
                )
        return result

    async def _applied(self) -> dict[str, dict[str, str]]:
        await self._ensure_control_table()
        rows = await self._conn.fetch(
            "SELECT version, applied_at::text AS applied_at, checksum "
            "FROM schema_migrations ORDER BY version"
        )
        return {
            r["version"]: {"applied_at": r["applied_at"], "checksum": r["checksum"]}
            for r in rows
        }

    async def status(self) -> list[MigrationStatus]:
        files = self._load_files()
        applied = await self._applied()
        result = []
        for mf in files:
            rec = applied.get(mf.version)
            if rec is None:
                result.append(
                    MigrationStatus(
                        version=mf.version,
                        name=mf.name,
                        applied=False,
                        applied_at=None,
                        drift=False,
                    )
                )
            else:
                result.append(
                    MigrationStatus(
                        version=mf.version,
                        name=mf.name,
                        applied=True,
                        applied_at=rec["applied_at"],
                        drift=rec["checksum"] != mf.checksum,
                    )
                )
        return result

    async def upgrade(self, target: str | None = None) -> list[str]:
        """Aplica migrations pendentes até ``target`` (inclusive).

        Returns:
            Lista de versões aplicadas nesta chamada.
        """
        files = self._load_files()
        applied = await self._applied()
        applied_now: list[str] = []

        for mf in files:
            if target is not None and mf.version > target:
                break
            if mf.version in applied:
                continue
            if not mf.up_sql.strip():
                logger.warning(
                    "storage/migrations/postgres: migration %s sem seção -- up, pulando",
                    mf.version,
                )
                continue
            logger.info(
                "storage/migrations/postgres: aplicando %s_%s", mf.version, mf.name
            )
            await self._conn.execute(mf.up_sql)
            await self._conn.execute(
                "INSERT INTO schema_migrations(version, name, applied_at, checksum) "
                "VALUES ($1, $2, now(), $3) "
                "ON CONFLICT (version) DO UPDATE SET applied_at = now(), checksum = EXCLUDED.checksum",
                mf.version,
                mf.name,
                mf.checksum,
            )
            applied_now.append(mf.version)
            logger.info(
                "storage/migrations/postgres: %s_%s aplicada", mf.version, mf.name
            )

        if not applied_now:
            logger.debug("storage/migrations/postgres: banco atualizado — nada a fazer")
        return applied_now

    async def downgrade(self, target: str) -> list[str]:
        """Reverte migrations até ``target`` (inclusive).

        Returns:
            Lista de versões revertidas nesta chamada.
        """
        files = self._load_files()
        applied = await self._applied()
        to_revert = sorted(
            [mf for mf in files if mf.version in applied and mf.version >= target],
            key=lambda mf: mf.version,
            reverse=True,
        )
        reverted: list[str] = []
        for mf in to_revert:
            if not mf.down_sql.strip():
                logger.warning(
                    "storage/migrations/postgres: migration %s sem seção -- down, pulando",
                    mf.version,
                )
                continue
            logger.info(
                "storage/migrations/postgres: revertendo %s_%s", mf.version, mf.name
            )
            await self._conn.execute(mf.down_sql)
            await self._conn.execute(
                "DELETE FROM schema_migrations WHERE version = $1", mf.version
            )
            reverted.append(mf.version)
            logger.info(
                "storage/migrations/postgres: %s_%s revertida", mf.version, mf.name
            )
        return reverted
